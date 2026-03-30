---
name: troubleshoot_blocked
description: 使用者的 Prompt 被護欄阻擋時的排查與解釋流程
triggers:
  - "被擋"
  - "被阻擋"
  - "blocked"
  - "為什麼不行"
  - "違規"
  - "護欄擋"
  - "guardrail"
---

# Prompt 被護欄阻擋排查 SOP

## 觸發情境
使用者反映「為什麼被擋」、「這句話為什麼不行」、「剛剛送出去被 block 了」等。

## 排查步驟

1. **判斷使用者是否已提供被擋的 Prompt 內容**：
   - **有提供**：直接跳到步驟 3。
   - **沒提供**：進入步驟 2。

2. **撈取原始 Payload**：使用 `search_litellm_logs` 查詢最近的 log。
   - 找到被擋的那筆紀錄
   - 從 log 中提取原始 Prompt 內容

3. **送進護欄檢測**：使用 `verify_prompt_with_guardrails` 檢查該 Prompt。
   - 工具會回傳三項結果：LLM 檢查、關鍵字檢查、正則檢查
   - 確認是哪一個機制觸發了阻擋

4. **比對知識庫**：使用 `search_error_cards` 搜尋護欄相關的 Error Card。
   - 查看是否有已知的 pattern 可以解釋

5. **向使用者解釋**：
   - 說明具體是「關鍵字」、「正則」還是「LLM 審查」觸發的
   - 如果是關鍵字或正則，告知具體觸發的詞彙/pattern
   - 如果是 LLM 審查，解釋審查邏輯

6. **提供修改建議**：
   - 建議使用者如何修改 Prompt 以避開護欄
   - 如果使用者認為是誤擋，引導至寄信流程請工程師調整規則

## 回應格式
結構化回覆：被擋原因 → 觸發的具體機制 → 修改建議。
