---
                            id: ERR-GENERIC-0001
                            component: generic
                            category: error
                            tags: ["ContextWindowExceededError", "token limit", "context window", "litellm"]
                            patterns:
                            - "新增 LiteLLM ContextWindowExceededError 錯誤處理指南"
                            ---

                            # LiteLLM ContextWindowExceededError 錯誤處理

如果你遇到 `ContextWindowExceededError`，通常代表：
- 請求的 Token 數量超過了模型的最大 context length 限制
- 輸入內容（messages）+ 預期輸出（max_tokens）超過模型支援範圍
- 常見於 GPT-4o (128,000 tokens)、GPT-3.5-turbo (4,096 tokens) 等模型

建議：
1. **縮短輸入內容**：
   - 減少 messages 中的文字長度
   - 移除不必要的歷史對話記錄
   - 分割長文本為多個較短的請求

2. **調整 completion 參數**：
   - 降低 `max_tokens` 參數值
   - 確保 input tokens + max_tokens < model's context limit
   - 檢查錯誤訊息中的具體 token 數量

3. **程式碼處理範例**：
   ```python
   from litellm.exceptions import ContextWindowExceededError
   
   try:
       response = await acompletion(...)
   except ContextWindowExceededError as e:
       print(f"Context window exceeded: {e}")
       # 處理邏輯：縮短輸入或分割請求
   ```

4. **考慮切換模型**：
   - 使用支援更大 context window 的模型
   - 或將任務分解為多個小請求

5. 以上解法排查完後還是無法解決錯誤時請找工程師: **楊修** | **陳志瑋** | **孫郁凱**
                            