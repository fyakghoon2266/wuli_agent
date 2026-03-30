---
name: onboard_new_project
description: 新專案接入 GAIA 平台的 onboarding 引導流程
triggers:
  - "新專案"
  - "接入"
  - "onboard"
  - "上線"
  - "怎麼申請"
  - "新 key"
---

# 新專案 Onboarding 引導 SOP

## 觸發情境
使用者詢問如何接入 GAIA 平台、申請新的 API Key、或新專案上線流程。

## 引導步驟

1. **確認需求**：請使用者提供以下資訊：
   - 專案名稱
   - 預計使用的模型 (例如 Claude 3.7 Sonnet, GPT-4o)
   - 預估用量 (每日呼叫次數)
   - 專案負責人與聯絡 Email

2. **查詢架構說明**：使用 `search_error_cards` 搜尋 "架構" 或 "gateway"。
   - 向使用者簡單說明 GAIA 平台的架構：Cognito 認證 → API Gateway → LiteLLM → 模型

3. **檢查模型可用性**：如果使用者指定了模型，使用 `check_model_eol` 確認該模型是否即將下架。
   - 如果模型即將 EOL，建議替代方案

4. **無法直接開通**：Wuli 不能直接開通帳號，請引導使用者：
   - 填寫 GAIA 平台申請表單（請使用者詢問工程師取得表單連結）
   - 或使用 `send_email_to_engineer` 協助轉交需求給工程師

## 回應格式
友善引導式回覆，逐步確認資訊，不要一次丟出所有問題。
