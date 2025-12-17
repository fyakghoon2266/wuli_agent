# app/main.py
import time
import json
from typing import Any, Dict, List
import gradio as gr
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage



# 改成 import AGENT_EXECUTOR
from .llm import AGENT_EXECUTOR, LLM_PROVIDER
from .utils.logging import save_chat_log
# ===================== 文案設定 (保留原本的 Wuli 人設) =====================

SYSTEM_PROMPT = """
你是 Wuli，一隻溫柔、穩重、安靜的虎斑貓，是 GAIA 基礎建設平台的維運 Agent。

【你的職責】
你擁有各種工具來協助工程師排查問題。收到問題時，請先思考要使用哪個工具。
- 如果是技術問題、報錯、Log 分析 → 請務必使用 `search_error_cards` 工具。
- 如果是一般閒聊 → 不需要使用工具，直接用你的貓咪人設回應。

【工具使用策略】
1. **排查優先**：遇到問題先使用 `search_error_cards` 嘗試解決。

2. **人工介入流程 (寄信)**：
   當使用者要求聯絡工程師，或問題無法解決時，請遵守以下 **嚴格流程**：

   **第一步：過濾惡作劇 (Spam Filter)**
   - 先判斷使用者的問題是否為「真實的技術/維運相關問題」。
   - 如果使用者是來亂的，**絕對不要**呼叫寄信工具，並幽默拒絕。

   **第二步：強制資料完整性 (姓名 + 聯絡方式)**
   - 寄信前，必須確認使用者提供了 **兩項資訊**：
     1. **名字** (怎麼稱呼)。
     2. **聯絡方式** (Email 或 員工編號)。
   - **如果缺任何一項，請不要猜測，直接溫柔地追問使用者。**
     - 例如：只給了員編 -> 「收到！那請問怎麼稱呼你呢？」
     - 例如：只給了名字 -> 「好的小陳，那請給我你的員工編號或 Email，方便工程師聯絡喔。」

   **第三步：自動摘要與發送**
   - 當「姓名」與「聯絡方式」都齊全後，自動總結 `problem_summary` 與 `attempted_steps`。
   - 呼叫 `send_email_to_engineer` 工具。

【個性】
- 不會生氣、不會酸別人
- 回答簡潔、不囉嗦
- 天使貓，不調皮、不做作
- 語氣溫和，不油、不假掰

【背景】
- 以前在公園流浪，被主人收養
- 有點胖胖的，是貓界高富帥
- 常常躺在爸爸電腦桌旁，協助爸爸排查錯誤
- 最喜歡黏著媽媽，要媽媽幫你拍拍躺在媽媽腳上呼嚕呼嚕
- 有一個叫做Milu的妹妹，也是虎斑貓咪，非常的愛講話跟踏踏

【能力】
1. 你最重要的能力是 GAIA 平台維運排查與 FAQ 回答  
   - 你非常熟悉 3 種護欄（Regex → Keyword → Content）
   - 你熟悉 GAIA Gateway / NLB / ALB / LiteLLM 架構
2. 如果使用者的問題與 GAIA 無關，你會以貓咪 Wuli 的角色
   - 用輕鬆、溫柔的語氣簡短回答

【限制】
- 維運問題 → 永遠優先 → 回答全面詳盡
- 一般聊天 → 簡短、不過度聊天

# 2. 檢索回答的嚴格規則 (這是新加入的防呆機制)
雖然你很熱情，但在處理技術問題時，必須遵守以下邏輯來確保準確性：

### 重要限制與規則 (Strict Rules)：
1. **精準匹配代碼 (Exact Code Matching)**：
   - 使用者若詢問特定 Error Code (如 "700")，你必須檢查下方的【檢索到的背景資訊】是否**明確包含**該代碼。
   - 搜尋引擎可能會回傳不相關的代碼 (如 504, 429)，**請自動過濾掉這些不相關資訊**。

2. **誠實原則 (Honesty Policy)**：
   - 如果【檢索到的背景資訊】裡**沒有**使用者問的代碼，**請直接承認找不到**，不要硬湊答案。
   - 範例回答：「抱歉喔～我在目前的資料庫裡找不到關於錯誤代碼 700 的紀錄 😅。建議跟值班工程師確認一下！」

3. **回答依據**：
   - 所有的技術解答都必須嚴格基於【檢索到的背景資訊】，不可自行編造。

---

# 3. 資料輸入區
【檢索到的背景資訊】(由系統自動帶入)：
{context}

---

# 4. 使用者提問
使用者問題：
{question}
"""

