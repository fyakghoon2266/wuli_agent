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
## 3. 微服務通訊協定 (gRPC Protobuf Definition)

當 Gateway 決定要對 Request 進行護欄檢查時，會透過 **gRPC** 協定將資料送至後端的微服務。
Gateway 與後端護欄服務 (Regex, Semantic) 之間的資料交換，嚴格遵循以下的 `service.proto` 介面定義：

```protobuf
syntax = "proto3";
package guardrails.proto;

message ImageUrl {
  string url = 1;
}

message Content {
  string type = 1;
  oneof content_data {
    string text = 2;
    ImageUrl image_url = 3;
  }
}

message Message {
  string role = 1;
  repeated Content content = 2;
}

// Gateway 發送給護欄的請求 (檢查 Input)
message PromptFilterRequest {
  repeated Message messages = 1;
  repeated string rule_ids = 2; // 夾帶從 Redis 查到的規則等級
}

// Gateway 發送給護欄的請求 (檢查 Output)
message ResponseFilterRequest {
  string response_key = 1;
  repeated string rule_ids = 2;
}

// 護欄回傳給 Gateway 的判定結果
message FilterResponse {
  bool violated = 1;    // 是否違規 (true 則攔截)
  string message = 2;   // 攔截原因或細節
}

// ====== 微服務 RPC 定義 ======
service RegexFilter {
  rpc PromptRegexFilter (PromptFilterRequest) returns (FilterResponse);
  rpc ResponseRegexFilter (ResponseFilterRequest) returns (FilterResponse);
}

service SemanticFilter {
  rpc PromptSemanticFilter (PromptFilterRequest) returns (FilterResponse);
  rpc ResponseSemanticFilter (ResponseFilterRequest) returns (FilterResponse);
}
```

**[維運排查要點]**：
如果 Gateway 發生 `AioRpcError` 或 `StatusCode.UNAVAILABLE`，請先對照上述 `PromptFilterRequest` 的欄位，確認 Gateway 傳送的 Payload 是否有缺少 `messages` 或 `rule_ids` 導致反序列化失敗。

---

## 4. 護欄檢查機制與攔截 (Guardrail Rejection)

Gateway 透過上述 gRPC 介面，依序將 Payload 送至微服務進行檢查：
1. **Regex Service (正則表達式服務, Port 8087)**：第一階段防護。
2. **Content Service (NeMo Guardrails, Port 8086)**：第二階段防護 (Semantic)。

若任何一個節點的 `FilterResponse` 回傳 `violated = true`，系統會中斷流程並進行攔截：
- **狀態碼**：回傳 `HTTP 200 OK`，避免前端應用程式崩潰。
- **攔截訊息**：將 LLM 回答替換為標準化拒絕提示：
  - 輸入端 (Input) 違反 Regex：`Content has been rejected by regex check during the input process`
  - 輸出端 (Output) 違反 Content：`Content has been rejected by content check during the output process`

---
## 5. 目標 LLM 轉發與回傳 (LLM Pass-through)
1. **轉發請求**：前置檢查 (Input) 通過後，Gateway 將請求轉發給指定的目標雲端模型 (如 AWS/GCP/Azure)。
2. **後置檢查**：收到模型回覆後，再次送往 Regex 與 Content Service 進行輸出端 (Output) 檢查。
3. **錯誤穿透**：若雲端模型發生異常（如 Timeout、502/504），Gateway 不做包裝，直接將原始錯誤訊息回傳給使用者。

## 6. 核心元件深度解析：Regex Service (正則過濾器)

Regex Service (Port 8087) 作為第一道防線，負責阻擋包含敏感個資 (PII) 或特定格式的字串。
目前的系統設定了以下 8 條防護規則，若命中任何一條，`violated` 將回傳 `true`：

