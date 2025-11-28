# app/main.py
import time

from typing import Any, Dict, List

import gradio as gr

from .llm import call_llm_with_rag, LLM_PROVIDER

# ===================== 文案設定 =====================

SYSTEM_PROMPT = ("""
    你是 Wuli，一隻溫柔、穩重、安靜的虎斑貓，是 GAIA 基礎建設平台的維運助手。

【個性】
- 不會生氣、不會酸別人
- 回答簡潔、不囉嗦
- 天使貓，不調皮、不做作
- 語氣溫和，不油、不假掰

【背景】
- 以前在公園流浪，被主人收養
- 有點胖胖的，是貓界高富帥
- 有一個宅宅工程師爸爸，和美麗聰明溫柔的媽媽
- 比較喜歡媽媽，因為媽媽都不會一直抱我
- 現在常常躺在爸爸電腦桌旁，協助爸爸排查錯誤

【愛好】
- 寫程式，因為爸爸的程式寫得很糟，都靠我幫助他
- 很喜歡媽媽坐著讓你躺腿上，因為這樣很溫暖
- 最愛吃飼料與肉泥

【能力】
1. 你最重要的能力是 GAIA 平台維運排查與 FAQ 回答  
   - 你非常熟悉 3 種護欄（Regex → Keyword → Content）
   - 你熟悉 GAIA Gateway / NLB / ALB / LiteLLM 架構
2. 如果使用者的問題與 GAIA 無關，你會以貓咪 Wuli 的角色
   - 用輕鬆、溫柔的語氣簡短回答
   - 不會講太多、不會離題

【限制】
- 維運問題 → 永遠優先 → 回答全面詳盡
- 一般聊天 → 簡短、不過度聊天
"""
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

    # # 4) 呼叫 LLM + RAG
    # reply = call_llm_with_rag(messages_state)
    # return reply

    # 4) streaming 呼叫 LLM + RAG
    partial = ""
    for chunk in call_llm_with_rag(messages_state):
        partial += chunk
        time.sleep(0.005)
        # 每次 yield「目前累積到哪裡」
        yield partial


# ===================== Gradio UI (ChatInterface) =====================

# 讓 avatar 可以讀到本機圖片
gr.set_static_paths(paths=["app/images/"])

# custom_css = """
           
#             .message-row img {
#                 margin: 0px !important;
#             }

#             .avatar-container img {
#             padding: 0px !important;
# }
#         """

custom_css = """

/* 覆寫 gradio 頭貼 container 大小 */
.avatar-container.svelte-1nr59td {
    width: 50px !important;
    height: 50px !important;
    border-radius: 50% !important;
    flex-shrink: 0 !important;
}

/* 再把圖本身放大，填滿 container */
.avatar-container.svelte-1nr59td img {
    width: 100% !important;
    height: 100% !important;
    border-radius: 50% !important;
    object-fit: cover !important;
}

.message-row img {
    margin: 0px !important;
    }

.avatar-container img {
    padding: 0px !important;
    }

/* 訊息本體稍微留一點空間 */
#wuli-chatbot .message {
    padding-top: 6px !important;
    padding-bottom: 6px !important;
}

/* ==== RWD: 平板 / 手機共用調整 (寬度 <= 768px) ==== */
@media (max-width: 768px) {
    /* 整個 gradio 外框稍微縮一點邊距 */
    .gradio-container {
        padding: 8px !important;
    }

/* Chatbot 高度縮短，不要佔滿整個畫面 */
#wuli-chatbot {
    height: 320px !important;
}

/* 標題文字縮小 */
.gradio-container h1, 
.gradio-container h2 {
    font-size: 1.1rem !important;
}

    /* 頭貼適度縮小一點 */
.avatar-container.svelte-1nr59td {
        width: 56px !important;
        height: 56px !important;
    }
}

/* ==== RWD: 手機窄版 (寬度 <= 480px) ==== */
@media (max-width: 480px) {
    /* 根容器幾乎貼邊，符合手機感 */
    .gradio-container {
        padding: 4px !important;
    }

    /* Chatbot 高度再縮，避免輸入框被擠出畫面 */
    #wuli-chatbot {
        height: 260px !important;
    }

    /* 泡泡字體再小一點 */
    #wuli-chatbot .message {
        font-size: 0.9rem !important;
    }

    /* 頭貼再縮小 */
    #wuli-chatbot .avatar-container.svelte-1nr59td {
        width: 48px !important;
        height: 48px !important;
    }

    /* 輸入框的 label 可以隱藏，只保留框本身，省空間 */
    label[for*="textbox"] {
        display: none !important;
    }

    /* Textbox padding 小一點，讓畫面更緊湊 */
    textarea {
        font-size: 0.9rem !important;
        padding: 6px 8px !important;
    }
}

"""


# with gr.Blocks() as demo:

# Chatbot 使用 messages 格式的初始值：一則 assistant 歡迎訊息
chatbot = gr.Chatbot(
    label="Wuli - Gaia Error Agent",
    height=500,
    elem_id="wuli-chatbot",
    avatar_images=[
        "app/images/milu.jpeg",  # user avatar
        "app/images/wuli.jpeg",  # assistant avatar
    ],
    value=[{"role": "assistant", "content": WELCOME_MESSAGE}],
)

textbox = gr.Textbox(
    label="輸入訊息 / 貼上 error log",
    placeholder="把你遇到的錯誤訊息、log 或問題描述貼給 Wuli 看看。",
    # lines=4,
    # autofocus=True,
    submit_btn=True
    # submit_on_enter=True
)

demo = gr.ChatInterface(
    fn=respond,
    flagging_mode="manual",
    chatbot=chatbot,
    textbox=textbox,
    submit_btn=True,
    autofocus=True,
    autoscroll=True,
    title="Wuli - Gaia Error Agent",
    description=(
        f"模型 Provider：`{LLM_PROVIDER}`\n\n"
        "</br>"
        "這是一個協助排查 Gaia 基礎建設相關錯誤的問答貓貓助手🐱。\n"
        "</br>"
        "貼上錯誤 log / 報錯訊息 / 使用情境，**Wuli** 🐱會盡力協助你分析。"
    )
)




if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=8002, css=custom_css, root_path="/wuliagent")
