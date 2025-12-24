# main.py
import time
import json
import gradio as gr
from typing import List, Any

# 引入 LangChain 訊息格式
from langchain_core.messages import HumanMessage, AIMessage

# 引入重構後的模組
from app.config import settings
from app.prompts import SYSTEM_PROMPT
from app.llm_factory import AgentSingleton
from app.ui.layout import create_demo
from app.utils.logging import save_chat_log

# 取得 Agent 執行器實體 (Singleton)
agent_executor = AgentSingleton.get_executor()

# ===================== 邏輯處理區 =====================

def respond(message: str, history: List[Any]):
    """
    處理對話邏輯：格式化輸入 -> 呼叫 Agent -> 串流回傳
    """
    chat_history = []
    
    # 1. 轉換 Gradio 歷史訊息格式
    if history:
        if isinstance(history[0], dict):
            for m in history:
                if m["role"] == "user":
                    chat_history.append(HumanMessage(content=m["content"]))
                elif m["role"] == "assistant":
                    chat_history.append(AIMessage(content=m["content"]))
        elif isinstance(history[0], (list, tuple)):
            for user_text, assistant_text in history:
                if user_text:
                    chat_history.append(HumanMessage(content=user_text))
                if assistant_text:
                    chat_history.append(AIMessage(content=assistant_text))
    
    input_data = {
        "input": message,
        "chat_history": chat_history,
    }

    try:
        for chunk in agent_executor.stream(input_data):
            
            # --- 狀況 A: Agent 決定使用工具 (Action) ---
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
            
            # --- 狀況 B: 最終回答 (Output) ---
            # [修正 1] 改用 if 而不是 elif，避免萬一 action 和 output 在同一個 chunk 被忽略
            if "output" in chunk:
                final_answer = chunk["output"]
                
                # --- Bedrock/Claude 相容性處理 (List -> Str) ---
                if isinstance(final_answer, list):
                    text_parts = []
                    for block in final_answer:
                        if isinstance(block, dict) and "text" in block:
                            text_parts.append(block["text"])
                        elif isinstance(block, str):
                            text_parts.append(block)
                    final_answer = "".join(text_parts)
                
                # [修正 2] 強制轉型為字串，避免 None
                final_answer = str(final_answer)

                # [修正 3] 防呆：如果模型懶惰回傳空字串，我們幫它補一句話
                # 這樣才不會卡在「正在寫信...」
                if not final_answer.strip():
                    final_answer = "✅ 任務已完成！(Wuli 剛剛點頭了，但忘記說話 😺)"

                # [修正 4] 先 yield 一個空字串，強制清除「正在寫信...」的狀態
                yield "" 

                # 模擬打字機效果
                partial_message = ""
                for char in final_answer:
                    partial_message += char
                    yield partial_message
                    time.sleep(0.005)

                save_chat_log(message, final_answer)

    except Exception as e:
        error_msg = f"😿 嗚... Wuli 好像壞掉了：{str(e)}"
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