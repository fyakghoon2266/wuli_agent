from langchain.tools import tool
from gradio_client import Client
from app.skills.base import SkillBase
from app.config import settings


class VerifyGuardrailsSkill(SkillBase):
    name = "verify_prompt_with_guardrails"
    description = "將 Prompt 送進護欄 API 檢查是否違規"
    permission = "user"
    tags = ["security", "guardrails", "compliance"]
    status_message = "🛡️ Wuli 正在進行安全檢查..."
    sop = (
        "2. **時光偵探 (Log Detective) & 合規檢測 (Compliance Check)**：\n"
        "   - **觸發條件**：當使用者提到「剛剛」、「幾點幾分」、「為什麼被擋」未提供具體內容；"
        "或直接貼出一段 Prompt 問為何被擋。\n"
        "   - **動作**：\n"
        "     1. 優先呼叫 `search_litellm_logs` 撈取 Payload。\n"
        "     2. 撈到 Prompt 後，接續呼叫 `verify_prompt_with_guardrails` 進行檢測。\n"
        "   - **回應**：根據 API 回傳的「LLM 檢查」、「關鍵字」、「正則」結果，"
        "向使用者解釋具體是哪裡觸發了護欄。\n"
    )

    def as_tool(self):
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
                client = Client(settings.GUARDRAILS_API_URL, ssl_verify=False)

                result = client.predict(
                    user_text=prompt_content,
                    api_name="/check_all"
                )

                formatted_result = (
                    f"🛡️ 【檢查報告】 針對內容: '{prompt_content[:50]}...'\n"
                    f"1. {result[0]}\n"
                    f"2. {result[1]}\n"
                    f"3. {result[2]}\n"
                )
                return formatted_result

            except Exception as e:
                return f"💥 呼叫護欄 API 失敗: {str(e)}"

        return verify_prompt_with_guardrails
