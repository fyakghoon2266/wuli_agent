---
id: ERR-GN-0001
component: generic
category: error
tags: ["timeout", "connection", "generic"]
patterns:
  - "timeout"
  - "ConnectionError"
---

# 一般連線錯誤（範例卡片）

如果你遇到 timeout 或 ConnectionError，通常代表：
- 後端服務暫時無法連線，或
- 網路 / DNS 有問題。

建議：
1. 先用 curl 測試同一個 URL 是否能通。
2. 檢查是否有 proxy / 防火牆設定。
3. 如果多個人同時遇到，請聯絡維運工程師。