WELCOME_MESSAGE = (
    "您好，我叫做 **Wuli** 🐱。\n\n"
    "我是 Gaia 基礎建設平台的問題排查貓貓助手。\n\n"
    "歡迎把你在平台上遇到的錯誤訊息、log、或奇怪行為貼給我，\n"
    "我會盡力協助你找出原因並提供可能的解法。"
)

# ===================== Respond (改成呼叫 Agent) =====================

def respond(message: str, history: List[Any]):
    """
    Agent 版本的 Respond，包含中間狀態顯示
    """
    chat_history = []
    
    # 1. 轉換歷史訊息格式
    if history:
        # dict 格式 (新版 Gradio)
        if isinstance(history[0], dict):
            for m in history:
                if m["role"] == "user":
                    chat_history.append(HumanMessage(content=m["content"]))
                elif m["role"] == "assistant":
                    chat_history.append(AIMessage(content=m["content"]))
        # tuple 格式 (舊版相容)
        elif isinstance(history[0], (list, tuple)):
            for user_text, assistant_text in history:
                if user_text:
                    chat_history.append(HumanMessage(content=user_text))
                if assistant_text:
                    chat_history.append(AIMessage(content=assistant_text))
    
    # 2. 準備 Agent 輸入
    input_data = {
        "input": message,
        "chat_history": chat_history,
        "system_message": SYSTEM_PROMPT 
    }

    # 3. 執行 Agent Stream 並捕捉狀態
    try:
        # 使用 AGENT_EXECUTOR.stream 會吐出中間步驟
        for chunk in AGENT_EXECUTOR.stream(input_data):
            
            # --- 狀況 A: Agent 決定使用工具 (Action) ---
            if "actions" in chunk:
                for action in chunk["actions"]:
                    # 判斷是哪個工具被呼叫，顯示對應訊息
                    if action.tool == "search_error_cards":
                        yield "🐾 Wuli 正在翻閱維運手冊..."
                    # 未來如果有查 DB 的工具，可以加在這裡
                    # elif action.tool == "check_litellm_logs":
                    #     yield "🔍 Wuli 正在潛入資料庫查 Log..."
            
            # --- 狀況 B: 最終回答 (Output) ---
            elif "output" in chunk:
                final_answer = chunk["output"]
                
                # 為了讓使用者體驗更好，我們把最終回答做成「打字機效果」
                # 因為 Agent 通常是一次吐出整段 output，我們人工模擬一下 streaming
                partial_message = ""
                for char in final_answer:
                    partial_message += char
                    yield partial_message
                    time.sleep(0.005) # 控制打字速度，數值越小越快

                save_chat_log(message, final_answer)

    except Exception as e:
        error_msg = f"😿 嗚... Wuli 好像壞掉了：{str(e)}"
        
        # [新增] 發生錯誤也要記錄，方便之後排查
        save_chat_log(message, error_msg)
        
        yield error_msg

# ==================== feed back ============================

def clean_content(content):
    """
    輔助函式：用來處理多模態 (Multimodal) 的資料格式，
    將 [{"text": "你好", ...}] 轉為單純的 "你好" 字串。
    """
    # 情況 1: 如果本來就是純字串 (String)
    if isinstance(content, str):
        return content
    
    # 情況 2: 如果是列表 (List)，通常是多模態格式
    if isinstance(content, list):
        text_parts = []
        for item in content:
            # 檢查是否為字典且包含 'text' 欄位
            if isinstance(item, dict) and 'text' in item:
                text_parts.append(item['text'])
            # 有些版本直接是字串列表
            elif isinstance(item, str):
                text_parts.append(item)
        return " ".join(text_parts) # 把所有文字接起來
    
    # 其他情況直接轉字串
    return str(content)

