# GAIA 護欄系統 (Guardrail System) 架構總覽與資料流

本文件說明 GAIA 護欄系統的微服務架構與請求處理流程。

## 1. 外部網路與身分驗證層 (AWS Infrastructure)
所有來自外部的請求依序經過以下基礎設施：
- **AWS Cognito**：負責發放與管理存取憑證 (Token)。UT/UAT 環境效期為 1 天，PROD 環境效期為 1 小時。
- **AWS API Gateway**：作為外部進入點，驗證使用者的 Cognito Token 是否合法且未過期。驗證失敗直接拒絕存取。
- **網路路由**：驗證通過的流量，依序經過 NLB (Network Load Balancer) 與 ALB (Application Load Balancer)，負載均衡後轉發至內部護欄 Gateway。

## 2. 內部護欄閘道器 (LiteLLM Gateway)
以 LiteLLM 建構，為護欄系統的核心入口。建議客戶端採用 OpenAI 標準格式的 Payload。
處理邏輯依序為：
1. **金鑰驗證**：驗證請求是否攜帶系統核發的 API Key（格式如 `sk-xxxxxxxxxx`）。
2. **流量控制**：檢查該帳號請求頻率是否超過 Rate Limit。若超過則回傳 HTTP 429。
3. **Payload 解析**：解析請求內容。
4. **規則配對 (Policy Lookup)**：至 Redis 查詢該 API Key 對應的防護等級（Level 1、Level 2 或無規則）。
   - **Fail-open 機制**：若 Redis 無法連線，預設以「無規則」放行，避免服務中斷。
   - 若判定為「無規則」，直接略過後續護欄檢查，將請求送往目標 LLM。

## 3. 護欄檢查機制 (gRPC Microservices)
若需要進行防護檢查，Gateway 會透過 gRPC 將 Payload 依序送往以下微服務：
1. **Regex Service (正則表達式服務, Port 8087)**：第一階段防護，透過正則規則比對並阻擋敏感詞或惡意特徵。
2. **Content Service (NeMo Guardrails, Port 8086)**：第二階段防護，進行深層語意分析、對話流控制與企業政策驗證。

## 4. 護欄攔截機制 (Guardrail Rejection)
若護欄節點偵測到違規內容，系統會中斷流程並攔截：
- **狀態碼**：回傳 `HTTP 200 OK`，避免前端應用程式噴錯。
- **攔截訊息**：將 LLM 回答替換為標準化拒絕提示：
  - 輸入端 (Input) 違反 Regex：`Content has been rejected by regex check during the input process`
  - 輸出端 (Output) 違反 Content：`Content has been rejected by content check during the output process`

## 5. 目標 LLM 轉發與回傳 (LLM Pass-through)
1. **轉發請求**：前置檢查 (Input) 通過後，Gateway 將請求轉發給指定的目標雲端模型 (如 AWS/GCP/Azure)。
2. **後置檢查**：收到模型回覆後，再次送往 Regex 與 Content Service 進行輸出端 (Output) 檢查。
3. **錯誤穿透**：若雲端模型發生異常（如 Timeout、502/504），Gateway 不做包裝，直接將原始錯誤訊息回傳給使用者。