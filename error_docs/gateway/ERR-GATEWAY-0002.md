--- 
id: ERR-GATEWAY-0002 
component: gateway 
category: error 
tags: ["certificate", "verify failed"] 
patterns: 
    - "certificate verify failed" 
--- 
# 一般連線錯誤（範例卡片） 

如果遇到certificate verify failed，通常代表： 
- 代理或是根憑證未安裝 

建議： 
1. 如果是在開發環境可以先設定ssl verify=False 
2. 安裝公司的ＣＡ（可能要去跟資訊部討論看看） 
3. 以上解法排查完後還是無法解決錯誤時請找工程師: **孫郁凱** | **楊修** | **陳志瑋**