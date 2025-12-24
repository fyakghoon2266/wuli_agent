# app/main.py
import time
import json
import base64
import mimetypes
import os
from typing import List, Any, Dict

import gradio as gr
from langchain_core.messages import HumanMessage, AIMessage

# 引入重構後的模組
from app.config import settings
from app.prompts import SYSTEM_PROMPT
from app.llm_factory import AgentSingleton
from app.ui.layout import create_demo
from app.utils.logging import save_chat_log

# 取得 Agent 執行器實體
agent_executor = AgentSingleton.get_executor()

# ===================== 圖片處理工具 =====================

def encode_image(image_path):
    """將圖片檔案轉為 Base64 字串"""
    if not image_path or not os.path.exists(image_path):
        return None, None
        
    # 簡單判斷 mime type
    mime_type, _ = mimetypes.guess_type(image_path)
    if not mime_type:
        mime_type = "image/jpeg"
        
    with open(image_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
        
    return mime_type, encoded_string

def process_history_for_langchain(gradio_history: List[Any]) -> List[Any]:
    """
    【關鍵修復】將 Gradio 的歷史紀錄清洗為 LangChain/Bedrock 可接受的格式
    解決 'Input tag file found using type' 錯誤
    """
    langchain_history = []
    
    if not gradio_history:
        return langchain_history

    # 針對 Gradio 4.0+ 的 dict 格式歷史紀錄進行迭代
    # 格式通常是: [{'role': 'user', 'content': ...}, {'role': 'assistant', 'content': ...}]
    if isinstance(gradio_history[0], dict):
        for msg in gradio_history:
            role = msg.get("role")
            content_raw = msg.get("content")
            
            # 準備轉換後的 content
            final_content = []
            
            # A. 如果 content 是字串 (純文字)
            if isinstance(content_raw, str):
                final_content = content_raw
            
            # B. 如果 content 是列表 (多模態: 文字 + 圖片/檔案)
            elif isinstance(content_raw, list):
                for item in content_raw:
                    # 情況 1: 純文字區塊
                    if isinstance(item, dict) and item.get("type") == "text":
                        final_content.append({"type": "text", "text": item.get("text")})
                    
                    # 情況 2: 檔案/圖片區塊 (Gradio 存成 'file' 或 'image')
                    # 🔥 重點：Bedrock 不吃 'file'，我們要轉成 'image_url' 或略過
                    elif isinstance(item, dict) and item.get("type") in ["file", "image"]:
                        file_path = item.get("url") or item.get("path") # Gradio 版本不同 key 可能不同
                        
                        # 嘗試讀取圖片轉 base64
                        # 注意：為了節省 Token 和避免報錯，這裡有兩個策略：
                        # 策略 1 (完整): 再次轉檔傳給 LLM (成本高，且如果 temp 檔被刪會報錯)
                        # 策略 2 (省錢/穩健): 歷史圖片只留個 "[圖片]" 標記，只讓 LLM 看最新上傳的圖
                        
                        # 這裡採用【混合策略】：如果是 User 的最新一則，一定要傳圖；
                        # 但如果是「歷史紀錄」，為了避免 Bedrock 報錯和 Token 爆炸，我們簡化它。
                        # 但因為你的需求是 "這裏面寫什麼?" (Refer to previous image)，
                        # 我們嘗試讀取看看，讀不到就變文字。
                        
                        m_type, b64_str = encode_image(file_path)
                        if b64_str:
                            final_content.append({
                                "type": "image_url",
                                "image_url": {"url": f"data:{m_type};base64,{b64_str}"}
                            })
                        else:
                            # 讀不到檔案 (可能被清除了)，改用文字標記
                            final_content.append({"type": "text", "text": "[已上傳一張圖片]"})

            # 建立 Message 物件
            if role == "user":
                langchain_history.append(HumanMessage(content=final_content))
            elif role == "assistant":
                langchain_history.append(AIMessage(content=final_content))
                
    return langchain_history

# ===================== 邏輯處理區 =====================

def respond(message: dict, history: List[Any]):
    """
    處理對話邏輯：支援多模態輸入，並修復 Bedrock 格式錯誤與 Unhashable Type 錯誤
    """
    
    # 1. 清洗歷史紀錄 (使用 process_history_for_langchain)
    chat_history = process_history_for_langchain(history)
    
    # 2. 準備本次的使用者輸入 (User Message - 給 LLM 看的真實內容)
    user_content = []
    
    # 用來給 AgentExecutor 做 Log 的純文字摘要 (避免 unhashable error)
    raw_text_input = ""
    
    # 判斷是否為多模態輸入
    if isinstance(message, dict):
        text_input = message.get("text", "")
        files = message.get("files", [])
        
        # 記錄純文字部分
        raw_text_input = text_input

        # A. 加入文字
        if text_input:
            user_content.append({"type": "text", "text": text_input})
        
        # B. 加入圖片
        for file_path in files:
            try:
                mime_type, base64_image = encode_image(file_path)
                if base64_image:
                    # 🔥 [Debug Log] 確認圖片轉碼成功
                    print(f"🔍 [Debug] 圖片轉碼成功！格式: {mime_type}, 長度: {len(base64_image)}")
                    
                    user_content.append({
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime_type};base64,{base64_image}"
                        }
                    })
                else:
                    print(f"⚠️ 警告: 無法讀取圖片 {file_path}")
            except Exception as e:
                print(f"❌ 圖片讀取失敗: {e}")
    else:
        # 純文字相容 (舊版)
        user_content = message
        raw_text_input = str(message)

    # 如果只有傳圖片沒傳字，給個預設文字，避免 input 為空
    if not raw_text_input:
        raw_text_input = "[使用者上傳了圖片]"

    # 🔥 [關鍵修正] 將 user_content 包裝成 HumanMessage 物件
    # 這是為了配合 Prompt Template 中的 MessagesPlaceholder(variable_name="user_message")
    input_message = HumanMessage(content=user_content)

    # 3. 準備 Agent 輸入
    input_data = {
        # 🟢 [关键 1] "input": 給 AgentExecutor 內部紀錄用 (必須是 String，避免 unhashable error)
        "input": raw_text_input,
        
        # 🟢 [关键 2] "user_message": 真正給 LLM 看的內容 (包含圖片 Payload)
        "user_message": [input_message],
        
        "chat_history": chat_history,
    }

    # 🔥 [Debug Log] 確認送出的結構類型
    debug_input_summary = []
    if isinstance(user_content, list):
        for item in user_content:
            if isinstance(item, dict):
                debug_input_summary.append(item.get("type", "unknown"))
    print(f"🚀 [Debug] 準備發送給 Agent 的輸入類型: {debug_input_summary}")

    # 4. 執行與回傳
    try:
        for chunk in agent_executor.stream(input_data):
            
            # --- 狀況 A: 工具使用狀態 ---
            if "actions" in chunk:
                for action in chunk["actions"]:
                    if action.tool == "search_error_cards":
                        yield "🐾 Wuli 正在翻閱維運手冊..."
                    elif action.tool == "search_litellm_logs":
                         yield "🔍 Wuli 正在潛入資料庫查 Log..."
                    elif action.tool == "verify_prompt_with_guardrails":
                         yield "🛡️ Wuli 正在進行安全檢查..."
                    elif action.tool == "send_email_to_engineer":
                         yield "📧 Wuli 正在寫信給工程師..."
            
            # --- 狀況 B: 最終回答 ---
            if "output" in chunk:
                final_answer = chunk["output"]
                
                # Bedrock List -> Str 轉換
                if isinstance(final_answer, list):
                    text_parts = []
                    for block in final_answer:
                        if isinstance(block, dict) and "text" in block:
                            text_parts.append(block["text"])
                        elif isinstance(block, str):
                            text_parts.append(block)
                    final_answer = "".join(text_parts)
                
                final_answer = str(final_answer)

                # 空字串防呆
                if not final_answer.strip():
                    final_answer = "✅ 分析完成！(但 Wuli 看得太入迷忘記說話了 😺)"

                yield "" # 清除狀態

                # 打字機效果
                partial_message = ""
                for char in final_answer:
                    partial_message += char
                    yield partial_message
                    time.sleep(0.005)

                save_chat_log(message, final_answer)

    except Exception as e:
        error_msg = f"😿 嗚... Wuli 的眼睛好像花了：{str(e)}"
        print(f"❌ Error Details: {e}") # 印出詳細錯誤到後台方便除錯
        save_chat_log(message, error_msg)
        yield error_msg
        
