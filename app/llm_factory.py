# app/llm_factory.py
from langchain_openai import ChatOpenAI, AzureChatOpenAI
from langchain_aws import ChatBedrock
from langchain_classic.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from app.config import settings
from app.prompts import build_system_prompt
from app.rag.retriever import init_rag
from app.skills import discover_skills
from app.utils.logging import get_logger

logger = get_logger(__name__)


def build_llm():
    """
    根據 app/config.py 的設定，建立對應的 LLM 實體。
    """
    provider = settings.LLM_PROVIDER

    if provider == "azure":
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
        model_id=settings.BEDROCK_MODEL_ID,
        region_name=settings.AWS_REGION,
        temperature=0.2,
        max_tokens=50000
    )

    else:
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
    使用 Skills auto-discovery 自動載入工具。
    """
    # 1. 透過 Skills 自動發現機制取得工具
    tools = discover_skills(is_admin=is_admin)

    if is_admin:
        logger.info(f"🛡️  啟用 Admin 模式：共載入 {len(tools)} 個工具")
    else:
        logger.info(f"👤 啟用 User 模式：共載入 {len(tools)} 個工具")

    # 2. 初始化 RAG (載入 ChromaDB)
    init_rag()

    # 3. 建立 LLM
    llm = build_llm()

    # 4. 動態組裝 System Prompt (包含 Skills 的 SOP)
    system_prompt = build_system_prompt(is_admin=is_admin)

    # 5. 設定 Prompt Template
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        MessagesPlaceholder(variable_name="chat_history"),
        MessagesPlaceholder(variable_name="user_message"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])

    # 6. 建立 Agent
    agent = create_tool_calling_agent(llm, tools, prompt)

    # 7. 回傳執行器
    return AgentExecutor(agent=agent, tools=tools, verbose=True)


class AgentSingleton:
    """
    單例模式管理器 (Singleton Pattern) - 保留相容性
    """
    _instance = None

    @classmethod
    def get_executor(cls):
        if cls._instance is None:
            logger.info("🤖 初始化 Wuli Agent ...")
            cls._instance = build_agent_executor()
            logger.info("✅ Wuli Agent 就緒！")
        return cls._instance
