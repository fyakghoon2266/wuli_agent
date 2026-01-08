# app/config.py
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # LLM 設定
    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "azure").lower()
    TIMEOUT_SECONDS = 60
    
    # OpenAI / Azure / Bedrock Keys (從環境變數讀取)
    AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
    AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
    AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-05-01-preview")
    AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT")
    AZURE_OPENAI_EMBEDDING_DEPLOYMENT = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT")
    # ... (其他 Azure/Bedrock 設定) ...

    # Bedrock
    BEDROCK_MODEL_ID = os.getenv("BEDROCK_MODEL_ID")
    BEDROCK_EMBEDDING_ID = os.getenv("BEDROCK_EMBEDDING_ID")
    AWS_REGION = os.getenv("AWS_REGION")

    # Email 設定
    SMTP_SERVER = "smtp.gmail.com"
    SMTP_PORT = 587
    SENDER_EMAIL = os.getenv("SENDER_EMAIL")
    SENDER_PASSWORD = os.getenv("SENDER_PASSWORD")
    ENGINEER_EMAIL = os.getenv("ENGINEER_EMAIL")

    # jira
    JIRA_URL = os.getenv("JIRA_URL")  # 例如 https://your-company.atlassian.net
    JIRA_USER = os.getenv("JIRA_USER") # 你的 Email
    JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN") # API Token
    JIRA_PROJECT_KEY = os.getenv("JIRA_PROJECT_KEY") # 例如 "OPS" 或 "GAIA"
    JIRA_PARENT_TICKET = "GA-633"

    # DB 設定
    LITELLM_DB_CONFIG = {
        "dbname": "litellm_db",
        "user": "litellm_user",
        "password": os.getenv("DB_PASSWORD"), # 建議這也改用 os.getenv("DB_PASSWORD")
        "host": "localhost",
        "port": "5432"
    }

    # Guardrails API
    GUARDRAILS_API_URL = "http://127.0.0.1:7860/"

    # git pos settings
    GITHUB_TOKEN=os.getenv("GITHUB_TOKEN")
    GITHUB_REPO_NAME=os.getenv("GITHUB_REPO_NAME")
    BASE_BRANCH=os.getenv("BASE_BRANCH")

    AUTHORIZED_USERS = [
        ("wuli_admin", os.getenv("ADMIN_PASSWORD")),      # 維運主管
        ("wuli_master", os.getenv("user")),
    ]

    # 2. 定義誰是「管理員」 (給 Wuli 判斷權限用)
    # 只有這些帳號可以使用「寫入/修改/開單」的工具
    ADMIN_USERS = ["wuli_admin"]

    # 🔥 [清單 1] SRE 維運團隊關注的「全量模型清單」
    # 這裡列出所有運作中的模型，Wuli 會檢查它們並寫入維運週報
    # SRE_MODEL_WATCHLIST = [
    #     ("azure", "text-embedding-ada-002"),
    #     ("azure", "text-embedding-3-small"),
    #     ("azure", "gpt-4o"),
    #     ("aws", "amazon.titan-embed-text-v2:0"),
    #     ("aws", "anthropic.claude-3-5-sonnet-20241022-v2:0"),
    #     ("aws", "anthropic.claude-3-5-haiku-20241022-v1:0"),
    #     ("aws", "anthropic.claude-3-7-sonnet-20250219-v1:0"),
    #     ("aws", "openai.gpt-oss-120b-1:0"),
    #     ("aws", "openai.gpt-oss-20b-1:0"),
    #     ("aws", "llama3-1-405b-instruct-v1:0"),
    #     ("aws", "llama3-2-11b-instruct-v1:0"),
    #     ("aws", "llama3-3-70b-instruct-v1:0"),
    #     ("aws", "llama3-8b-instruct-v1:0"),
    #     ("aws", "anthropic.claude-sonnet-4-20250514-v1:0"),
    #     ("aws", "anthropic.claude-haiku-4-5-20251001-v1:0"),
    #     ("aws", "anthropic.claude-sonnet-4-5-20250929-v1:0"),
    #     ("aws", "anthropic.claude-opus-4-1-20250805-v1:0"),
    #     ("aws", "llama4-maverick-17b-instruct-v1:0"),
    #     ("aws", "llama4-scout-17b-instruct-v1:0"),
    #     ("gcp", "gemini-2.0-flash"),
    #     ("gcp", "gemini-2.5-pro"),
    #     ("gcp", "gemini-2.5-flash-lite"),
    #     ("gcp", "text-multilingual-embedding-002"),
    # ]
    SRE_MODEL_WATCHLIST = [

        ("aws", "Claude 3.5 Sonnet v1"),
        ("aws", "Claude 3.5 Haiku"),
        ("aws", "Claude 3.5 Sonnet v2"),
        ("aws", "Claude 3.7 Sonnet v1"),
        ("aws", "gpt oss 120b "),
    ]

    # 🔥 [清單 2] 專案經理 (PM) 關注的通知清單
    # 針對特定專案，如果該專案底下的模型快過期，才寄信給該 PM
    PM_PROJECT_WATCHLIST = [
        {
            "project_name": "Cub search",
            "pm_name": "王儀茹 Ada",
            "pm_emails": ["NT96931@cathaybk.com.tw","NT92018@cathaybk.com.tw"],
            "models": [
                ("aws", "Claude 3.7 Sonnet"), 
                ("aws", "titan embed text V2")
            ]
        },
        {
            "project_name": "理專AI助手 (Call-Record Summary)",
            "pm_name": "莊文遠 Brain",
            "pm_emails": ["NT89356@cathaybk.com.tw","NT92018@cathaybk.com.tw"],
            "models": [
                ("aws", "Claude 3.5 Sonnet v2")
            ]
        },
        # 可以繼續新增更多專案...
    ]

# 實例化一個全域設定物件
settings = Config()