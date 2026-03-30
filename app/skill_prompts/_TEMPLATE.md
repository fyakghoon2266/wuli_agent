---
name: your_skill_name
description: 一句話描述這個 SOP 的用途（會顯示在 Wuli 的工具目錄中）
triggers:
  - "關鍵字1"
  - "關鍵字2"
  - "keyword3"
---

<!--
  📝 如何撰寫新的 Skill Prompt
  ================================

  1. 複製這個檔案，重新命名為你的 skill 名稱（例如 troubleshoot_504.md）
  2. 填寫上方 YAML frontmatter：
     - name: 英文小寫 + 底線，例如 troubleshoot_504
     - description: 中文一句話描述，Wuli 會看到這段來決定要不要使用
     - triggers: 關鍵字清單，當使用者的問題包含這些字時 Wuli 會優先查閱此 SOP
  3. 在下方撰寫 SOP 內容，可以引用 Wuli 的現有工具名稱

  可引用的工具（寫在步驟裡 Wuli 就會自動使用）：
  - search_error_cards      → 搜尋維運手冊
  - search_litellm_logs     → 查詢 LiteLLM Log
  - verify_prompt_with_guardrails → 護欄合規檢查
  - web_search_technical_solution → 外部網路搜尋
  - send_email_to_engineer  → 寄信給值班工程師
  - check_model_eol         → 查詢模型 EOL
  - system_health_check     → 系統健檢
  - propose_new_error_card  → 新增 Error Card (admin)
  - log_incident_for_weekly_report → 記錄週報 (admin)
  - report_issue_to_jira    → 開 Jira 單 (admin)

  放好檔案後，重啟 Wuli 即可生效，不需要修改任何 Python 程式碼。
-->

# 你的 SOP 標題

## 觸發情境
描述什麼時候要用這個 SOP。

## 排查步驟
1. 第一步：用 `工具名稱` 做什麼
2. 第二步：根據結果判斷...
3. 第三步：如果都找不到，做什麼

## 回應格式
描述 Wuli 應該怎麼回答使用者。
