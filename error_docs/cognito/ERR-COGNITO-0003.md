---
                            id: ERR-COGNITO-0003
                            component: cognito
                            category: error
                            tags: ["cognito", "InvalidParameterException", "LimitExceededException", "authentication", "rate-limit"]
                            patterns:
                            - "Cognito InvalidParameterException / LimitExceededException 排查指南"
                            ---

                            # Cognito InvalidParameterException / LimitExceededException 排查指南

如果你遇到 InvalidParameterException 或 LimitExceededException，通常代表：

## InvalidParameterException 可能原因：
- 傳入的參數格式不正確（例如 email 格式、密碼強度不符合規則）
- 必要參數缺失或為空值
- 參數值超出 Cognito 允許的範圍或長度限制
- 使用者屬性設定不符合 User Pool 的配置

## LimitExceededException 可能原因：
- 短時間內嘗試次數過多（例如登入失敗、重設密碼、驗證碼請求）
- 超過 Cognito User Pool 的 API 請求限制
- 達到特定操作的頻率上限（如發送 SMS 驗證碼）
- 同一 IP 或使用者的操作過於頻繁

建議：
1. **檢查參數格式**：確認所有傳入 Cognito 的參數符合格式要求
2. **驗證必要欄位**：確保所有必填參數都有正確提供
3. **等待重試**：如果是 LimitExceededException，等待 5-15 分鐘後再嘗試
4. **檢查 User Pool 設定**：確認密碼政策、屬性要求等配置
5. **實作退避機制**：在應用程式中加入指數退避 (exponential backoff) 重試邏輯
6. 以上解法排查完後還是無法解決錯誤時請找工程師: **楊修** | **陳志瑋** | **孫郁凱**
                            