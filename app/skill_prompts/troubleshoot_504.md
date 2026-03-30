---
name: troubleshoot_504
description: 504 Gateway Timeout 逾時問題的標準排查流程
triggers:
  - "504"
  - "timeout"
  - "逾時"
  - "gateway timeout"
  - "連線逾時"
---

# 504 Gateway Timeout 排查 SOP

## 觸發情境
使用者反映收到 504 錯誤、timeout、連線逾時等訊息。

## 排查步驟

1. **確認時間範圍**：請使用者提供發生時間（精確到分鐘），或使用預設最近 30 分鐘。

2. **查詢 Log**：使用 `search_litellm_logs` 查詢：
   - 填入使用者提供的 key_name
   - keyword 設為 "504" 或 "timeout"
   - 觀察 log 中的 response 欄位是否有 error 訊息

3. **比對知識庫**：使用 `search_error_cards` 搜尋 "504" 或 "gateway timeout"。
   - 如果命中 ERR-GATEWAY 系列卡片，照卡片建議回覆。

4. **常見原因檢查清單**：
   - LLM 回應時間過長（模型推論超時）
   - API Gateway 的 timeout 設定太短（預設 30 秒）
   - NLB/ALB 的 idle timeout 設定不匹配
   - 後端 Pod 資源不足或正在 scaling

5. **如果以上都查不到**：使用 `web_search_technical_solution` 搜尋類似問題。

6. **無法解決**：啟動 `send_email_to_engineer` 寄信流程，附上已排查的結果。

## 回應格式
用 Markdown 列表整理排查結果，包含：時間、影響範圍、可能原因、建議下一步。
