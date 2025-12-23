# app/llm.py
import os
from typing import List, Dict, Any
import json
import psycopg2 # 新增這個
import datetime

from typing import Optional

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from dotenv import load_dotenv
load_dotenv()

from langchain_core.messages import (
    SystemMessage,
    HumanMessage,
    AIMessage,
    BaseMessage,
)
from langchain_openai import ChatOpenAI, AzureChatOpenAI
from langchain_aws import ChatBedrock

# 引入 Agent 相關套件
from langchain.tools import tool
# from langchain.agents import create_tool_calling_agenc
from langchain_classic.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from gradio_client import Client

from .rag.retriever import retrieve_cards, init_rag

# ===================== LLM Provider 設定 =====================
# (保留你原本的設定邏輯，完全不動)
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "azure").lower()
TIMEOUT_SECONDS = 60

# --- OpenAI ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")

# --- Bedrock ---
BEDROCK_MODEL_ID = os.getenv(
    "BEDROCK_MODEL_ID",
    "anthropic.claude-3-5-sonnet-20241022-v2:0",
)
AWS_REGION = os.getenv("AWS_REGION", "us-west-2")

# --- Azure OpenAI ---
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-05-01-preview")
AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT")

# 設定你的 Email 資訊 (建議之後改放到 .env)
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SENDER_EMAIL = os.getenv("SENDER_EMAIL")  # Wuli 的發信帳號
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD") # 應用程式密碼
ENGINEER_EMAIL = os.getenv("ENGINEER_EMAIL") # 值班工程師的 Email

LITELLM_DB_CONFIG = {
    "dbname": "litellm",
    "user": "postgres",
    "password": "sk-1234",
    "host": "localhost", 
    "port": "5432"
}


def build_llm():
    # (保留原本的 build_llm 邏輯，這裡省略以節省篇幅，請直接用你原本的程式碼)
    if LLM_PROVIDER == "azure":
        if not (AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY and AZURE_OPENAI_DEPLOYMENT):
             raise RuntimeError("LLM_PROVIDER=azure，但 AZURE_OPENAI_* 尚未完整設定。")
        return AzureChatOpenAI(
            azure_endpoint=AZURE_OPENAI_ENDPOINT,
            api_key=AZURE_OPENAI_API_KEY,
            api_version=AZURE_OPENAI_API_VERSION,
            azure_deployment=AZURE_OPENAI_DEPLOYMENT,
            timeout=TIMEOUT_SECONDS,
            temperature=0.2,
            streaming=True # 建議開啟 Streaming
        )

    if LLM_PROVIDER == "bedrock":
        return ChatBedrock(
            model_id=BEDROCK_MODEL_ID,
            region_name=AWS_REGION,
            timeout=TIMEOUT_SECONDS,
            temperature=0.2,
            streaming=True # 建議開啟 Streaming
        )

    # 預設 OpenAI
    if not OPENAI_API_KEY:
        raise RuntimeError("LLM_PROVIDER=openai，但 OPENAI_API_KEY 未設定。")

    return ChatOpenAI(
        api_key=OPENAI_API_KEY,
        model=OPENAI_MODEL,
        timeout=TIMEOUT_SECONDS,
        temperature=0.2,
        streaming=True # 建議開啟 Streaming
    )


LLM = build_llm()

# 啟動時先把 error_docs 建進 Chroma
ERROR_CARDS, ERROR_COLLECTION = init_rag()


# ===================== 定義 Tools (工具) =====================

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
        # 簡單驗證 Email 格式 (防呆)
        if "@" not in user_email or "." not in user_email:
            return f"❌ 寄信失敗：提供的聯絡資訊 '{user_email}' 看起來不像有效的 Email 格式。請要求使用者提供正確的信箱以便寄送副本。"

        # 建立郵件內容
        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL
        msg['To'] = ENGINEER_EMAIL
        msg['Cc'] = user_email  # <--- 關鍵修改：設定副本給使用者
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

        # 連線 SMTP Server 寄信
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        
        # 注意：send_message 的收件人清單必須包含 To 和 Cc 的所有人
        recipients = [ENGINEER_EMAIL, user_email]
        server.send_message(msg, to_addrs=recipients)
        
        server.quit()
        
        return f"✅ 信件已成功寄出！\n收件人：工程師\n副本(CC)：{user_name} ({user_email})\n請使用者去收信確認喔！"
        
    except Exception as e:
        return f"❌ 寄信失敗：{str(e)}"

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
        conn = psycopg2.connect(**LITELLM_DB_CONFIG)
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

from gradio_client import Client # <--- 記得在最上面加這個

# ... (其他的 import 和工具) ...

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
        # 連線到你的 Guardrails API
        client = Client("https://35.78.175.148/guardrails/", ssl_verify=False)
        
        # 呼叫預測
        result = client.predict(
            user_text=prompt_content,
            api_name="/check_all"
        )
        
        # result 是一個 tuple，包含 (LLM檢查結果, 關鍵字檢查結果, 正則檢查結果)
        # 我們把它組合成清楚的字串回傳給 Wuli
        formatted_result = (
            f"🛡️ 【檢查報告】 針對內容: '{prompt_content[:50]}...'\n"
            f"1. {result[0]}\n"
            f"2. {result[1]}\n"
            f"3. {result[2]}\n"
        )
        return formatted_result

    except Exception as e:
        return f"💥 呼叫護欄 API 失敗: {str(e)}"

# 未來如果有 LiteLLM DB 工具，就加在這裡
# @tool
# def check_litellm_logs(user_id: str): ...


# ===================== 建立 Agent =====================

def build_agent_executor():
    # 1. 工具清單：加入 send_email_to_engineer
    tools = [
        search_error_cards, 
        send_email_to_engineer,
        search_litellm_logs, 
        verify_prompt_with_guardrails] 

    # 2. Agent Prompt (保持不變)
    prompt = ChatPromptTemplate.from_messages([
        ("system", "{system_message}"), 
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])

    # 3. 建立 Agent
    agent = create_tool_calling_agent(LLM, tools, prompt)

    # 4. 建立 Executor
    return AgentExecutor(agent=agent, tools=tools, verbose=True)

# 建立全域的 Executor 實體
AGENT_EXECUTOR = build_agent_executor()