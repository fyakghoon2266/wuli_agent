# app/tools/jira_ops.py
import json
from datetime import datetime
from jira import JIRA
from langchain.tools import tool
from app.config import settings

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
        
        # 1. 根據你的邏輯自動決定 Issue Type
        # (注意：這裡的 Story/Task/Bug 必須與你們 Jira 裡的英文類型名稱完全一致)
        if category == "resolved":
            issue_type = "Story"      # 解決掉的 -> 故事
            prefix = "[Resolved] "
        elif category == "pending":
            issue_type = "Task"       # 沒解決的 -> 任務
            prefix = "[Pending] "
        elif category == "bug":
            issue_type = "Bug"        # 系統漏洞 -> 漏洞
            prefix = "[Bug] "
        else:
            # 預設值，避免 LLM 亂填
            issue_type = "Task"
            prefix = ""

        # 2. 準備欄位
        issue_dict = {
            'project': {'key': settings.JIRA_PROJECT_KEY},
            'summary': f"{prefix}{summary}", # 自動加上前綴讓列表更清楚
            'description': description,
            'issuetype': {'name': issue_type},
            
            # 🔥 指定父系卡片 (GA-633)
            # 在 Jira Cloud 中，Epic Link 現在統一使用 'parent' 欄位
            'parent': {'key': settings.JIRA_PARENT_TICKET},

            # 必填日期 (設為今天)
            'customfield_10088': today_date, 
            'customfield_10089': today_date,
            'customfield_10035': 1.0
        }

        # 3. 建立票券
        new_issue = jira.create_issue(fields=issue_dict)
        
        return (
            f"✅ 已在 {settings.JIRA_PARENT_TICKET} 底下建立追蹤卡片！\n"
            f"📌 類型: {issue_type}\n"
            f"🔑 單號: {new_issue.key}\n"
            f"🔗 連結: {new_issue.permalink()}"
        )

    except Exception as e:
        error_msg = str(e)
        # 嘗試解析詳細錯誤
        if "response text" in error_msg:
             try:
                 start = error_msg.find("response text = ") + 16
                 json_str = error_msg[start:]
                 err_dict = json.loads(json_str)
                 error_msg = f"Jira 拒絕建立: {err_dict.get('errors', err_dict)}"
             except:
                 pass
        
        # 💡 常見錯誤提示
        if "issue type" in error_msg.lower():
            return f"❌ 建立失敗：類型錯誤。請確認父卡片 {settings.JIRA_PARENT_TICKET} 是否為 Epic？一般 Task 底下無法建立 Story/Bug。"
            
        return f"❌ Jira 開票失敗: {error_msg}"