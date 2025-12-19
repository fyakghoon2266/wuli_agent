# app/llm.py
import os
from typing import List, Dict, Any

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

# 未來如果有 LiteLLM DB 工具，就加在這裡
# @tool
# def check_litellm_logs(user_id: str): ...


# ===================== 建立 Agent =====================

def build_agent_executor():
    # 1. 工具清單：加入 send_email_to_engineer
    tools = [search_error_cards, send_email_to_engineer] 

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