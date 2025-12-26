import json
import os
import time
from langchain.tools import tool

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
            "detail": detail,   # 這裡改用通用名稱 detail，因為可能是解法，也可能是進度
            "status": status    # 🔥 新增狀態
        }
        
        logs.append(new_entry)
        _save_logs(logs)
        
        status_icon = "✅" if status == "Resolved" else "🚧"
        return f"{status_icon} 已記錄至週報清單！({status})\n- 事項: {error_summary}\n- 目前累積: {len(logs)} 筆資料"

    except Exception as e:
        return f"❌ 記錄失敗: {str(e)}"