import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from langchain.tools import tool
from app.skills.base import SkillBase
from app.config import settings


class SendEmailSkill(SkillBase):
    name = "send_email_to_engineer"
    description = "寄信通知值班工程師，並副本給使用者"
    permission = "user"
    tags = ["communication", "email", "escalation"]
    status_message = "📧 Wuli 正在寫信給工程師..."
    sop = (
        "4. **人工介入流程 (寄信)**：\n"
        "   當確定無法解決問題，必須寄信時，請遵守以下流程：\n"
        "   - **第一步：強制資料完整性** (確保取得「姓名」與「Email」)。若缺漏，請直接溫柔追問，不要猜測。\n"
        "   - **第二步：自動摘要與發送**：總結問題與已嘗試的步驟，呼叫 `send_email_to_engineer`。\n"
    )

    def as_tool(self):
        @tool
        def send_email_to_engineer(user_name: str, user_email: str, problem_summary: str, attempted_steps: str):
            """
            【寄信給值班工程師工具】

            使用時機：
            1. 當使用者要求人工介入。
            2. 必須要求使用者提供「Email 信箱」，因為會寄送副本給使用者留存。

            Args:
                user_name: 使用者的稱呼 (例如：小陳、Jason)。
                user_email: 使用者的 Email 信箱 (必須是合法的 Email 格式，用於寄送副本)。
                problem_summary: 問題的詳細摘要 (包含錯誤碼、發生時間、現象)。
                attempted_steps: 使用者已經嘗試過哪些排查步驟。
            """
            try:
                if "@" not in user_email or "." not in user_email:
                    return f"❌ 寄信失敗：提供的聯絡資訊 '{user_email}' 看起來不像有效的 Email 格式。請要求使用者提供正確的信箱以便寄送副本。"

                msg = MIMEMultipart()
                msg['From'] = settings.SENDER_EMAIL
                msg['To'] = settings.ENGINEER_EMAIL
                msg['Cc'] = user_email
                msg['Subject'] = f"【Wuli Agent 求助】使用者：{user_name}"

                body = f"""
        值班工程師你好，Wuli 收到使用者的求助請求。
        (本郵件已自動副本給使用者 {user_name} 留存)

        ================================================
        👤 使用者身份
        姓名：{user_name}
        聯絡信箱：{user_email}

        🔴 遭遇問題摘要
        {problem_summary}

        🛠️ 使用者已嘗試過的步驟
        {attempted_steps}
        ================================================

        請協助確認，謝謝！
        (本郵件由 Wuli Agent 自動彙整發送)
        """
                msg.attach(MIMEText(body, 'plain'))

                server = smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT)
                server.starttls()
                server.login(settings.SENDER_EMAIL, settings.SENDER_PASSWORD)

                recipients = [settings.ENGINEER_EMAIL, user_email]
                server.send_message(msg, to_addrs=recipients)
                server.quit()

                return f"✅ 信件已成功寄出！\n收件人：工程師\n副本(CC)：{user_name} ({user_email})\n請使用者去收信確認喔！"

            except Exception as e:
                return f"❌ 寄信失敗：{str(e)}"

        return send_email_to_engineer
