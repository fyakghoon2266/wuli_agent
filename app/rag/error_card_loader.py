# app/rag/error_card_loader.py
import os
from pathlib import Path
from typing import List, Tuple

import yaml

from .models import ErrorCard


def split_frontmatter(text: str) -> Tuple[dict, str]:
    """
    簡單解析 `---` YAML frontmatter，回傳 (meta, body_text)。
    """
    text = text.lstrip()
    if not text.startswith("---"):
        return {}, text

    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text

    _, yaml_part, body = parts
    meta = yaml.safe_load(yaml_part) or {}
    return meta, body.strip()


def load_error_cards(root_dir: str) -> List[ErrorCard]:
    """
    掃描 error_docs/ 底下所有 .md，轉成 ErrorCard list。
    """
    cards: List[ErrorCard] = []
    root_path = Path(root_dir)

    if not root_path.exists():
        return []

    for path in root_path.rglob("*.md"):
        raw = path.read_text(encoding="utf-8")
        meta, body = split_frontmatter(raw)

        # 給些合理預設值
        card = ErrorCard(
            id=meta.get("id", path.stem),
            component=meta.get("component", "generic"),
            category=meta.get("category", "error"),
            http_status=meta.get("http_status"),
            error_code=meta.get("error_code"),
            severity=meta.get("severity", "medium"),
            tags=meta.get("tags", []) or [],
            patterns=meta.get("patterns", []) or [],
            path=str(path),
            content=body,
        )
        cards.append(card)

    return cards
