from langchain.tools import tool
from gradio_client import Client
from app.config import settings

@tool
def verify_prompt_with_guardrails(prompt_content: str):
    """
    【護欄阻擋原因檢查器】
    
    使用時機：
    1. 當 `search_litellm_logs` 查到某個 Prompt 被阻擋，但 Log 裡沒有詳細原因時。
    2. 使用者問：「為什麼這句話不行？」、「幫我檢查這句話有沒有違規」。
    3. Wuli 需要判斷某個 Payload 到底是中了「關鍵字」、「正則」還是「LLM 審查」。
    4. 【直接檢查】：當使用者直接貼出一段文字問：「這句話為什麼被擋？」、「幫我檢查這段 Prompt 有沒有違規」、「這句話會過嗎？」。
    
    Args:
        prompt_content: 要檢查的使用者輸入內容 (User Prompt)。
    """
    try:
        # 連線到你的 Guardrails API
        client = Client(settings.GUARDRAILS_API_URL, ssl_verify=False)
        
        # 呼叫預測
        result = client.predict(
            user_text=prompt_content,
            api_name="/check_all"
        )
        
        # result 是一個 tuple，包含 (LLM檢查結果, 關鍵字檢查結果, 正則檢查結果)
        # 我們把它組合成清楚的字串回傳給 Wuli
        formatted_result = (
            f"🛡️ 【檢查報告】 針對內容: '{prompt_content[:50]}...'\n"
            f"1. {result[0]}\n"
            f"2. {result[1]}\n"
            f"3. {result[2]}\n"
        )
        return formatted_result

    except Exception as e:
        return f"💥 呼叫護欄 API 失敗: {str(e)}"