---
id: ERR-GN-0003
component: generic
category: info
tags: ["本機", "桌機到UT環境"]
patterns:
  - "怎麼從桌機或是本機連線到護欄UT環境"
---


# 護欄連線資訊

如果想要從本機端連線至護欄的UT環境要先確保下面幾件事情都完成了：
- 申請到cognito相關資訊＆有拿到護欄的token | key
- 申請本機端到護欄ＵＴ防火牆連線
- 呼叫cognito要透過proxy，取得access token後連線至api gateway則不需要透過proxy
- 提權修改etc/host （這一段不確定是否需要，會因為DNS跟雲架政策而決定）
- 如果還有任何問題可以聯絡 **林奕廷**, **孫郁凱**, **楊修**