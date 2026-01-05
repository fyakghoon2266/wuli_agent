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
        "dbname": "litellm",
        "user": "postgres",
        "password": "sk-1234", # 建議這也改用 os.getenv("DB_PASSWORD")
        "host": "localhost",
        "port": "5432"
    }

    # Guardrails API
    GUARDRAILS_API_URL = "http://127.0.0.1:7860/"

    # git pos settings
    GITHUB_TOKEN=os.getenv("GITHUB_TOKEN")
    GITHUB_REPO_NAME=os.getenv("GITHUB_REPO_NAME")
    BASE_BRANCH=os.getenv("BASE_BRANCH")

# 實例化一個全域設定物件
settings = Config()