---
id: ERR-GN-0004
component: generic
category: info
tags: ["gcp連線", "cloudrun"]
patterns:
  - "clound run 連線至護欄"
  - "google gke連線"
  - "ws_blockoption"
---


# 護欄連線資訊

如果想要從google gke or cloud run連線至護欄，請先確定下列事項：
- 可以先參考護欄在iknow上面的資訊
- 都確認設定完後cloud run需要再麻煩雲架單位幫忙打tag
- 如果沒有打tag會無法順利取得cognito access token
- 會出現一個網頁碼，裡面會帶有"ws_blockoption"的資訊
- 這代表被企業的Forcepoint攔截了，這時候要請雲假幫忙在該ap的cloud run上打上tag
- 如果還有任何問題可以聯絡 **林奕廷**, **孫郁凱**, **陳志瑋**, **楊修**