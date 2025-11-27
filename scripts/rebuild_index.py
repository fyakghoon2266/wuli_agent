# scripts/rebuild_index.py
from app.rag.retriever import init_rag

if __name__ == "__main__":
    cards, collection = init_rag()
    print(f"Reindexed {len(cards)} error cards into collection '{collection.name}'")