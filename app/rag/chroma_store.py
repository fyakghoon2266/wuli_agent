# app/rag/chroma_store.py
from pathlib import Path
from typing import List

import chromadb
from chromadb.utils import embedding_functions

from .models import ErrorCard


CHROMA_DIR = "./chroma_db"


def build_client() -> chromadb.PersistentClient:
    Path(CHROMA_DIR).mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=CHROMA_DIR)


def build_embedding_function():
    """
    這裡先用 Chroma 內建的 sentence-transformers embedding。
    未來你要換成 Azure / OpenAI embedding，可以在這裡改。
    """
    return embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )


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
