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

@tool
def search_litellm_logs(
    keyword: str = "",
    lookback_minutes: int = 60,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None
):
    """
    【LiteLLM Log 查詢工具 - 自動校正時區版】
    
    功能：查詢 Log 並自動將 UTC 時間轉換為台北時間 (+8) 顯示。
    """
    try:
        conn = psycopg2.connect(**settings.LITELLM_DB_CONFIG)
        cursor = conn.cursor()

        # [重點 1] 在 SQL 查詢欄位時，直接 +8 小時，讓回傳給 Python 的就是台北時間
        base_sql = """
        SELECT 
            ("startTime" + INTERVAL '8 hours') as local_time,
            "user",
            messages, 
            proxy_server_request, 
            response
        FROM "LiteLLM_SpendLogs"
        """
        
        conditions = []
        params = []

        # --- 動態決定查詢條件 ---
        
        # 這裡的邏輯是：
        # 資料庫裡的 startTime 是 UTC (02:00)。
        # 加上 8 小時後變成台北時間 (10:00)。
        # 我們拿這個「變換後的時間」來跟使用者的條件 (10:00) 做比較。

        if start_time:
            # 絕對時間查詢
            conditions.append('("startTime" + INTERVAL \'8 hours\') >= %s')
            params.append(start_time)
            
            if end_time:
                conditions.append('("startTime" + INTERVAL \'8 hours\') <= %s')
                params.append(end_time)
                
        else:
            # 相對時間查詢 (最近 N 分鐘)
            # 因為你的 DB 已經設成 Asia/Taipei，所以 NOW() 是台北時間
            # 我們拿 (UTC資料 + 8) 來跟 (台北NOW) 比較，這樣單位就統一了
            conditions.append('("startTime" + INTERVAL \'8 hours\') >= NOW() - INTERVAL %s') 
            params.append(f"{lookback_minutes} minutes")

        # 組合 WHERE 子句
        if conditions:
            base_sql += " WHERE " + " AND ".join(conditions)
        
        # 排序 (用原始 startTime 排就好，結果一樣)
        base_sql += ' ORDER BY "startTime" DESC LIMIT 15;'

        # 執行查詢
        cursor.execute(base_sql, tuple(params))
        rows = cursor.fetchall()
        
        if not rows:
            return f"📭 查詢完成，但在指定區間內沒有找到 Log (已自動校正 +8 時區)。"

        result_text = []
        for row in rows:
            t_start, user_id, msgs, proxy_req, resp = row
            
            # t_start 現在已經是 Postgres 算好的台北時間了，直接轉字串
            # 如果它是 datetime 物件，轉成乾淨的字串格式
            if isinstance(t_start, datetime.datetime):
                t_start_str = t_start.strftime("%Y-%m-%d %H:%M:%S")
            else:
                t_start_str = str(t_start)

            # --- 解析 Prompt (Input) ---
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

            # 關鍵字過濾
            if keyword:
                search_target = f"{str(user_id)} {prompt_content}"
                if keyword.lower() not in search_target.lower():
                    continue

            # --- 解析 Response (Output) ---
            output_content = "Success"
            if isinstance(resp, dict):
                if 'error' in resp:
                    output_content = f"❌ Error: {resp['error']}"
                else:
                    choices = resp.get('choices', [])
                    if choices:
                        output_content = f"✅ Reply: {choices[0]['message']['content'][:50]}..."

            # 格式化輸出
            log_entry = (
                f"⏰ 時間 (Taipei): {t_start_str}\n"
                f"👤 User: {user_id}\n"
                f"📝 Prompt: {prompt_content[:200]}...\n"
                f"📤 狀態: {output_content}\n"
                "------------------------------------------------"
            )
            result_text.append(log_entry)

        conn.close()
        
        if not result_text:
            return f"已搜尋資料庫，但在過濾關鍵字 '{keyword}' 後沒有符合的紀錄。"
            
        return "\n".join(result_text)

    except Exception as e:
        return f"💥 資料庫查詢失敗: {str(e)}"