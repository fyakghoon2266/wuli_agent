# app/main.py
from typing import Any, Dict, List

import gradio as gr

from .llm import call_llm_with_rag, LLM_PROVIDER

# ===================== 文案設定 =====================

SYSTEM_PROMPT = (
    "你是一個協助工程師處理 LLM 基礎建設 Gaia 平台相關問題的技術型助手。\n"
    "你也叫做 Wuli，是一隻冷靜、理性的問題排查貓貓。\n"
    "你可以使用內部的 Error Cards（錯誤說明卡片）來協助判斷 log 與提供建議。\n"
    "如果沒有合適的 Error Card，可以根據一般工程實務給出保守、安全的建議。\n"
    "回答要：精簡、技術正確、適度親切但不要太油。"
)

WELCOME_MESSAGE = (
    "您好，我叫做 **Wuli** 🐱。\n\n"
    "我是 Gaia 基礎建設平台的問題排查貓貓助手。\n\n"
    "歡迎把你在平台上遇到的錯誤訊息、log、或奇怪行為貼給我，\n"
    "我會盡力協助你找出原因並提供可能的解法。"
)


# ===================== ChatInterface callback =====================

def respond(message: str, history: List[Any]) -> str:
    """
    ChatInterface 標準介面：
    - message: 使用者這一輪輸入
    - history: 目前對話歷史（由 ChatInterface 管）
      - 在 messages 模式下：List[{"role": "...", "content": "..."}]
      - 在 tuple 模式下（某些版本）：List[(user, assistant)]
    回傳：本輪助手回覆字串
    """

    messages_state: List[Dict[str, str]] = []

    # 1) system prompt
    messages_state.append({"role": "system", "content": SYSTEM_PROMPT})

    # 2) 把 history 轉成 messages_state
    if history:
        # messages 模式：list of dict
        if isinstance(history[0], dict):
            for m in history:
                role = m.get("role")
                content = m.get("content")
                if role in ("user", "assistant") and content:
                    messages_state.append({"role": role, "content": content})
        # 舊 tuple 模式：list of (user, assistant)
        elif isinstance(history[0], (list, tuple)):
            for user_text, assistant_text in history:
                if user_text:
                    messages_state.append({"role": "user", "content": user_text})
                if assistant_text:
                    messages_state.append(
                        {"role": "assistant", "content": assistant_text}
                    )
    else:
        # 沒有歷史：讓 Wuli 先自我介紹一次（只進 LLM context，不影響 UI）
        messages_state.append({"role": "assistant", "content": WELCOME_MESSAGE})

    # 3) 本輪 user 訊息
    messages_state.append({"role": "user", "content": message})

    # 4) 呼叫 LLM + RAG
    reply = call_llm_with_rag(messages_state)
    return reply


# ===================== Gradio UI (ChatInterface) =====================

# 讓 avatar 可以讀到本機圖片
gr.set_static_paths(paths=["app/images/"])

custom_css = """
           
            .message-row img {
                margin: 0px !important;
            }

            .avatar-container img {
            padding: 0px !important;
}
        """


# with gr.Blocks() as demo:

# Chatbot 使用 messages 格式的初始值：一則 assistant 歡迎訊息
chatbot = gr.Chatbot(
    label="Wuli - Gaia Error Agent",
    height=400,
    avatar_images=[
        "app/images/milu.jpeg",  # user avatar
        "app/images/wuli.jpeg",  # assistant avatar
    ],
    value=[{"role": "assistant", "content": WELCOME_MESSAGE}],
)

textbox = gr.Textbox(
    label="輸入訊息 / 貼上 error log",
    placeholder="把你遇到的錯誤訊息、log 或問題描述貼給 Wuli 看看。",
    lines=4,
    autofocus=True,
    submit_btn=True
)

demo = gr.ChatInterface(
    fn=respond,
    flagging_mode="manual",
    chatbot=chatbot,
    textbox=textbox,
    title="Wuli - Gaia Error Agent",
    description=(
        f"模型 Provider：`{LLM_PROVIDER}`\n\n"
        "這是一個協助排查 Gaia 基礎建設相關錯誤的問答機器人。\n"
        "貼上錯誤 log / 報錯訊息 / 使用情境，我會盡力協助你分析。"
    )
)

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860, css=custom_css)
