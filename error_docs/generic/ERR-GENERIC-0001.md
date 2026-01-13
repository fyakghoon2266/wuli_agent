---
                            id: ERR-GENERIC-0001
                            component: generic
                            category: error
                            tags: ["litellm", "context window", "token limit", "prompt length"]
                            patterns:
                            - "新增 LiteLLM ContextWindowExceededError 錯誤處理指南"
                            ---

                            # LiteLLM ContextWindowExceededError 錯誤處理

如果你遇到 `ContextWindowExceededError`，通常代表：
- Prompt 內容超過了模型的 Context Window 限制
- Token 數量達到或超過模型上限（例如 Claude 3.5 Sonnet 限制 200,000 tokens）
- 在 LiteLLM Proxy 環境中，此錯誤可能被包裝成通用的 `BadRequestError`

建議：
1. **縮短 Prompt 長度**：
   - 移除不必要的內容或重複文字
   - 將長文本分段處理
   - 使用摘要技術壓縮內容

2. **選擇更大 Context Window 的模型**：
   - 考慮切換到 Google Gemini 系列（通常有較大 context window）
   - 查詢目標模型的具體 token 限制

3. **改進錯誤處理邏輯**：
   ```python
   try:
       response = await litellm.acompletion(...)
   except litellm.ContextWindowExceededError as e:
       # 專門處理 context window 錯誤
       print("Context window exceeded, trying with shorter prompt...")
   except litellm.BadRequestError as e:
       # 檢查是否為包裝的 context window 錯誤
       if "ContextWindowExceededError" in str(e):
           print("Wrapped context window error detected")
   ```

4. **預防措施**：
   - 在發送請求前計算 token 數量
   - 設定 Prompt 長度上限檢查
   - 實作自動截斷或分段機制

5. 以上解法排查完後還是無法解決錯誤時請找工程師: **楊修** | **陳志瑋** | **孫郁凱**
                            