import time
import json
import base64
import mimetypes
import os
from typing import List, Any, Dict

import gradio as gr
import pypdf  # 需安裝 pypdf
import docx   # 需安裝 python-docx
from langchain_core.messages import HumanMessage, AIMessage

# 引入重構後的模組
from app.config import settings
from app.prompts import SYSTEM_PROMPT
from app.llm_factory import AgentSingleton
from app.ui.layout import create_demo
from app.utils.logging import save_chat_log

# 取得 Agent 執行器實體
agent_executor = AgentSingleton.get_executor()

# ===================== 檔案讀取工具 (新增) =====================

def read_file_content(file_path):
    """
    萬用檔案讀取器：根據副檔名決定怎麼讀取內容
    回傳: (內容字串, 類型標記)
    類型標記: 'text', 'image', 'unknown', 'error'
    """
    if not file_path or not os.path.exists(file_path):
        return "", "error"

    filename = os.path.basename(file_path)
    ext = os.path.splitext(filename)[1].lower()
    content = ""

    try:
        # 1. 處理純文字 (.txt, .log, .py, .md, .json...)
        if ext in ['.txt', '.log', '.py', '.js', '.md', '.json', '.csv', '.sh', '.yaml', '.yml']:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
            return f"\n\n--- 📄 檔案內容 ({filename}) ---\n{content}\n--- 結束 ---\n", "text"
        
        # 2. 處理 Word (.docx)
        elif ext == '.docx':
            doc = docx.Document(file_path)
            content = "\n".join([para.text for para in doc.paragraphs])
            return f"\n\n--- 📄 Word 文件內容 ({filename}) ---\n{content}\n--- 結束 ---\n", "text"
            
        # 3. 處理 PDF (.pdf)
        elif ext == '.pdf':
            reader = pypdf.PdfReader(file_path)
            texts = []
            for page in reader.pages:
                extracted = page.extract_text()
                if extracted:
                    texts.append(extracted)
            content = "\n".join(texts)
            return f"\n\n--- 📄 PDF 文件內容 ({filename}) ---\n{content}\n--- 結束 ---\n", "text"
            
        # 4. 圖片 (.jpg, .png...) -> 不讀內容，回傳標記讓後續邏輯處理 Base64
        elif ext in ['.jpg', '.jpeg', '.png', '.webp', '.gif', '.bmp']:
            return filename, "image"

        else:
            return f"[系統提示: 無法讀取的檔案格式 {filename}]", "unknown"

    except Exception as e:
        return f"[系統提示: 讀取檔案 {filename} 時發生錯誤: {str(e)}]", "error"

# ===================== 圖片處理工具 =====================

