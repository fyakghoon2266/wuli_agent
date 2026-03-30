import json
from datetime import datetime
from jira import JIRA
from langchain.tools import tool
from app.skills.base import SkillBase
from app.config import settings


class ReportJiraSkill(SkillBase):
    name = "report_issue_to_jira"
    description = "在 Jira 建立追蹤卡片 (掛在 GA-633 底下)"
    permission = "admin"
    tags = ["jira", "ticket", "tracking"]
    status_message = "🎫 Wuli 正在建立 Jira 卡片..."
    sop = ""  # Jira 開票由 admin 手動觸發，不需要特別 SOP

    def as_tool(self):
        @tool("report_issue_to_jira")
        def report_issue_to_jira(summary: str, description: str, category: str):
            """
            Use this tool to report an issue or work log to Jira under the fixed parent Epic (GA-633).

            Args:
                summary (str): The concise title of the issue.
                description (str): Detailed description, error logs, or steps.
                category (str): The status category of the issue. MUST be one of:
                    - "resolved": Use this if the issue is already solved. (Will create a 'Story')
                    - "pending": Use this if the issue is NOT solved yet and needs follow-up. (Will create a 'Task')
                    - "bug": Use this if it is a confirmed system defect or internal error. (Will create a 'Bug')
            """
            if not settings.JIRA_URL or not settings.JIRA_API_TOKEN:
                return "❌ 尚未設定 Jira 連線資訊。"

            try:
                jira = JIRA(server=settings.JIRA_URL, basic_auth=(settings.JIRA_USER, settings.JIRA_API_TOKEN))
                today_date = datetime.now().strftime("%Y-%m-%d")

                if category == "resolved":
                    issue_type = "Story"
                    prefix = "[Resolved] "
                elif category == "pending":
                    issue_type = "Task"
                    prefix = "[Pending] "
                elif category == "bug":
                    issue_type = "Bug"
                    prefix = "[Bug] "
                else:
                    issue_type = "Task"
                    prefix = ""

                issue_dict = {
                    'project': {'key': settings.JIRA_PROJECT_KEY},
                    'summary': f"{prefix}{summary}",
                    'description': description,
                    'issuetype': {'name': issue_type},
                    'parent': {'key': settings.JIRA_PARENT_TICKET},
                    'customfield_10088': today_date,
                    'customfield_10089': today_date,
                    'customfield_10035': 1.0
                }

                new_issue = jira.create_issue(fields=issue_dict)

                return (
                    f"✅ 已在 {settings.JIRA_PARENT_TICKET} 底下建立追蹤卡片！\n"
                    f"📌 類型: {issue_type}\n"
                    f"🔑 單號: {new_issue.key}\n"
                    f"🔗 連結: {new_issue.permalink()}"
                )

            except Exception as e:
                error_msg = str(e)
                if "response text" in error_msg:
                    try:
                        start = error_msg.find("response text = ") + 16
                        json_str = error_msg[start:]
                        err_dict = json.loads(json_str)
                        error_msg = f"Jira 拒絕建立: {err_dict.get('errors', err_dict)}"
                    except:
                        pass

                if "issue type" in error_msg.lower():
                    return f"❌ 建立失敗：類型錯誤。請確認父卡片 {settings.JIRA_PARENT_TICKET} 是否為 Epic？"

                return f"❌ Jira 開票失敗: {error_msg}"

        return report_issue_to_jira
