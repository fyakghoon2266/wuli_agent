import json
import os
import time
from langchain.tools import tool
from app.skills.base import SkillBase

LOG_FILE = "data/weekly_incidents.json"


def _load_logs():
    if not os.path.exists(LOG_FILE):
        return []
    try:
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []


def _save_logs(logs):
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(logs, f, ensure_ascii=False, indent=2)


class LogIncidentSkill(SkillBase):
    name = "log_incident_for_weekly_report"
    description = "將事件記錄至週報清單"
    permission = "admin"
    tags = ["incident", "report", "logging"]
    status_message = "📋 Wuli 正在記錄本次事件至週報..."
    sop = (
        "### 📝 週報記錄 SOP (嚴格觸發制 🔒)\n"
        "**【重要規則】請勿自動記錄週報！** "
        "只有在使用者**明確發出指令** (如 \"@Wuli 加入週報\", \"標記此問題\") 時才允許執行。\n"
        "**執行流程：**\n"
        "1. 聽到觸發關鍵字。\n"
        "2. 判斷狀態：已解決 (Resolved) 或 未解決 (Pending)。\n"
        "3. 提取 錯誤摘要、詳細內容、狀態、回報人。\n"
        "4. 呼叫 `log_incident_for_weekly_report`，完成後感謝使用者貢獻。\n"
    )

    def as_tool(self):
        @tool("log_incident_for_weekly_report")
        def log_incident_for_weekly_report(error_summary: str, detail: str, status: str, reporter: str):
            """
            ONLY use this tool when the user EXPLICITLY asks to mark a conversation as a 'Gaia Incident' or 'Handover item'.

            Args:
                error_summary (str): A concise summary (e.g., "LiteLLM 502 Bad Gateway").
                detail (str): If status is 'Resolved', provide the Solution.
                              If status is 'Pending', provide Current Progress & Next Steps.
                status (str): Must be either "Resolved" (已解決) or "Pending" (未解決/交接).
                reporter (str): The name of the engineer reporting this.
            """
            try:
                logs = _load_logs()

                new_entry = {
                    "id": int(time.time()),
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "reporter": reporter,
                    "error": error_summary,
                    "detail": detail,
                    "status": status
                }

                logs.append(new_entry)
                _save_logs(logs)

                status_icon = "✅" if status == "Resolved" else "🚧"
                return f"{status_icon} 已記錄至週報清單！({status})\n- 事項: {error_summary}\n- 目前累積: {len(logs)} 筆資料"

            except Exception as e:
                return f"❌ 記錄失敗: {str(e)}"

        return log_incident_for_weekly_report
