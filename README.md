```css
WULI_AGENT/
├── .env                  # 環境變數 (機密)
├── requirements.txt
└── app/
    ├── __init__.py
    ├── config.py         # [新建] 集中管理所有全域變數與設定
    ├── prompts.py        # [新建] 集中管理 System Prompt 與文案
    ├── llm_factory.py    # [重構 llm.py] 專注於產生 LLM 與 Agent 實體
    ├── main.py           # 程式入口 (Entry Point)
    ├── tools/            # [新建] 工具包，將 Tool 拆開
    │   ├── __init__.py
    │   ├── ops.py        # 查 Log, 查錯誤卡片
    │   ├── communication.py # 寄信
    │   └── security.py   # 護欄檢查
    ├── ui/               # [新建] UI 相關
    │   ├── __init__.py
    │   ├── layout.py     # Gradio 介面建構
    │   └── styles.py     # CSS 樣式
    ├── utils/            # 工具函式
    │   ├── logging.py    # 你的 save_chat_log
    │   └── ...
    └── rag/              # 既有的 RAG 邏輯
```


## app啟動方式

```bash
python -m app.main
```

## 重新載入error card方式：

```bash
python -m scripts.rebuild_index
```

### 問題排查
```bash
journalctl -u wuliagent -f
```

### 新增功能

```bash
cd /home/ubuntu/services/wuliagent
git pull  # 或 scp/rsync 更新程式
sudo systemctl restart wuliagent
journalctl -u wuliagent -f
```


### 🛠 如果你有改程式碼，記得 reload systemd（只有修改 service 檔時需要）

如果你只改 Python 程式碼 → 不用 daemon-reload
直接：
```bash
sudo systemctl restart wuliagent
```

如果你有改：
```bash
/etc/systemd/system/wuliagent.service
```
則要：
```bash
sudo systemctl daemon-reload
sudo systemctl restart wuliagent
```


### 🧪 查看是否成功重啟
```bash
sudo systemctl status wuliagent
```



### aws cognito測試題目:

請問在cognito認證的時候遇到 InvalidParameterException / LimitExceededException錯誤要怎麼辦?

可以幫我把這一題新增到知識庫裡面嗎?

### 網頁搜尋範例:

可以幫我用網路搜尋看看litellm ContextWindowExceededError 的錯誤嗎?


### 紀錄維運功能語法:

@wuli加入到維運周報