def encode_image(image_path):
    """將圖片檔案轉為 Base64 字串"""
    if not image_path or not os.path.exists(image_path):
        return None, None
        
    mime_type, _ = mimetypes.guess_type(image_path)
    if not mime_type:
        mime_type = "image/jpeg"
        
    with open(image_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
        
    return mime_type, encoded_string

def process_history_for_langchain(gradio_history: List[Any]) -> List[Any]:
    """
    將 Gradio 的歷史紀錄清洗為 LangChain/Bedrock 可接受的格式
    """
    langchain_history = []
    
    if not gradio_history:
        return langchain_history

    if isinstance(gradio_history[0], dict):
        for msg in gradio_history:
            role = msg.get("role")
            content_raw = msg.get("content")
            final_content = []
            
            if isinstance(content_raw, str):
                final_content = content_raw
            
            elif isinstance(content_raw, list):
                for item in content_raw:
                    if isinstance(item, dict) and item.get("type") == "text":
                        final_content.append({"type": "text", "text": item.get("text")})
                    
                    elif isinstance(item, dict) and item.get("type") in ["file", "image"]:
                        # 歷史紀錄中的圖片處理 (簡化版，避免 Token 爆炸)
                        file_path = item.get("url") or item.get("path")
                        if file_path:
                            # 判斷是否為圖片副檔名
                            ext = os.path.splitext(file_path)[1].lower()
                            if ext in ['.jpg', '.jpeg', '.png', '.webp']:
                                # 嘗試讀圖
                                m_type, b64_str = encode_image(file_path)
                                if b64_str:
                                    final_content.append({
                                        "type": "image_url",
                                        "image_url": {"url": f"data:{m_type};base64,{b64_str}"}
                                    })
                                else:
                                    final_content.append({"type": "text", "text": "[歷史圖片已過期]"})
                            else:
                                # 若是歷史文件，通常已經在當時的 text 裡了，這裡可略過或標記
                                pass 

            if role == "user":
                langchain_history.append(HumanMessage(content=final_content))
            elif role == "assistant":
                langchain_history.append(AIMessage(content=final_content))
                
    return langchain_history

# ===================== 邏輯處理區 =====================

def respond(message: dict, history: List[Any]):
    """
    處理對話邏輯：支援多模態輸入 (圖片轉 Base64, 文件轉文字)
    """
    
    # 1. 清洗歷史紀錄
    chat_history = process_history_for_langchain(history)
    
    # 2. 準備本次的使用者輸入
    user_content = []
    raw_text_input = ""
    
    # 用來存放需要轉 Base64 給 Vision Model 的圖片路徑
    image_files_to_process = []

    # --- 解析 Input ---
    if isinstance(message, dict):
        text_input = message.get("text", "")
        files = message.get("files", [])
        
        # 處理上傳的檔案 (分離 圖片 vs 文件)
        if files:
            for file_path in files:
                content, file_type = read_file_content(file_path)
                
                # A. 如果是文字/文件 -> 直接加到 text_input
                if file_type == "text":
                    text_input += content
                # B. 如果是錯誤訊息 -> 也加到 text_input 讓 LLM 知道
                elif file_type == "error":
                    text_input += f"\n{content}\n"
                # C. 如果是圖片 -> 加入待處理清單
                elif file_type == "image":
                    image_files_to_process.append(file_path)

        # 記錄處理後的完整文字 (包含文件內容)
        raw_text_input = text_input

        # 建構 Payload: 加入文字
        if text_input:
            user_content.append({"type": "text", "text": text_input})
        
        # 建構 Payload: 加入圖片 (Base64)
        for img_path in image_files_to_process:
            try:
                mime_type, base64_image = encode_image(img_path)
                if base64_image:
                    print(f"🔍 [Debug] 圖片轉碼成功: {img_path}")
                    user_content.append({
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime_type};base64,{base64_image}"
                        }
                    })
            except Exception as e:
                print(f"❌ 圖片讀取失敗: {e}")
    else:
        # 純文字相容
        user_content = message
        raw_text_input = str(message)

    # 空值防呆
    if not raw_text_input and not image_files_to_process:
        raw_text_input = "[使用者上傳了無法讀取的內容]"

    # 包裝成 HumanMessage
    input_message = HumanMessage(content=user_content)

    # 3. 準備 Agent 輸入
    input_data = {
        "input": raw_text_input, # 這裡現在包含你的 txt/pdf 內容了！
        "user_message": [input_message],
        "chat_history": chat_history,
    }

    # Debug Log
    print(f"🚀 [Debug] 發送 Input 字數: {len(raw_text_input)}, 圖片數: {len(image_files_to_process)}")

    # 4. 執行與回傳
    try:
        for chunk in agent_executor.stream(input_data):
            
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
            
            if "output" in chunk:
                final_answer = chunk["output"]
                
                if isinstance(final_answer, list):
                    text_parts = []
                    for block in final_answer:
                        if isinstance(block, dict) and "text" in block:
                            text_parts.append(block["text"])
                        elif isinstance(block, str):
                            text_parts.append(block)
                    final_answer = "".join(text_parts)
                
                final_answer = str(final_answer)

                if not final_answer.strip():
                    final_answer = "✅ 分析完成！(但 Wuli 看得太入迷忘記說話了 😺)"

                yield "" 

                partial_message = ""
                for char in final_answer:
                    partial_message += char
                    yield partial_message
                    time.sleep(0.005)

                save_chat_log(message, final_answer)

    except Exception as e:
        error_msg = f"😿 嗚... Wuli 的眼睛好像花了：{str(e)}"
        print(f"❌ Error Details: {e}")
        save_chat_log(message, error_msg)
        yield error_msg
        
# ===================== Feedback 處理區 (保持不變) =====================

def clean_content(content):
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
    index = x.index
    is_liked = x.liked 
    user_query_raw = "無法讀取"
    bot_response_raw = "無法讀取"

    try:
        if index < len(history):
             if isinstance(history[index], dict):
                 bot_response_raw = history[index].get('content', '')
                 if index > 0:
                     user_query_raw = history[index - 1].get('content', '')
             elif isinstance(history[index], (list, tuple)):
                 pass 
    except Exception as e:
        print(f"解析資料錯誤: {e}")

    user_query_clean = clean_content(user_query_raw)
    bot_response_clean = clean_content(bot_response_raw)

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
        print(f"回饋已儲存: {status}")
    except Exception as e:
        print(f"寫入檔案失敗: {e}")

# ===================== 程式入口 =====================

if __name__ == "__main__":
    demo = create_demo(respond_fn=respond, feedback_fn=on_feedback)
    demo.launch(server_name="127.0.0.1", server_port=8002, root_path="/wuliagent")