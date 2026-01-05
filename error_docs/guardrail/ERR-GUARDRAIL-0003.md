---
id: ERR-GUARDRAIL-0003
component: guardrail
category: info
tags: ["content", "rejected"]
patterns:
  - "rejected by content check"
---

# 護欄檢查issue(content)

如果你遇到 Content has been rejected by content check during th input/output process，通常代表：
- 內容觸犯了內容的政策
- 有小概率工程師正在重新部署內容的規則
- 可能是護欄模型不穩定

建議：
1. 可以使用以下工具來測試看看是觸犯了哪一個內容的政策[護欄內容檢查系統](https://35.75.254.74/guardrails)
2. 假設您的AP服務是有使用到rag時請確保把retrieval的資料內容一並帶入檢查，很多時候是檢索資料內容裡面帶有觸犯政策的內容
3. 如檢查後都沒有觸犯任何規則，請等5分鐘後再重新測試一次看看護欄是否還有阻
4. 以上解法排查完後還是無法解決錯誤時請找工程師: **楊修** | **陳志瑋**

給工程師的建議：
1. 可以先去cloudwatch或是litellm上檢查是否真的為被阻擋（請參考wiki）
2. 如並非真正阻擋導致請先確認護欄（pod : content）模型是否正常（去cloudwatch上面檢查是否有error log）
  - 如果content上面有出現這個error: <font color="red">An error occurred (ValidationException) when calling the InvokeModelWithResponseStream operation: Input is too long for requested model."</font>，這代表使用者帶入大量的token導致模型吃不消，要請使用者減少一次帶入的token
3. 出現Content has been rejected by content check during th input/output process並確認真的不是阻擋導致的話請先不要處理，直接轉給開發團隊處理
4. 所有確認方式在GAIA基礎建設平的wiki上都有方法，可以查閱
