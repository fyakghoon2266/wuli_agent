import gradio as gr
from app.ui.styles import CUSTOM_CSS, AUTO_FOCUS_JS
from app.prompts import WELCOME_MESSAGE
from app.config import settings

# 設定靜態路徑 (讓頭貼讀得到)
gr.set_static_paths(paths=["app/images/"])


# ===================== 建構 UI 函式 =====================

def create_demo(respond_fn, feedback_fn):
    """
    建立 Gradio UI 的工廠函式。
    
    Args:
        respond_fn: 處理對話的主要邏輯函式 (Stream)。
        feedback_fn: 處理按讚/倒讚的邏輯函式。
    
    Returns:
        gr.Blocks: 建構好的 Gradio App 物件。
    """
    with gr.Blocks(title="Wuli - Gaia Error Agent") as demo:
        
        # 1. 注入 CSS
        gr.HTML(f"<style>{CUSTOM_CSS}</style>")

        # 2. 定義 Chatbot 元件
        chatbot = gr.Chatbot(
            label="Wuli - Gaia Error Agent",
            height=600,
            elem_id="wuli-chatbot",
            # 注意：這裡的路徑是相對於執行 main.py 的位置
            avatar_images=("app/images/milu.jpeg", "app/images/wuli.jpeg"),
            value=[{"role": "assistant", "content": WELCOME_MESSAGE}],
            layout="bubble",
            buttons=["copy", "copy_all"],
            scale=1,
            render_markdown=True,
            sanitize_html=True,
            line_breaks=True
        )

        # 3. 定義輸入框
        # textbox = gr.Textbox(
        #     label="輸入訊息 / 貼上 error log",
        #     placeholder="把你遇到的錯誤訊息、log 或問題描述貼給 Wuli 看看。",
        #     submit_btn=True,
        #     elem_id="chat-input" 
        # )

        # 4. 綁定 Feedback 事件
        chatbot.like(feedback_fn, chatbot, None)

        # 5. 綁定自動 Focus JS
        chatbot.change(
            fn=None,
            inputs=[],
            outputs=[],
            js=AUTO_FOCUS_JS
        )

        # 6. 使用 ChatInterface 整合
        # 這裡將外部傳入的 respond_fn 綁定進去
        gr.ChatInterface(
        fn=respond_fn,
        flagging_mode="manual",
        chatbot=chatbot,
        # textbox=textbox, <--- 這行刪掉，讓 ChatInterface 自己產生多模態輸入框
        multimodal=True,   # <--- 🔥 關鍵：開啟多模態 (出現上傳按鈕) 🔥
        submit_btn=True,
        autofocus=True,
        autoscroll=True,
        title="Wuli - Gaia Error Agent",
        description=(
            f"模型 Provider：`{settings.LLM_PROVIDER}`\n"
            "</br>"
            "這是一個協助排查 Gaia 基礎建設相關錯誤的問答貓貓助手🐱。\n"
            "</br>"
            "貼上錯誤 log / **error log 截圖** / 使用情境，**Wuli** 🐱會盡力協助你分析。"
        )
    )
    
    return demo