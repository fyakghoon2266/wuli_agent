---
id: ERR-COGNITO-0001
component: infra
category: error
http_status: 407
tags: ["407", "Proxy", "Authentication Required"]
patterns:
  - "Proxy Authentication Required"
  - "407 Proxy"
---

# 一般連線錯誤（範例卡片）

如果你遇到 407 Proxy Authentication Required，通常代表：
- Proxy主機認證資訊錯誤;或是未設定好

建議： 
1. 於執行環境正確設定代理環境變數或程式級PROXY, ex: **HTTP_PROXY**, **HTTPS_PROXY**
2. 記得申請PROXY白名單
3. 只有在呼叫aws cognito認證時才需要透過proxy，呼叫gaia api gateway不需要
4. 以上解法排查完後還是無法解決錯誤時請找工程師**孫郁凱**