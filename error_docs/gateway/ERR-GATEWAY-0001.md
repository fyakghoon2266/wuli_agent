---
id: ERR-GATEWAY-0001
component: gateway
category: error
http_status: 429
tags: ["Too many request", "RateLimitError"]
patterns:
  - "Too many request"
  - "RateLimitError"
  - "Requests have exceeded the throughput limit on your Provisioned"
---

# 模型端錯誤

如果你遇到 429 Too many request 或 RateLimitError，通常代表：
- 模型端的TPM或是RPM達到該分鐘的上限了
- 過多的請求

建議：
1. 請先稍等1分鐘左右
2. 如果是多人共用同一把護欄token key，請確保其他user沒有高頻率發request
3. 每個模型都有固定的rpm, tpm上限，模型是全行共用的，建議檢查一下專案本身發出來的request一分鐘有幾筆以及每次的token量是多少
4. 以上解法排查完後還是無法解決錯誤時請找工程師: **楊修** | **陳志瑋**