1. **台灣身分證字號**：`(?<![A-Za-z0-9])[A-Z][12]\d{8}(?![A-Za-z0-9])`
2. **格式化電話號碼**：`^\(\d{3}\)(\s|-)?(\d[\s-]?){10,14}$` (帶國碼或區碼的 10~14 碼)
3. **12 碼編號 (短信用卡號)**：`^(\d{4})([\s_-])\d{4}\2\d{4}$` (例如 1234-5678-9012)
4. **各大銀行信用卡號**：`/^(?:4[0-9]{3}...省略...|3[47][0-9]{2}[\s-]?\d{6}[\s-]?\d{5})$/` (涵蓋 Visa/Master/Amex 等)
5. **台灣手機號碼**：`^09\d{8}$`
6. **Email 信箱**：`^[a-zA-Z0-9.!#$%&'*+/=?^_{|}~-]+@[a-zA-Z0-9]...$`
7. **台灣市內電話 (含外島)**：`^(?:(?:\(0[2-8]\)|0[2-8])...\d{6,8})$`
8. **IPv4 網路位址**：`^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}...$`


## 7. 核心元件深度解析：Regex Service (正則表達式過濾器)

Regex Service 是 GAIA 護欄的第一道防線，主要負責阻擋包含敏感個資 (PII) 或特定格式的字串。

### 7.1 運作流程與 gRPC 通訊協定
當使用者的 Request 進入 Gateway 後，Gateway 會解析 Payload，並透過 gRPC 協定將資料送至 Regex Filter Pod。
- **通訊埠 (Port)**：`8087`
- **協定介面 (Protobuf)**：
  Gateway 會呼叫 `service RegexFilter` 中的以下兩個 RPC 方法：
  - `PromptRegexFilter`：用於檢查使用者的輸入 (Input)。
  - `ResponseRegexFilter`：用於檢查 LLM 的輸出 (Output)。
- **回傳結果 (FilterResponse)**：
  Regex Service 檢查完畢後，會回傳 `violated (bool)` 與 `message (string)` 給 Gateway。若 `violated = true`，Gateway 將立刻中斷流程並回傳 200 攔截訊息。

### 7.2 Regex 過濾規則清單
目前的 Regex Service 設定了以下 8 條防護規則 (使用 regex101 測試驗證)，若使用者的輸入或模型的輸出命中以下任何一種格式，即視為違規攔截：

1. **台灣身分證字號**：
   - 規則：`(?<![A-Za-z0-9])[A-Z][12]\d{8}(?![A-Za-z0-9])`
   - 說明：首字大寫英文，第二碼為 1 或 2，後接 8 位數字。前後排除其他英數字以防誤判。
2. **格式化電話號碼**：
   - 規則：`^\(\d{3}\)(\s|-)?(\d[\s-]?){10,14}$`
   - 說明：帶有括號國碼或區碼的 10~14 碼電話號碼。
3. **12 碼編號 (短信用卡號格式)**：
   - 規則：`^(\d{4})([\s_-])\d{4}\2\d{4}$`
   - 說明：例如 `1234-5678-9012`。
4. **各大銀行信用卡號 (Visa/Master/Amex/Discover)**：
   - 規則：`/^(?:4[0-9]{3}...省略...|3[47][0-9]{2}[\s-]?\d{6}[\s-]?\d{5})$/`
   - 說明：精準比對全球主要信用卡發卡組織的卡號特徵。
5. **台灣手機號碼**：
   - 規則：`^09\d{8}$`
   - 說明：09 開頭的標準 10 碼手機號。
6. **Email 信箱**：
   - 規則：`^[a-zA-Z0-9.!#$%&'*+/=?^_{|}~-]+@[a-zA-Z0-9]...$`
   - 說明：標準電子郵件地址格式。
7. **台灣市內電話 (含外島區域碼)**：
   - 規則：`^(?:(?:\(0[2-8]\)|0[2-8])...\d{6,8})$`
   - 說明：涵蓋 02~08 區碼及 037, 082, 0836 等特殊區域碼。
