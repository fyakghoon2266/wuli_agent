# app/rag/models.py
from pydantic import BaseModel
from typing import List, Optional


class ErrorCard(BaseModel):
    id: str
    component: str                  # gateway / guardrail / upstream_llm / ...
    category: str                   # error / block / warning / info
    http_status: Optional[int] = None
    error_code: Optional[str] = None
    severity: Optional[str] = None
    tags: List[str] = []
    patterns: List[str] = []        # 關鍵字 / regex（先當關鍵字用）
    path: Optional[str] = None      # 檔案路徑（方便 debug）
    content: str                    # Markdown 正文（給 LLM 當 context）
