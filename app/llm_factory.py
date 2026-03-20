# app/llm_factory.py
from langchain_openai import ChatOpenAI, AzureChatOpenAI
from langchain_aws import ChatBedrock
# 注意：如果你使用的是新版 langchain，可能需要改為 from langchain.agents import ...
from langchain_classic.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

# 引入配置與文案
from app.config import settings
from app.prompts import SYSTEM_PROMPT

# 引入 RAG 初始化函式
from app.rag.retriever import init_rag

# 引入拆分後的工具 (請確保這些檔案已建立)
from app.tools.ops import search_error_cards, search_litellm_logs_admin, search_litellm_logs_user
from app.tools.communication import send_email_to_engineer
from app.tools.security import verify_prompt_with_guardrails
from app.tools.search import get_search_tool
from app.tools.git_ops import propose_new_error_card
from app.tools.incident import log_incident_for_weekly_report
from app.tools.selfie import send_wuli_photo
from app.tools.jira_ops import report_issue_to_jira
from app.tools.lifecycle import check_model_eol
from app.utils.logging import get_logger

logger = get_logger(__name__)

def build_llm():
    """
    根據 app/config.py 的設定，建立對應的 LLM 實體。
    """
    provider = settings.LLM_PROVIDER
    
    if provider == "azure":
        # 檢查必要參數
        if not (settings.AZURE_OPENAI_ENDPOINT and settings.AZURE_OPENAI_API_KEY and settings.AZURE_OPENAI_DEPLOYMENT):
             raise RuntimeError("LLM_PROVIDER=azure，但 AZURE_OPENAI_* 相關設定不完整。")
             
        return AzureChatOpenAI(
            azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
            api_key=settings.AZURE_OPENAI_API_KEY,
            api_version=settings.AZURE_OPENAI_API_VERSION,
            azure_deployment=settings.AZURE_OPENAI_DEPLOYMENT,
            timeout=settings.TIMEOUT_SECONDS,
            temperature=0.2,
            streaming=True
        )

    elif provider == "bedrock":
        return ChatBedrock(
        model_id=settings.BEDROCK_MODEL_ID,  # 或者用 haiku / opus
        region_name=settings.AWS_REGION,  # 或是你模型開通的區域，如 us-west-2
        temperature=0.2,
        max_tokens=50000
    )

    else: # 預設為 OpenAI
        if not settings.OPENAI_API_KEY:
            raise RuntimeError("LLM_PROVIDER=openai，但 OPENAI_API_KEY 未設定。")

        return ChatOpenAI(
            api_key=settings.OPENAI_API_KEY,
            model=settings.OPENAI_MODEL,
            timeout=settings.TIMEOUT_SECONDS,
            temperature=0.2,
            streaming=True
        )

def build_agent_executor(is_admin: bool = False):
    """
    組裝 LLM、Tools 與 Prompt，建立 Agent 執行器。
    """

    """
    根據是否為管理員，回傳不同權限的 Agent
    """
    
    if is_admin:
        log_tool = search_litellm_logs_admin
    else:
        log_tool = search_litellm_logs_user
    
    # 🔥 強制將工具名稱統一，這樣 System Prompt 不需要為了不同人寫兩套
    log_tool.name = "search_litellm_logs"

    # 2. 定義基礎工具
    base_tools = [
        search_error_cards,            
        log_tool,                      # <--- 這裡放動態決定的工具
        get_search_tool,               
        verify_prompt_with_guardrails, 
        send_wuli_photo,               
        check_model_eol,              
        send_email_to_engineer,        
    ]

    # 2. 定義管理員工具 (只有 Admin 能用：寫入、發信、開票)
    admin_tools = [
        propose_new_error_card,        # 新增錯誤知識庫
        log_incident_for_weekly_report,# 寫週報
        report_issue_to_jira           # 開 Jira 單
    ]

    # 3. 根據權限組合工具箱
    if is_admin:
        logger.info("🛡️  啟用 Admin 模式：授權所有高風險工具")
        tools = base_tools + admin_tools
    else:
        logger.info("👤 啟用 User 模式：僅授權唯讀/查詢工具")
        tools = base_tools
    # 1. 初始化 RAG (載入 ChromaDB)
    # 放在這裡的好處是：只有在 Agent 真正要被建立時，才會去讀取 Vector DB，加快 import 速度
    init_rag() 

    # 2. 建立 LLM
    llm = build_llm()

    # 4. 設定 Prompt Template
    # 使用 ChatPromptTemplate 讓結構更清晰
    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT), 
        MessagesPlaceholder(variable_name="chat_history"),
        # ("human", "{input}"),
        MessagesPlaceholder(variable_name="user_message"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])

    # 5. 建立 Agent
    # create_tool_calling_agent 是 LangChain 針對支援 Function Calling 模型 (GPT/Claude) 的最佳實作
    agent = create_tool_calling_agent(llm, tools, prompt)

    # 6. 回傳執行器
    return AgentExecutor(agent=agent, tools=tools, verbose=True)


class AgentSingleton:
    """
    單例模式管理器 (Singleton Pattern)
    確保整個應用程式生命週期中，AgentExecutor 只會被初始化一次。
    避免重複連線資料庫或重複載入 RAG 模型。
    """
    _instance = None
    
    @classmethod
    def get_executor(cls):
        if cls._instance is None:
            logger.info("🤖 初始化 Wuli Agent ...")
            cls._instance = build_agent_executor()
            logger.info("✅ Wuli Agent 就緒！")
        return cls._instance