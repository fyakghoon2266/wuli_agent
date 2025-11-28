---
id: ERR-COGNITO-0002
component: infra
category: error
http_status: 401
tags: ["401", "認證錯誤", "NotAuthorizedException Required"]
patterns:
  - "HTTP 401"
  - "NotAuthorizedException"
  - "InvalidToken"
---

# 一般連線錯誤

如果你遇到 HTTP 401或是NotAuthorizedException，通常代表：
- cognito token有錯誤或是cognito發過來的access Token超過有效期限
- prod環境有效期限是60分鐘，UT ＆ UAT是一整天

建議： 
1. 重新呼叫一次cognito來獲取新的access token
2. 查看一下client_id & client_secret
3. 以上解法排查完後還是無法解決錯誤時請找工程師**孫郁凱**
