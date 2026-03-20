# app/rag/retriever.py
import os
from typing import List, Tuple

# 引入 LangChain 的 Document Loader
from langchain_community.document_loaders import DirectoryLoader, TextLoader

from .models import ErrorCard
from .error_card_loader import load_error_cards
from .chroma_store import index_error_cards, get_collection

# 定義目錄名稱
ERROR_DOCS_DIR = "./error_docs"
KNOWLEDGE_DOCS_DIR = "./knowledge_docs"  # 🌟 新增：一般知識庫目錄
COLLECTION_NAME = "error_cards"


def load_knowledge_docs(directory: str) -> List[ErrorCard]:
    """
    🌟 新增：讀取一般知識文件，並將它們「偽裝」成 ErrorCard 物件，
    以便後續能夠統一存入 ChromaDB。
    """
    if not os.path.exists(directory):
        return []
        
    # 使用 TextLoader 來讀取 .md 檔案
    loader = DirectoryLoader(directory, glob="**/*.md", loader_cls=TextLoader)
    documents = loader.load()
    
    knowledge_cards = []
    for doc in documents:
        # 取得檔名當作 ID (例如 guardrail_architecture.md -> guardrail_architecture)
        file_name = os.path.basename(doc.metadata.get("source", "unknown"))
        doc_id = os.path.splitext(file_name)[0]
        
        # 將一般文件封裝成 ErrorCard 格式
        card = ErrorCard(
            id=f"KNOWLEDGE-{doc_id}",
            component="knowledge",
            category="architecture",
            http_status=None,
            error_code=None,
            severity="info",
            tags=["architecture", "knowledge"],
            # 這裡加上一些通用的 patterns，這樣 rule-based 也能撈到它
            patterns=["架構", "護欄", "gateway", "litellm", "流程", "怎麼運作"], 
            path=doc.metadata.get("source", ""),
            content=doc.page_content,
        )
        knowledge_cards.append(card)
        
    return knowledge_cards


def init_rag():
    """
    啟動或重建索引用：
    1. 從 ERROR_DOCS_DIR 載入所有 Error Card
    2. 從 KNOWLEDGE_DOCS_DIR 載入一般知識文件
    3. 合併後重建 Chroma collection（覆蓋舊的）
    """
    # 載入錯誤卡片
    error_cards = load_error_cards(ERROR_DOCS_DIR)
    
    # 載入一般知識文件
    knowledge_cards = load_knowledge_docs(KNOWLEDGE_DOCS_DIR)
    
    # 合併兩者
    all_cards = error_cards + knowledge_cards
    
    # 統一送入 ChromaDB 建立索引
    collection = index_error_cards(all_cards, COLLECTION_NAME)
    
    return all_cards, collection


def rule_based_match(query: str, k: int = 3) -> List[ErrorCard]:
    """
    第一層：使用 ErrorCard.patterns 做 rule-based 匹配。
    只要 patterns 中任一字串出現在 query 內，就視為命中。
    """
    # 同時載入兩邊的檔案進行即時比對
    cards = load_error_cards(ERROR_DOCS_DIR) + load_knowledge_docs(KNOWLEDGE_DOCS_DIR)

    hits: List[ErrorCard] = []
    q = query.lower()

    for card in cards:
        if not card.patterns:
            continue
        for p in card.patterns:
            if not p:
                continue
            if p.lower() in q:
                hits.append(card)
                break  # 一張卡片只算一次命中

    return hits[:k]


def retrieve_cards(query: str, k: int = 3) -> List[Tuple[str, str]]:
    """
    對外的檢索介面：
    1. 先用 rule-based pattern match（patterns）
    2. 若沒有命中，再 fallback 到 Chroma 語意搜尋
    3. 回傳 [(card_id, card_content), ...]
    """
    query = (query or "").strip()
    if not query:
        return []

    # --- 第一層：rule-based patterns ---
    rb_hits = rule_based_match(query, k=k)
    if rb_hits:
        return [(c.id, c.content) for c in rb_hits]

    # --- 第二層：fallback 到 embedding 檢索 ---
    collection = get_collection(COLLECTION_NAME)

    res = collection.query(query_texts=[query], n_results=k)
    ids = res.get("ids", [[]])[0]
    docs = res.get("documents", [[]])[0]

    return list(zip(ids, docs))