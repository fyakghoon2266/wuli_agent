import psycopg2
import smtplib
import requests
from langchain.tools import tool
from app.skills.base import SkillBase
from app.config import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)


def _check_chromadb():
    """檢查 ChromaDB 向量資料庫"""
    try:
        from app.rag.chroma_store import build_client, get_collection
        client = build_client()
        collection = get_collection()
        count = collection.count()
        return "✅", f"正常 (已索引 {count} 筆文件)"
    except Exception as e:
        return "❌", f"異常: {str(e)}"


def _check_postgresql():
    """檢查 LiteLLM PostgreSQL 資料庫"""
    try:
        conn = psycopg2.connect(**settings.LITELLM_DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        conn.close()
        return "✅", "正常"
    except Exception as e:
        return "❌", f"異常: {str(e)}"


def _check_guardrails_api():
    """檢查護欄 API"""
    try:
        resp = requests.get(settings.GUARDRAILS_API_URL, timeout=5)
        if resp.status_code == 200:
            return "✅", "正常"
        else:
            return "⚠️", f"回應碼 {resp.status_code}"
    except requests.exceptions.ConnectionError:
        return "❌", "無法連線"
    except Exception as e:
        return "❌", f"異常: {str(e)}"


def _check_smtp():
    """檢查 SMTP 郵件伺服器"""
    try:
        server = smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT, timeout=5)
        server.starttls()
        server.login(settings.SENDER_EMAIL, settings.SENDER_PASSWORD)
        server.quit()
        return "✅", "正常"
    except Exception as e:
        return "❌", f"異常: {str(e)}"


def _check_github():
    """檢查 GitHub API"""
    try:
        if not settings.GITHUB_TOKEN:
            return "⚠️", "未設定 GITHUB_TOKEN"
        from github import Github, Auth
        g = Github(auth=Auth.Token(settings.GITHUB_TOKEN))
        repo = g.get_repo(settings.GITHUB_REPO_NAME)
        repo.full_name  # 觸發 API 呼叫
        return "✅", f"正常 ({repo.full_name})"
    except Exception as e:
        return "❌", f"異常: {str(e)}"


def _check_jira():
    """檢查 Jira API"""
    try:
        if not settings.JIRA_URL or not settings.JIRA_API_TOKEN:
            return "⚠️", "未設定 Jira 連線資訊"
        from jira import JIRA
        jira = JIRA(server=settings.JIRA_URL, basic_auth=(settings.JIRA_USER, settings.JIRA_API_TOKEN))
        jira.server_info()
        return "✅", "正常"
    except Exception as e:
        return "❌", f"異常: {str(e)}"


class HealthCheckSkill(SkillBase):
    name = "system_health_check"
    description = "檢查 Wuli Agent 所有相依服務的健康狀態"
    permission = "user"
    tags = ["health", "monitoring", "status"]
    status_message = "🏥 Wuli 正在進行系統健檢..."
    sop = (
        "6. **🏥 系統健檢 (Health Check)**：\n"
        "   - 當使用者問「系統狀態」、「health check」、「哪些服務正常」時，"
        "呼叫 `system_health_check` 工具。\n"
        "   - 根據回傳結果，向使用者報告各服務的健康狀態。\n"
    )

    def as_tool(self):
        @tool("system_health_check")
        def system_health_check(scope: str = "all"):
            """
            檢查 Wuli Agent 所依賴的所有外部服務健康狀態。

            Args:
                scope (str): 檢查範圍。'all' 檢查全部，或指定服務名稱如
                             'chromadb', 'postgresql', 'guardrails', 'smtp', 'github', 'jira'。
            """
            checks = {
                "chromadb": ("ChromaDB 向量資料庫", _check_chromadb),
                "postgresql": ("PostgreSQL (LiteLLM Log DB)", _check_postgresql),
                "guardrails": ("護欄 API (NeMo Guardrails)", _check_guardrails_api),
                "smtp": ("SMTP 郵件服務 (Gmail)", _check_smtp),
                "github": ("GitHub API", _check_github),
                "jira": ("Jira API", _check_jira),
            }

            scope_lower = scope.lower().strip()

            if scope_lower != "all" and scope_lower in checks:
                checks = {scope_lower: checks[scope_lower]}

            results = []
            total_ok = 0
            total = 0

            for key, (label, check_fn) in checks.items():
                total += 1
                try:
                    status_icon, detail = check_fn()
                    if status_icon == "✅":
                        total_ok += 1
                except Exception as e:
                    status_icon = "❌"
                    detail = f"檢查程式本身發生錯誤: {str(e)}"

                results.append(f"{status_icon} **{label}**: {detail}")

            header = f"🏥 **Wuli 系統健檢報告** ({total_ok}/{total} 服務正常)\n"
            separator = "─" * 40 + "\n"
            body = "\n".join(results)

            if total_ok == total:
                footer = "\n\n🎉 所有服務運作正常！Wuli 的各路感官都很靈敏喔～"
            else:
                footer = f"\n\n⚠️ 有 {total - total_ok} 個服務需要關注，建議通知工程師檢查。"

            return header + separator + body + footer

        return system_health_check
