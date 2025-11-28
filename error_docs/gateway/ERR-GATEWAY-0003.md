--- 
id: ERR-GATEWAY-0003
component: gateway 
category: error 
http_status: 504
tags: ["Gateway Timeout", "504"] 
patterns: 
    - "504 Gateway Timeout" 
--- 
# 逾時錯誤


如果遇到504 Gateway Timeout，通常代表：
- AP端的LLM回應時間太久了，這可能跟每個AP場景有關，有些生成圖片或程式, 網頁的就會特別久 
- 可能有用到think mode，導致思考時間太久
- Gateway端網路不穩（機率滿低的）

建議： 
1. 先檢查AP程式內的邏輯，移除不必要的邏輯，畢竟超過2分鐘的response通常都不是健康的做法
2. 如果是system prompt導致的建議調整寫法
3. 以上解法排查完後還是無法解決錯誤時請找工程師: **楊修** | **陳志瑋**

給工程師的建議：
1. 可以在litellm log觀察，通常request payload會帶有一個think的schema過來，有的話就是ap程式打開思考模式了
2. Gaia基礎建設平台在兩個地方有設計Time out機制，第一個是NLB(這邊是設定2分鐘)，另一個是AI Gateway(就是litellm，這邊是設定5分鐘)，通常使用者的問題如果跑超過2分鐘的就會收到從NLB端口發出來的Gateway Time Out，使用者是可以成功收到這一個error status code(504 gateway time out | 504 bad gateway)