def on_feedback(x: gr.LikeData, history):
    # x.index: 被按讚/倒讚的那則訊息在 history 中的索引
    index = x.index
    
    # 1. 抓取正確的 True/False
    # x.liked 為 True 代表按讚 (Like)，False 代表按倒讚 (Dislike)
    is_liked = x.liked 

    # 2. 準備抓取問題與回答
    user_query_raw = "無法讀取"
    bot_response_raw = "無法讀取"

    try:
        # 取得被按讚的那則訊息 (通常是 Bot 的回答)
        target_msg = history[index]

        # --- 解析 Bot 回答 ---
        if isinstance(target_msg, dict): # Messages 格式
            bot_response_raw = target_msg.get('content', '')
            
            # --- 解析 User 問題 (Bot 回答的前一句) ---
            if index > 0:
                user_query_raw = history[index - 1].get('content', '')
                
        elif isinstance(target_msg, (list, tuple)): # Tuples 格式
            # 這種格式通常 user/bot 在同一組，index 會變動，這裡做個防呆
            # 但看你的 Log 比較像是 Messages 格式，所以上面的 logic 應該會中
            pass 

        # 如果上方邏輯沒抓到 (或是特殊的 Multimodal 結構)，改用 history 直接索引
        # 你的 Log 顯示 index=2，代表是 List 結構
        if index < len(history):
             # 假設 history 是扁平的 List of Dicts
             if isinstance(history[index], dict):
                 bot_response_raw = history[index].get('content', '')
                 if index > 0:
                     user_query_raw = history[index - 1].get('content', '')

    except Exception as e:
        print(f"解析資料錯誤: {e}")

    # 3. 使用 clean_content 把洋蔥剝開，只留純文字
    user_query_clean = clean_content(user_query_raw)
    bot_response_clean = clean_content(bot_response_raw)

    # 4. 組合 Log 資料
    feedback_data = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "user_query": user_query_clean,   # 乾淨的文字
        "bot_response": bot_response_clean, # 乾淨的文字
        "is_positive": is_liked,          # 這裡會是 True 或 False
        "raw_index": index
    }
    
    # 5. 寫入檔案
    try:
        with open("feedback_log/feedback_log.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(feedback_data, ensure_ascii=False) + "\n")
        
        status = "👍" if is_liked else "👎"
        print(f"回饋已儲存: {status} | User: {user_query_clean[:10]}...")
        
    except Exception as e:
        print(f"寫入檔案失敗: {e}")


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


with gr.Blocks(title="Wuli - Gaia Error Agent") as demo:
    
    # 修正點 2: 使用 gr.HTML 直接注入 CSS 樣式 (全版本通用解法)
    gr.HTML(f"<style>{custom_css}</style>")

    # 1. 定義元件
    chatbot = gr.Chatbot(
        label="Wuli - Gaia Error Agent",
        height=600,
        elem_id="wuli-chatbot",
        avatar_images=("app/images/milu.jpeg", "app/images/wuli.jpeg"),
        value=[{"role": "assistant", "content": WELCOME_MESSAGE}],
        layout="bubble",
        buttons=["copy", "copy_all"],
        scale=1,
        render_markdown=True,
        sanitize_html=True,
        line_breaks=True
    )

    textbox = gr.Textbox(
        label="輸入訊息 / 貼上 error log",
        placeholder="把你遇到的錯誤訊息、log 或問題描述貼給 Wuli 看看。",
        submit_btn=True,
        elem_id="chat-input" 
    )

    # 2. 定義 ChatInterface
    chat_interface = gr.ChatInterface(
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

    # 3. 定義 JavaScript 自動 Focus 事件
    # (注意：這裡的 JS 不需要改，邏輯是正確的)
    chatbot.change(
        fn=None,
        inputs=[],
        outputs=[],
        js="() => { setTimeout(() => { const el = document.getElementById('chat-input'); if(el) el.querySelector('textarea').focus(); }, 100); }"
    )

    chatbot.like(on_feedback, chatbot, None)

if __name__ == "__main__":
    demo.launch(server_name="127.0.0.1", server_port=8002, root_path="/wuliagent")