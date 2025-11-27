```css
llm_infra_helper/
├── .env                  # 你的 Azure / OpenAI / Bedrock 等設定（dotenv 已經用上）
├── error_docs/           # Error Card Markdown 放這裡（之後維運同事只碰這裡）
│   ├── gateway/
│   │   └── ERR-GW-0001-rate-limit.md
│   ├── guardrail/
│   │   └── EVT-GR-0001-block.md
│   └── generic/
│       └── ERR-GN-0001-unknown.md
├── chroma_db/            # Chroma 的持久化資料夾（程式會自動建立）
└── app/
    ├── __init__.py
    ├── main.py           # Gradio 入口（原本那支檔案的 UI 部分）
    ├── llm.py            # build_llm + call_llm_with_rag（你原本的邏輯搬來＋RAG）
    └── rag/
        ├── __init__.py
        ├── models.py         # ErrorCard 結構
        ├── error_card_loader.py  # 讀 error_docs/*.md + frontmatter
        ├── chroma_store.py   # 建立 Chroma vector store
        └── retriever.py      # 封裝「給問題 → 找對應 card」的 API

```


## app啟動方式

```bash
python -m app.main
```

## 重新載入error card方式：

```bash
python -m scripts.rebuild_index
```