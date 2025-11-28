---
id: ERR-GN-0001
component: generic
category: error
tags: ["timeout", "connection", "generic"]
patterns:
  - "timeout"
  - "ConnectionError"
---

# 逾時錯誤

如果你遇到 timeout 或 ConnectionError，通常代表：
- 後端服務暫時無法連線，或
- 網路 / DNS 有問題。

建議：
1. 先用 curl 測試同一個 URL 是否能通。
2. 檢查是否有 proxy / 防火牆設定。
3. 如果是在公司本機來呼叫到基礎建設平台，目前只有開放UT環境可以直通其他環境皆無法
4. 以上解法排查完後還是無法解決錯誤時請找工程師: **孫郁凱** | **楊修** | **陳志瑋**