# ===================== Feedback 處理區 =====================

def clean_content(content):
    """處理多模態資料，轉為純文字"""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        text_parts = []
        for item in content:
            if isinstance(item, dict) and 'text' in item:
                text_parts.append(item['text'])
            elif isinstance(item, str):
                text_parts.append(item)
        return " ".join(text_parts)
    return str(content)

def on_feedback(x: gr.LikeData, history):
    """處理使用者按讚/倒讚"""
    index = x.index
    is_liked = x.liked 
    user_query_raw = "無法讀取"
    bot_response_raw = "無法讀取"

    try:
        # 解析 History 結構 (針對新版 Gradio dict 格式)
        if index < len(history):
             if isinstance(history[index], dict):
                 bot_response_raw = history[index].get('content', '')
                 if index > 0:
                     user_query_raw = history[index - 1].get('content', '')
             # 針對舊版 tuple 格式
             elif isinstance(history[index], (list, tuple)):
                 # 注意：tuple 格式通常 user/bot 在同一組，邏輯可能不同，這裡針對 dict 優化
                 pass 

    except Exception as e:
        print(f"解析資料錯誤: {e}")

    # 清理內容
    user_query_clean = clean_content(user_query_raw)
    bot_response_clean = clean_content(bot_response_raw)

    # 寫入 JSONL
    feedback_data = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "user_query": user_query_clean,
        "bot_response": bot_response_clean,
        "is_positive": is_liked,
        "raw_index": index
    }
    
    try:
        with open("feedback_log/feedback_log.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(feedback_data, ensure_ascii=False) + "\n")
        
        status = "👍" if is_liked else "👎"
        print(f"回饋已儲存: {status} | User: {user_query_clean[:10]}...")
    except Exception as e:
        print(f"寫入檔案失敗: {e}")





# ===================== 程式入口 =====================

if __name__ == "__main__":
    # 使用 layout.py 提供的工廠函式建立 UI
    # 並注入我們的邏輯函式 (respond, on_feedback)
    demo = create_demo(respond_fn=respond, feedback_fn=on_feedback)
    
    # 啟動伺服器
    demo.launch(server_name="127.0.0.1", server_port=8002, root_path="/wuliagent")