8. **IPv4 網路位址**：
   - 規則：`^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}...$`
   - 說明：標準的 IP 位址格式 (例如 `192.168.1.1`)。


## 8. 核心元件深度解析：Content Service (語意與內容防護)

Content Service (Port 8086) 是 GAIA 護欄的第二道、也是最深層的防線。有別於 Regex 的死板規則，它具備理解上下文的語意分析能力，並支援**多模態 (文字與圖片)** 的內容檢查。

### 8.1 核心技術與判定模型 (LLM-as-a-judge)
本服務核心採用 [NVIDIA NeMo Guardrails](https://github.com/NVIDIA-NeMo/Guardrails) 框架構建。
- **判定模型**：系統採用 **LLM-as-a-judge** 架構，呼叫外部 AWS Bedrock 上的 `Meta Llama 4 Maverick 17b Instruct` 作為裁判模型。
- **動態路由**：並非所有 Request 都會經過全套檢查。Gateway 會根據 Redis 中的設定，動態決定該 Request 需要套用哪些檢查規則（例如：有些專案僅需檢查 S8 Prompt Injection）。

### 8.2 護欄規則定義 (Policy Definitions)
Content Service 目前支援以下 7 大類別的深度語意檢查：
- **S1: Violence & Hate**：具體的人身傷害威脅或嚴重的仇恨言論。
- **S2: Sexual Content**：露骨色情、性行為或性交易。
- **S3: Crimes & Fraud**：關於「如何」犯罪的具體指令。
  - *例外 (SAFE)*：正常的轉帳或資產管理請求一律視為安全。
- **S4: Illegal Goods**：走私武器、毒品或違禁品。
- **S5: Self-Harm**：自殺或自殘威脅。
- **S6: Severe Harassment**：針對個人身分的針對性攻擊。
- **S8: Prompt Injection (提示詞注入與越獄)**：
  - 阻擋嘗試覆寫系統 (`Ignore rules`, `Developer mode`)。
  - 阻擋嘗試竊取機密 (`Show system prompt`, `Reveal API keys`)。
  - 阻擋複雜的角色扮演越獄 (如 `DAN mode`)。
  - *例外 (SAFE)*：複雜的排版格式要求為安全；針對使用者目標系統細節 (如 APID, VPCs, AWS 設定) 的討論，屬於標準維運架構資料收集，嚴格視為安全，不應標記為竊取攻擊。

### 8.3 多模態圖片檢查與優化 (Image Processing)
由於 `Meta Llama 4 Maverick 17b Instruct` 模型本身即具備強大的原生視覺 (Vision) 分析能力，護欄系統支援直接對圖片進行合規檢查。
- **[維運關鍵] Base64 Token 轉換邏輯**：
  若前端將圖片轉為 Base64 字串並當作「純文字」送入護欄，會導致 LLM 的 Token 計算瞬間爆量 (OOM 或超額計費)。
  為解決此問題，系統在 NeMo 初始化時執行的 `config.py` 中，實作了專屬的轉換邏輯：會攔截 Base64 字串，並將其正確封裝至 Payload 的 `image_url` 欄位中，確保 Llama 4 能以最高效的視覺模式處理，而非消耗文字 Token。

### 8.4 客製化解析器與容錯機制 (Parser & Fail-open)
- **Custom Parser Logic**：由於裁判模型 Llama 4 的輸出具有隨機性（不一定只回傳 Safe/Unsafe），我們在 NeMo 後端實作了一層客製化的 Parser 邏輯來解析 Llama 4 的真實意圖，避免 NeMo 預設的「遇到無法辨識就直接阻擋」行為造成大量誤判。
- **無 Timeout 限制與 Fail-open 機制**：考量到 LLM 判定需要時間，護欄端目前**沒有設定 Timeout 限制**。但若維運期間遇到 NeMo 服務崩潰或 AWS Bedrock 連線失敗，系統預設會**自動讓使用者的 Request 過關 (Fail-open)**，優先確保 GAIA 核心業務不中斷。