# app/rag/retriever.py
from typing import List, Tuple

from .models import ErrorCard
from .error_card_loader import load_error_cards
from .chroma_store import index_error_cards, get_collection

# error_docs 目錄 & collection 名稱
ERROR_DOCS_DIR = "./error_docs"
COLLECTION_NAME = "error_cards"


def init_rag():
    """
    啟動或重建索引用：
    1. 從 ERROR_DOCS_DIR 載入所有 Error Card
    2. 重建 Chroma collection（覆蓋舊的）
    """
    cards = load_error_cards(ERROR_DOCS_DIR)
    collection = index_error_cards(cards, COLLECTION_NAME)
    return cards, collection


def rule_based_match(query: str, k: int = 3) -> List[ErrorCard]:
    """
    第一層：使用 ErrorCard.patterns 做 rule-based 匹配。
    只要 patterns 中任一字串出現在 query 內，就視為命中。

    ⚠️ 不再使用全域快取，每次都從 error_docs/ 重新載入，
       這樣新增 / 修改卡片不需要重啟服務就會生效。
    """
    cards = load_error_cards(ERROR_DOCS_DIR)

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

