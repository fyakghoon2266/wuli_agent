---
id: ERR-GUARDRAIL-0002
component: guardrail
category: info
tags: ["keyword", "rejected"]
patterns:
  - "rejected by keyword check"
---

# 護欄檢查issue(keyword)

如果你遇到 Content has been rejected by keyword check during th input/output process，通常代表：
- 內容觸犯了關鍵字的政策
- 有小概率工程師正在重新部署關鍵字的規則

建議：
1. 可以使用以下工具來測試看看是觸犯了哪一個關鍵字的政策[護欄內容檢查系統](https://35.75.254.74/guardrails)
2. 假設您的AP服務是有使用到rag時請確保把retrieval的資料內容一並帶入檢查，很多時候是檢索資料內容裡面帶有觸犯政策的內容
3. 如檢查後都沒有觸犯任何規則，請等5分鐘後再重新測試一次看看護欄是否還有阻擋
4. 以上解法排查完後還是無法解決錯誤時請找工程師: **楊修** | **陳志瑋**