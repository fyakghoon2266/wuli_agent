import psycopg2
import datetime
from typing import Optional
from langchain.tools import tool
from app.config import settings
from app.rag.retriever import retrieve_cards

@tool
def search_error_cards(query: str):
    """
    這是一個「維運手冊/錯誤卡片搜尋工具」。
    當使用者詢問關於系統錯誤代碼 (Error Code)、Log 內容、GAIA 平台架構、
    護欄 (Guardrails)、Proxy 設定、Token 認證、504 Timeout、407 Error
    或任何系統異常排查時，**必須**使用此工具來查詢內部文件。
    
    輸入 query 應該是使用者遇到的錯誤訊息或問題關鍵字。
    """
    # 這裡直接呼叫你原本的 retrieve_cards
    hits = retrieve_cards(query, k=3)
    
    if not hits:
        return "搜尋維運手冊後，沒有發現直接相關的說明。"

    context_blocks = []
    for idx, (card_id, content) in enumerate(hits, start=1):
        context_blocks.append(f"[Result {idx}: {card_id}]\n{content}")
    
    return "\n\n".join(context_blocks)

# ==========================================
# 核心邏輯 (共用函式，不掛 @tool)
# ==========================================
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

        # 🔥 修正 1: 多 SELECT "api_key_alias" (對應 UI 的 Key Name)
        # LiteLLM 的 "user" 欄位通常存的是 internal user id (default_user_id)
        base_sql = """
        SELECT 
            ("startTime" + INTERVAL '8 hours') as local_time,
            "user",
            "api_key_alias", 
            messages, 
            proxy_server_request, 
            response
        FROM "LiteLLM_SpendLogs"
        """
        
        conditions = []
        params = []

        # 🔥 修正 2: 過濾條件改為比對 "api_key_alias"
        if key_name:
            conditions.append('"api_key_alias" = %s')
            params.append(key_name)

        # 時間條件
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
            # 🔥 修正 3: 解包時多一個欄位
            t_start, user_id, api_key_alias, msgs, proxy_req, resp = row
            
            # 優先顯示 Alias，如果沒有 Alias 才顯示 user_id
            display_project_name = api_key_alias if api_key_alias else f"{user_id} (無 Alias)"

            if isinstance(t_start, datetime.datetime):
                t_start_str = t_start.strftime("%Y-%m-%d %H:%M:%S")
            else:
                t_start_str = str(t_start)

            # 解析 Prompt
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

            # 關鍵字過濾 (同時比對 alias 和 user_id)
            if keyword:
                search_target = f"{str(user_id)} {str(api_key_alias)} {prompt_content}"
                if keyword.lower() not in search_target.lower():
                    continue

            # 解析 Response
            output_content = "Success"
            if isinstance(resp, dict):
                if 'error' in resp:
                    output_content = f"❌ Error: {resp['error']}"
                else:
                    choices = resp.get('choices', [])
                    if choices:
                        output_content = f"✅ Reply: {choices[0]['message']['content'][:50]}..."

            # 🔥 修正 4: 顯示正確的 Key Name
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


# ==========================================
# 工具定義 (雙軌制)
# ==========================================

@tool("search_litellm_logs_admin")
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


@tool("search_litellm_logs_user")
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