---
id: ERR-GUARDRAIL-0001
component: guardrail
category: info
tags: ["regex", "rejected"]
patterns:
  - "rejected by regex check"
---

# 護欄檢查issue(regex)


如果你遇到 Content has been rejected by regex check during th input/output process，通常代表：
- 內容觸犯了正則表達式的邏輯
- 有小概率工程師正在重新部署正則表達式的規則

建議：
1. 可以使用以下工具來測試看看是觸犯了哪一個正則表達式的政策[護欄內容檢查系統](https://35.78.175.148/guardrails)
2. 假設您的AP服務是有使用到rag時請確保把retrieval的資料內容一並帶入檢查，很多時候是檢索資料內容裡面帶有觸犯政策的內容
3. 如檢查後都沒有觸犯任何規則，請等5分鐘後再重新測試一次看看護欄是否還有阻擋
4. 以上解法排查完後還是無法解決錯誤時請找工程師: **楊修** | **陳志瑋**