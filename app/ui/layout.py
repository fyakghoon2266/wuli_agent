# app/ui/layout.py
import gradio as gr
from app.config import settings
from app.prompts import WELCOME_MESSAGE
from app.ui.styles import GEMINI_STYLE_CSS, CHECK_INPUT_JS

gr.set_static_paths(paths=["app/images/"])

# ===================== 建構 UI 函式 =====================

def create_demo(respond_fn, feedback_fn):
    
    chatbot = gr.Chatbot(
        elem_id="wuli-chatbot",
        avatar_images=("app/images/milu.jpeg", "app/images/wuli.jpeg"),
        layout="bubble", 
        show_label=False,
        scale=1, 
        render_markdown=True,
        value=[{"role": "assistant", "content": WELCOME_MESSAGE}],
    )

    textbox = gr.MultimodalTextbox(
        placeholder="跟 Wuli 說說發生什麼事了... (可貼上圖片或 Log)",
        container=False, 
        scale=7,
        autofocus=True,
        lines=1,
        max_lines=5, 
        elem_id="chat-input", 
        file_count="multiple" 
    )

    # 這裡我們甚至不傳 theme 了，因為我們的 CSS 已經接管了一切
    with gr.Blocks(fill_height=True, title="Wuli - Gaia Error Agent") as demo:
        
        gr.HTML(GEMINI_STYLE_CSS)

        interface = gr.ChatInterface(
            fn=respond_fn,
            chatbot=chatbot,
            textbox=textbox,
            multimodal=True, 
            title=None,
            description=None,
            submit_btn=True,
            stop_btn=True,
            fill_height=True,
            autoscroll=True,
        )

        chatbot.like(feedback_fn, None, None)
        
        # 綁定 JS 檢查事件
        textbox.change(None, [], [], js=CHECK_INPUT_JS)
        demo.load(None, [], [], js=CHECK_INPUT_JS)
        
    return demo