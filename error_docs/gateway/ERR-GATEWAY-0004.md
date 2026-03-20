--- 
id: ERR-GATEWAY-0004
component: gateway 
category: error 
http_status: 500
tags: ["gRPC", "Connection refused", "Payload Schema", "500", "NeMo Guardrails", "Regex"] 
patterns: 
    - "AioRpcError" 
    - "StatusCode.UNAVAILABLE"
    - "Failed to connect to remote host"
--- 
# gRPC 連線失敗或 Payload 解析錯誤

如果遇到這個錯誤，通常代表：
- **使用者端**：傳送過來的 LLM Request Payload 中出現了新的或未定義的 Key，導致 Gateway 解析時與我們定義的 gRPC schema 不同而發生錯誤。
- **護欄端 (Guardrail)**：內部的 gRPC 微服務異常或是連線被拒絕（例如 `Connection refused (111)`）。

建議： 
1. 先請使用者提供剛剛送出的完整 Request Payload（包含所有的參數與 Key），以便後續排查。
2. 這個錯誤通常牽涉到系統底層連線或 Schema 定義，使用者無法自行排除，請收集好 Payload 後直接尋求工程師協助。

給工程師的建議：
1. 先檢查使用者提供的 Payload，比對目前的 gRPC protobuf schema，確認是否因為使用了 LLM 新推出的參數或自訂 Key 導致解析失敗。
2. 如果 Payload 正常，請檢查目標 IP 上的護欄微服務是否正常運作。GAIA 護欄是由微服務組成的，請根據 Error Log 中的 Port 號來判斷是哪一個節點掛掉：
   - **Port 8086**：代表 **NeMo Guardrails** 服務異常或連線被拒。
   - **Port 8087**：代表 **正則表達式 (Regex) 過濾服務** 異常或連線被拒。
3. 觀察對應的微服務是否發生 Crash，或是內部的網段/防火牆規則是否有異動導致連線被阻擋。