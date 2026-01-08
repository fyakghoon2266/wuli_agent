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

# 引入模組
from app.config import settings
# from app.prompts import SYSTEM_PROMPT # 如果 llm_factory 已經處理了 Prompt，這裡可能不需要
from app.llm_factory import build_agent_executor # 移除 AgentSingleton，直接用 build
from app.ui.layout import create_demo
from app.utils.logging import save_chat_log
from app.scheduler import start_scheduler, run_weekly_eol_scan

# ===================== 檔案讀取工具 (保持不變) =====================

def read_file_content(file_path):
    """
    萬用檔案讀取器：根據副檔名決定怎麼讀取內容
    """
    if not file_path or not os.path.exists(file_path):
        return "", "error"

    filename = os.path.basename(file_path)
    ext = os.path.splitext(filename)[1].lower()
    content = ""

    try:
        # 1. 處理純文字
        if ext in ['.txt', '.log', '.py', '.js', '.md', '.json', '.csv', '.sh', '.yaml', '.yml']:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
            return f"\n\n--- 📄 檔案內容 ({filename}) ---\n{content}\n--- 結束 ---\n", "text"
        
        # 2. 處理 Word
        elif ext == '.docx':
            doc = docx.Document(file_path)
            content = "\n".join([para.text for para in doc.paragraphs])
            return f"\n\n--- 📄 Word 文件內容 ({filename}) ---\n{content}\n--- 結束 ---\n", "text"
            
        # 3. 處理 PDF
        elif ext == '.pdf':
            reader = pypdf.PdfReader(file_path)
            texts = []
            for page in reader.pages:
                extracted = page.extract_text()
                if extracted:
                    texts.append(extracted)
            content = "\n".join(texts)
            return f"\n\n--- 📄 PDF 文件內容 ({filename}) ---\n{content}\n--- 結束 ---\n", "text"
            
        # 4. 圖片
        elif ext in ['.jpg', '.jpeg', '.png', '.webp', '.gif', '.bmp']:
            return filename, "image"

        else:
            return f"[系統提示: 無法讀取的檔案格式 {filename}]", "unknown"

    except Exception as e:
        return f"[系統提示: 讀取檔案 {filename} 時發生錯誤: {str(e)}]", "error"

# ===================== 圖片處理工具 (保持不變) =====================

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

    # (這裡保持原本邏輯不變)
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
                        file_path = item.get("url") or item.get("path")
                        if file_path:
                            ext = os.path.splitext(file_path)[1].lower()
                            if ext in ['.jpg', '.jpeg', '.png', '.webp']:
                                m_type, b64_str = encode_image(file_path)
                                if b64_str:
                                    final_content.append({
                                        "type": "image_url",
                                        "image_url": {"url": f"data:{m_type};base64,{b64_str}"}
                                    })
                                else:
                                    final_content.append({"type": "text", "text": "[歷史圖片已過期]"})
                            else:
                                pass 

            if role == "user":
                langchain_history.append(HumanMessage(content=final_content))
            elif role == "assistant":
                langchain_history.append(AIMessage(content=final_content))
                
    return langchain_history

# ===================== 邏輯處理區 (權限核心修改) =====================

