# app/llm.py
import os
from typing import List, Dict

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

from .rag.retriever import retrieve_cards, init_rag


# ===================== LLM Provider 設定 =====================

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


def build_llm():
    if LLM_PROVIDER == "azure":
        if not (AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY and AZURE_OPENAI_DEPLOYMENT):
            raise RuntimeError(
                "LLM_PROVIDER=azure，但 AZURE_OPENAI_* 尚未完整設定。"
            )
        return AzureChatOpenAI(
            azure_endpoint=AZURE_OPENAI_ENDPOINT,
            api_key=AZURE_OPENAI_API_KEY,
            api_version=AZURE_OPENAI_API_VERSION,
            azure_deployment=AZURE_OPENAI_DEPLOYMENT,
            timeout=TIMEOUT_SECONDS,
            temperature=0.2,
            streaming=True
        )

    if LLM_PROVIDER == "bedrock":
        return ChatBedrock(
            model_id=BEDROCK_MODEL_ID,
            region_name=AWS_REGION,
            timeout=TIMEOUT_SECONDS,
            temperature=0.2,
        )

    # 預設 OpenAI
    if not OPENAI_API_KEY:
        raise RuntimeError("LLM_PROVIDER=openai，但 OPENAI_API_KEY 未設定。")

    return ChatOpenAI(
        api_key=OPENAI_API_KEY,
        model=OPENAI_MODEL,
        timeout=TIMEOUT_SECONDS,
        temperature=0.2,
    )


LLM = build_llm()

# 啟動時先把 error_docs 建進 Chroma（也會更新 retriever 裡的 CARDS）
ERROR_CARDS, ERROR_COLLECTION = init_rag()


# ===================== messages_state -> LangChain messages =====================

def to_langchain_messages(messages_state: List[Dict[str, str]]) -> List[BaseMessage]:
    lc_messages: List[BaseMessage] = []
    for m in messages_state:
        role = m["role"]
        content = m["content"]
        if role == "system":
            lc_messages.append(SystemMessage(content=content))
        elif role == "user":
            lc_messages.append(HumanMessage(content=content))
        elif role == "assistant":
            lc_messages.append(AIMessage(content=content))
        else:
            lc_messages.append(HumanMessage(content=content))
    return lc_messages


# ===================== 主流程：帶 RAG 的 LLM 呼叫 =====================

def call_llm_with_rag(messages_state: List[Dict[str, str]]) -> str:
    """
    簡單版 RAG 流程：

    1. 從 messages_state 抓出最後一輪 user input
    2. 用 retrieve_cards() 找相關 Error Cards
       - 先用 patterns 做 rule-based 點對點匹配
       - 若沒命中，再 fallback 到 Chroma 語意搜尋
    3. 把命中的卡片內容組成 context，一起塞到最後一輪 user prompt 裡
    4. 呼叫 LLM 產生回答
    """
    if not messages_state:
        return "[系統錯誤] messages_state 為空。"

    # 找最後一個 user 訊息
    last_user = None
    for m in reversed(messages_state):
        if m["role"] == "user":
            last_user = m["content"]
            break

    if last_user is None:
        return "[系統錯誤] 找不到 user 訊息。"

    # === 1) 用 RAG 檢索 Error Cards ===
    hits = retrieve_cards(last_user, k=3)

    context_blocks = []
    for idx, (card_id, content) in enumerate(hits, start=1):
        context_blocks.append(f"[Error Card {idx}: {card_id}]\n{content}")
    context_text = "\n\n".join(context_blocks)

    # === 2) 準備要送給 LLM 的 messages ===

    # 先把歷史（不含最後一輪 user）轉成 LangChain messages
    history = [
        m for m in messages_state
        if not (m["role"] == "user" and m["content"] == last_user)
    ]
    lc_messages = to_langchain_messages(history)

    # 重新組裝最後一輪 user prompt：把 context + 問題打包進去
    if context_text:
        user_prompt = (
            "以下是幾張內部的 Error Cards（錯誤說明卡片），內容包含錯誤現象、成因與建議處置方式：\n\n"
            f"{context_text}\n\n"
            "請優先根據這些 Error Cards 的內容，判斷使用者遇到的是哪一類問題，"
            "並用清楚的步驟給出建議。如果 Error Cards 不完全適用，可以再輔以你的常識補充說明。\n\n"
            f"使用者的實際問題／錯誤訊息如下：\n{last_user}"
        )
    else:
        # 沒有命中任何卡片，就當作一般技術問答
        user_prompt = (
            "目前沒有找到明確對應的 Error Card，"
            "請根據你對 LLM 基礎建設與一般工程實務的理解，協助回答這個問題：\n\n"
            f"{last_user}"
        )

    lc_messages.append(HumanMessage(content=user_prompt))

    # === 3) 呼叫 LLM ===
    try:
        result = LLM.invoke(lc_messages)
    except Exception as e:
        return f"[LLM 呼叫失敗] {type(e).__name__}: {e}"

    return str(getattr(result, "content", result))
