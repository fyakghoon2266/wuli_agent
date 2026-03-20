# scripts/rebuild_index.py
from app.rag.retriever import init_rag
from app.utils.logging import get_logger

logger = get_logger(__name__)

if __name__ == "__main__":
    cards, collection = init_rag()
    logger.info(f"Reindexed {len(cards)} error cards into collection '{collection.name}'")