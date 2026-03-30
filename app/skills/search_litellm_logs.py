import psycopg2
import datetime
from typing import Optional

from langchain.tools import tool
from app.skills.base import SkillBase
from app.config import settings


def _core_log_search(
    key_name: Optional[str],
    keyword: str,
    lookback_minutes: int,
    start_time: Optional[str],
    end_time: Optional[str]
):
    try:
        conn = psycopg2.connect(**settings.LITELLM_DB_CONFIG)
        cursor = conn.cursor()

        base_sql = """
        SELECT
            ("startTime" + INTERVAL '8 hours') as local_time,
            "user",
            metadata->>'user_api_key_alias' as api_key_alias,
            messages,
            proxy_server_request,
            response
        FROM "LiteLLM_SpendLogs"
        """

        conditions = []
        params = []

        if key_name:
            conditions.append("metadata->>'user_api_key_alias' = %s")
            params.append(key_name)

        if start_time:
            conditions.append('("startTime" + INTERVAL \'8 hours\') >= %s')
            params.append(start_time)
            if end_time:
                conditions.append('("startTime" + INTERVAL \'8 hours\') <= %s')
                params.append(end_time)
        else:
            conditions.append('("startTime" + INTERVAL \'8 hours\') >= NOW() - INTERVAL %s')
            params.append(f"{lookback_minutes} minutes")

        if conditions:
            base_sql += " WHERE " + " AND ".join(conditions)

        base_sql += ' ORDER BY "startTime" DESC LIMIT 15;'

        cursor.execute(base_sql, tuple(params))
        rows = cursor.fetchall()
        conn.close()

        target = f"專案 Key Name '{key_name}'" if key_name else "所有紀錄"

        if not rows:
            return f"📭 查詢完成，在 {target} 中找不到符合的 Log (已校正時區)。"

        result_text = []
        for row in rows:
            t_start, user_id, api_key_alias, msgs, proxy_req, resp = row

            display_project_name = api_key_alias if api_key_alias else f"{user_id} (無 Alias)"

            if isinstance(t_start, datetime.datetime):
                t_start_str = t_start.strftime("%Y-%m-%d %H:%M:%S")
            else:
                t_start_str = str(t_start)

            prompt_content = "(無法讀取 Prompt)"
            if isinstance(msgs, list) and len(msgs) > 0:
                prompt_content = msgs[-1].get('content', '')
            elif proxy_req:
                try:
                    hidden_msgs = proxy_req.get('messages') or proxy_req.get('body', {}).get('messages')
                    if hidden_msgs:
                        prompt_content = hidden_msgs[-1].get('content', '')
                except:
                    pass

            if keyword:
                search_target = f"{str(user_id)} {str(api_key_alias)} {prompt_content}"
                if keyword.lower() not in search_target.lower():
                    continue

            output_content = "Success"
            if isinstance(resp, dict):
                if 'error' in resp:
                    output_content = f"❌ Error: {resp['error']}"
                else:
                    choices = resp.get('choices', [])
                    if choices:
                        output_content = f"✅ Reply: {choices[0]['message']['content'][:50]}..."

            log_entry = (
                f"⏰ 時間: {t_start_str}\n"
                f"👤 Key Name: {display_project_name}\n"
                f"📝 Prompt: {prompt_content[:100]}...\n"
                f"📤 狀態: {output_content}\n"
                "------------------------------------------------"
            )
            result_text.append(log_entry)

        if not result_text:
            return f"已搜尋資料庫，但在過濾關鍵字 '{keyword}' 後沒有符合的紀錄。"

        return "\n".join(result_text)

    except Exception as e:
        return f"💥 資料庫查詢失敗: {str(e)}"


class SearchLitellmLogsAdminSkill(SkillBase):
    name = "search_litellm_logs"
    description = "查詢 LiteLLM 使用紀錄 (管理員版，可查所有專案)"
    permission = "admin"
    tags = ["logs", "database", "litellm"]
    status_message = "🔍 Wuli 正在潛入資料庫查 Log..."
    sop = (
        "0. **查詢 Log 的權限規則 (Log Search Policy)**：\n"
        "   - 當使用者要求查 Log 時：\n"
        "   - 如果使用者是管理員 (你不需要管，直接查)。\n"
        "   - **如果是一般使用者，必須提供 `Key Name` (專案代號)。**\n"
        "   - 若一般使用者沒給 Key Name，請溫柔地反問：\n"
        "     「為了幫你精確查詢，請問你的 Key Name (專案代號) 是什麼呢？😺」\n"
        "   - 拿到 Key Name 後，請填入工具的 `key_name` 參數中。\n"
    )

    def as_tool(self):
        @tool("search_litellm_logs")
        def search_litellm_logs_admin(
            key_name: Optional[str] = None,
            keyword: str = "",
            lookback_minutes: int = 60,
            start_time: Optional[str] = None,
            end_time: Optional[str] = None
        ):
            """
            【LiteLLM Log 查詢工具 - 管理員版】
            key_name 為選填。
            若不填 key_name，將查詢「所有專案」的紀錄。
            若填寫 key_name，則過濾特定專案。
            """
            return _core_log_search(key_name, keyword, lookback_minutes, start_time, end_time)

        return search_litellm_logs_admin


class SearchLitellmLogsUserSkill(SkillBase):
    name = "search_litellm_logs"
    description = "查詢 LiteLLM 使用紀錄 (一般使用者版，需提供 Key Name)"
    permission = "user"
    tags = ["logs", "database", "litellm"]
    status_message = "🔍 Wuli 正在潛入資料庫查 Log..."
    sop = ""  # SOP 已在 admin 版定義，避免重複

    def as_tool(self):
        @tool("search_litellm_logs")
        def search_litellm_logs_user(
            key_name: str,
            keyword: str = "",
            lookback_minutes: int = 60,
            start_time: Optional[str] = None,
            end_time: Optional[str] = None
        ):
            """
            【LiteLLM Log 查詢工具 - 一般用戶版】
            key_name 為必填。
            必須提供 Key Name (專案代號) 才能查詢，不可查詢全域紀錄。
            """
            if not key_name:
                return "⛔ 錯誤：一般使用者查詢 Log 時，必須提供 Key Name (專案代號)。"
            return _core_log_search(key_name, keyword, lookback_minutes, start_time, end_time)

        return search_litellm_logs_user
