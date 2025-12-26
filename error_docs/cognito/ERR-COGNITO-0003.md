---
                            id: ERR-COGNITO-0003
                            component: cognito
                            category: error
                            tags: ["401", "cognito", "key", "expired", "authentication"]
                            patterns:
                            - "HTTP 401 錯誤 - Cognito Key 過期處理"
                            ---

                            # HTTP 401 錯誤 - Cognito Key 過期

如果你遇到 HTTP 401 錯誤，通常代表：
- Cognito 的 Key 已經過期
- 認證憑證失效

建議：
1. 前往 Cognito 控制台檢查 Key 狀態
2. 更新/重新生成新的 Key
3. 確認新 Key 已正確配置到應用程式中
4. 重新測試 API 呼叫
5. 以上解法排查完後還是無法解決錯誤時請找工程師: **楊修** | **陳志瑋** | **孫郁凱**
                            