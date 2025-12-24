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
from app.tools.ops import search_error_cards, search_litellm_logs
from app.tools.communication import send_email_to_engineer
from app.tools.security import verify_prompt_with_guardrails

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
        model_kwargs={
            "temperature": 0.2,
        }
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

def build_agent_executor():
    """
    組裝 LLM、Tools 與 Prompt，建立 Agent 執行器。
    """
    # 1. 初始化 RAG (載入 ChromaDB)
    # 放在這裡的好處是：只有在 Agent 真正要被建立時，才會去讀取 Vector DB，加快 import 速度
    init_rag() 

    # 2. 建立 LLM
    llm = build_llm()

    # 3. 準備工具清單
    # 這裡將從不同模組 import 進來的工具組合在一起
    tools = [
        search_error_cards,           # 查手冊 (ops.py)
        search_litellm_logs,          # 查 Log (ops.py)
        send_email_to_engineer,       # 寄信 (communication.py)
        verify_prompt_with_guardrails # 查護欄 (security.py)
    ]

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
            print("🤖 初始化 Wuli Agent ...")
            cls._instance = build_agent_executor()
            print("✅ Wuli Agent 就緒！")
        return cls._instance