def respond(message: dict, history: List[Any], request: gr.Request):
    """
    處理對話邏輯：支援多模態輸入 + 權限控管
    """
    
    # 1. 🔥 身份識別與權限判斷
    if request:
        username = request.username
        # print(f"🎤 收到訊息，來自使用者: {username}")
    else:
        username = "guest"

    # 判斷是否為管理員 (根據 app/config.py 設定)
    is_admin = username in settings.ADMIN_USERS
    
    # 2. 🔥 根據權限，現場建立對應的 Agent (不再使用全域變數)
    # 這裡的 current_agent 會根據 is_admin 拿到不同的工具箱
    current_agent = build_agent_executor(is_admin=is_admin)
    
    # 3. 清洗歷史紀錄
    chat_history = process_history_for_langchain(history)
    
    # 4. 準備本次的使用者輸入
    user_content = []
    raw_text_input = ""
    image_files_to_process = []

    # --- 解析 Input ---
    if isinstance(message, dict):
        text_input = message.get("text", "")
        files = message.get("files", [])
        
        if files:
            for file_path in files:
                content, file_type = read_file_content(file_path)
                if file_type == "text":
                    text_input += content
                elif file_type == "error":
                    text_input += f"\n{content}\n"
                elif file_type == "image":
                    image_files_to_process.append(file_path)

        raw_text_input = text_input

        if text_input:
            user_content.append({"type": "text", "text": text_input})
        
        for img_path in image_files_to_process:
            try:
                mime_type, base64_image = encode_image(img_path)
                if base64_image:
                    user_content.append({
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime_type};base64,{base64_image}"
                        }
                    })
            except Exception as e:
                print(f"❌ 圖片讀取失敗: {e}")
    else:
        user_content = message
        raw_text_input = str(message)

    if not raw_text_input and not image_files_to_process:
        raw_text_input = "[使用者上傳了無法讀取的內容]"

    input_message = HumanMessage(content=user_content)

    # 5. 準備 Agent 輸入
    input_data = {
        "input": raw_text_input,
        "user_message": [input_message],
        "chat_history": chat_history,
    }

    print(f"🚀 [Debug] User: {username} (Admin: {is_admin}) | Input: {len(raw_text_input)} chars")

    # 6. 執行與回傳
    try:
        # 🔥 修正重點：使用 current_agent 執行，而不是 agent_executor
        for chunk in current_agent.stream(input_data):
            
            if "actions" in chunk:
                for action in chunk["actions"]:
                    # 根據工具名稱顯示不同訊息
                    tool_name = action.tool
                    if tool_name == "search_error_cards":
                        yield "🐾 Wuli 正在翻閱維運手冊..."
                    elif tool_name == "search_litellm_logs":
                         yield "🔍 Wuli 正在潛入資料庫查 Log..."
                    elif tool_name == "verify_prompt_with_guardrails":
                         yield "🛡️ Wuli 正在進行安全檢查..."
                    elif tool_name == "send_email_to_engineer":
                         yield "📧 Wuli 正在寫信給工程師..."
                    elif tool_name == "report_issue_to_jira":
                         yield "🎫 Wuli 正在建立 Jira 卡片..."
                    elif tool_name == "web_search_technical_solution":
                         yield "🌐 內部查無資料，Wuli 正在搜尋外部網站解答中..."
                    else:
                        yield f"🤖 Wuli 正在使用工具: {tool_name}..."
            
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
    # (此部分代碼保持原本的樣子，為了節省版面我先略過，不需要修改)
    pass 

# 🔥 [新增] 用來更新登入狀態的函式
def update_login_info(request: gr.Request):
    """
    當網頁載入時觸發。
    檢查 request.username 並回傳歡迎訊息。
    """
    if not request:
        return "👻 未登入 (Guest)"
        
    username = request.username
    
    # 判斷身分
    if username in settings.ADMIN_USERS:
        role_display = "🛡️ 管理員 (Admin)"
        color = "green" # 可以用 markdown 語法上色
    else:
        role_display = "👤 一般使用者 (User)"
        color = "blue"
        
    # 回傳 Markdown 格式的字串
    # 這裡的 <div style='text-align: right'> 可以讓文字靠右對齊，看起來像右上角的資訊欄
    return f"""
    <div style='text-align: right; font-size: 1.1em;'>
        👋 嗨，<b>{username}</b>！<br>
        目前身分：<span style='color: {color}; font-weight: bold;'>{role_display}</span>
    </div>
    """

# ===================== 程式入口 =====================

if __name__ == "__main__":

    # 1. 啟動排程
    start_scheduler()
    
    # 🔥 [測試區] 強制立刻執行一次 EOL 檢查
    # 測試完記得註解掉，不然每次重啟都會寄信！
    print("⚡️ [DEBUG] 正在執行手動測試：EOL 掃描...")
    try:
        run_weekly_eol_scan()
    except Exception as e:
        print(f"❌ 測試執行失敗: {e}")
    print("⚡️ [DEBUG] 測試結束，啟動 UI...")

    # 2. 建立 UI
    demo = create_demo(respond_fn=respond, feedback_fn=on_feedback)

    # 3. 🔥 啟動並加上 Auth 門禁
    print(f"🔒 Wuli Agent 安全模式啟動")
    print(f"   - Admin Users: {settings.ADMIN_USERS}")
    
    # 請確保 settings.AUTHORIZED_USERS 格式為 [("帳號", "密碼"), ("帳號2", "密碼2")]
    demo.launch(
        server_name="127.0.0.1", 
        server_port=8002, 
        root_path="/wuliagent",
        auth=settings.AUTHORIZED_USERS, # 👈 關鍵：加上這行啟用登入
        auth_message="🚧 歡迎使用 Wuli SRE Agent，請登入您的貓貓帳號，讓我確認您是管理員貓貓還是使用者貓貓 🚧"
    )