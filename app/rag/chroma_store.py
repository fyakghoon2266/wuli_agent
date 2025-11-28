# app/rag/chroma_store.py
from pathlib import Path
from typing import List
import os

from dotenv import load_dotenv
load_dotenv()

import chromadb
from langchain_openai import OpenAIEmbeddings, AzureOpenAIEmbeddings
from chromadb.utils import embedding_functions

from .models import ErrorCard


CHROMA_DIR = "./chroma_db"

class LangChainOpenAIEmbeddingFunction(embedding_functions.EmbeddingFunction):
    """
    用 langchain-openai 的 Embeddings 當作 Chroma 的 embedding_function。
    會根據環境變數決定走 OpenAI 還是 Azure OpenAI。
    """

    def __init__(self) -> None:
        provider = os.getenv("EMBEDDING_PROVIDER", "").lower() or os.getenv(
            "LLM_PROVIDER", "azure"
        ).lower()

        if provider == "azure":
            # 這些環境變數請照你實際的 Azure 設定
            self._emb = AzureOpenAIEmbeddings(
                azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
                api_key=os.environ["AZURE_OPENAI_API_KEY"],
                api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-05-01-preview"),
                azure_deployment=os.environ[
                    "AZURE_OPENAI_EMBEDDING_DEPLOYMENT"
                ],  # 建議用獨立的 embedding deployment
            )
        else:
            # 預設走 OpenAI 公有雲
            self._emb = OpenAIEmbeddings(
                api_key=os.environ["OPENAI_API_KEY"],
                model=os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"),
            )

    def __call__(self, texts: List[str]) -> List[List[float]]:
        # langchain 的 embed_documents 本來就吃 List[str]、回 List[List[float]]
        return self._emb.embed_documents(texts)


def build_client() -> chromadb.PersistentClient:
    Path(CHROMA_DIR).mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=CHROMA_DIR)


# def build_embedding_function():
#     """
#     這裡先用 Chroma 內建的 sentence-transformers embedding。
#     未來你要換成 Azure / OpenAI embedding，可以在這裡改。
#     """
#     return embedding_functions.SentenceTransformerEmbeddingFunction(
#         model_name="sentence-transformers/all-MiniLM-L6-v2"
#     )

def build_embedding_function():
    """
    改用 langchain-openai 的 Embeddings：
    - EMBEDDING_PROVIDER=azure 時用 AzureOpenAIEmbeddings
    - 其他情況預設用 OpenAIEmbeddings
    """
    return LangChainOpenAIEmbeddingFunction()


def index_error_cards(cards: List[ErrorCard], collection_name: str = "error_cards"):
    client = build_client()
    emb_fn = build_embedding_function()

    try:
        collection = client.get_collection(collection_name, embedding_function=emb_fn)
    except Exception:
        collection = client.create_collection(collection_name, embedding_function=emb_fn)

    existing = collection.count()
    if existing > 0:
        collection.delete(ids=collection.get()["ids"])

    ids = []
    texts = []
    metadatas = []

    for card in cards:
        ids.append(card.id)
        texts.append(card.content)

        meta = {
            "id": card.id,
            "component": card.component,
            "category": card.category,
            "severity": card.severity or "",
            "tags": ",".join(card.tags) if card.tags else "",
            "path": card.path or "",
        }

        if card.http_status is not None:
            meta["http_status"] = int(card.http_status)
        if card.error_code is not None:
            meta["error_code"] = str(card.error_code)

        metadatas.append(meta)

    if ids:
        collection.add(ids=ids, documents=texts, metadatas=metadatas)

    return collection



def get_collection(collection_name: str = "error_cards"):
    client = build_client()
    emb_fn = build_embedding_function()
    return client.get_collection(collection_name, embedding_function=emb_fn)
