---
id: ERR-GN-0002
component: generic
category: error
http_status: 500
tags: ["500 Internal Server Error", "key alias", "decode"]
patterns:
  - "Error retrieving rules for key alias"
---


# 認證錯誤

如果遇到500 Internal Server Error Error retrieving rules for key alias，通常代表：
- 護欄發過來的guardrail token(護欄的key)跟規則的名稱不一致

建議：
1. 請維運工程師檢查並重新設定兩者的名稱即可

給工程師的建議：
1. 如果使用者在第一次拿道key發送request後立刻出現這個錯誤的話是因為護欄litellm的key跟cathay_rule_repository裡面設定規則的key兩個名稱對不上或是有其它地方沒有設定好導致的，這時候要回去看一下litellm介面跟tfs cathay_rule_repository repo兩個有沒有設定一至。
