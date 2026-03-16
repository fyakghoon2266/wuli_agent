# app/scheduler.py
import datetime
import json
import time
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from langchain_core.messages import HumanMessage

# 引入 LLM Factory 來做摘要/查詢
from app.llm_factory import build_agent_executor
# 引入 log 路徑
from app.tools.incident import LOG_FILE, _save_logs
from app.config import settings

# 設定你的 Email 資訊
SMTP_SERVER = settings.SMTP_SERVER
SMTP_PORT = settings.SMTP_PORT
SMTP_USER = settings.SENDER_EMAIL
SMTP_PASSWORD = settings.SENDER_PASSWORD
GAIA_TEAM_EMAIL = settings.ENGINEER_EMAIL

def send_email_report(subject, body, to_emails=None):
    """
    發送 HTML 信件的共用函式
    Args:
        subject (str): 信件標題
        body (str): 信件內容 (支援 HTML)
        to_emails (list[str] or str, optional): 收件人清單。預設為 GAIA_TEAM_EMAIL。
    """
    if not to_emails:
        to_emails = [GAIA_TEAM_EMAIL]
    
    # 如果傳入的是單一字串，轉成 list
    if isinstance(to_emails, str):
        to_emails = [e.strip() for e in to_emails.split(',')]
    
    # 移除重複並過濾空值
    recipients = list(set([e for e in to_emails if e]))
    
    if not recipients:
        print("❌ 發信失敗: 沒有有效的收件人")
        return False

    msg = MIMEMultipart()
    msg['From'] = SMTP_USER
    msg['To'] = ", ".join(recipients)
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'html'))

    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()
        print(f"📧 信件發送成功！(To: {recipients})")
        return True
    except Exception as e:
        print(f"❌ 發信失敗 (To: {recipients}): {str(e)}")
        return False

def generate_and_send_weekly_report():
    """
    [SRE 週報] 每週五執行
    """
    print("⏰ 排程啟動：正在檢查是否需要發送週報...")
    
    if not os.path.exists(LOG_FILE):
        print("📭 沒有週報檔案，略過。")
        return

    try:
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            logs = json.load(f)
    except:
        logs = []

    if not logs:
        print("📭 本週無事故記錄，略過發信。")
        return

    # --- 整理內容 (HTML) ---
    rows_html = ""
    for log in logs:
        # 簡單判斷顏色
        color = "#d9534f" if "Alert" in log['error'] or "Warning" in log['error'] else "#333"
        
        rows_html += f"""
        <tr style="border-bottom: 1px solid #ddd;">
            <td style="padding: 10px;">{log['timestamp']}</td>
            <td style="padding: 10px;">{log['reporter']}</td>
            <td style="padding: 10px; color: {color};"><b>{log['error']}</b></td>
            <td style="padding: 10px;">{log['solution']}</td>
        </tr>
        """

    email_body = f"""
    <h2>🐱 Wuli 的自動化交接週報</h2>
    <p>各位 Gaia 夥伴辛苦了！這是本週 ({logs[0]['timestamp']} ~ {logs[-1]['timestamp']}) 的維運事故彙整：</p>
    
    <table style="width: 100%; border-collapse: collapse; text-align: left;">
        <thead>
            <tr style="background-color: #f2f2f2;">
                <th style="padding: 10px;">時間</th>
                <th style="padding: 10px;">回報人</th>
                <th style="padding: 10px;">錯誤 / 事件</th>
                <th style="padding: 10px;">詳情 / 解決方案</th>
            </tr>
        </thead>
        <tbody>
            {rows_html}
        </tbody>
    </table>
    
    <p>祝大家週末愉快！ Meow~ 🐾</p>
    <p><i>(此信件由 Wuli Agent 自動生成)</i></p>
    """

    # --- 發送 ---
    if send_email_report(f"[Gaia Ops] Wuli 週報 - {len(logs)} 件紀錄", email_body):
        _save_logs([])
        print("🧹 已清空週報暫存檔，準備迎接下週。")

def run_weekly_eol_scan():
    """
    [每週五綜合巡檢] - EOL 掃描
    """
    print(f"🕵️‍♂️ [週五巡檢] Wuli 開始執行全域模型 EOL 掃描... (Today: {datetime.date.today()})")
    
    unique_models = set()
    
    # 1. 彙整所有要查的模型 (去重)
    for p, m in settings.SRE_MODEL_WATCHLIST:
        unique_models.add((p, m))
    for project in settings.PM_PROJECT_WATCHLIST:
        for p, m in project["models"]:
            unique_models.add((p, m))
            
    if not unique_models:
        print("⚠️ 沒有設定任何模型，結束檢查。")
        return

    eol_cache = {} 
    expiring_models = set()
    
    # 這裡只需要 Admin 權限來執行 Tavily 搜尋，不需要寄信權限 (因為我們改用 Python 寄信了)
    agent = build_agent_executor(is_admin=True) 
    
    print(f"🔍 正在查詢 {len(unique_models)} 個模型的 EOL 資訊...")
    
    # ---------------------------------------------------------
    # 2. 查詢階段 (LLM + Tavily)
    # ---------------------------------------------------------
    for provider, model in unique_models:
        # 🔥 修正點 1: 嚴格限制 LLM 輸出乾淨的 HTML 標籤，禁用 Markdown
        query_prompt = f"""
        請使用 'check_model_eol' 工具讀取 '{provider}' 的官方文件，尋找模型 '{model}' 的 EOL (End of Life) 日期。
        
        【嚴格判斷規則】
        1. **精確名稱比對**：你必須在文件中找到與 '{model}' **完全一致或高度相關** 的型號。
           - 例如：'Claude 3 Sonnet' **不等於** 'Claude 3.5 Sonnet'。
           - 例如：'v1' **不等於** 'v2'。
           - 如果文件只寫了 'Claude 3' 的日期，但我要查的是 'Claude 3.5'，請視為 **找不到資訊**。
        
        2. **日期判斷**：
           - 官方 EOL 日期 (格式 YYYY-MM-DD)。
           - 要注意有些EOL欄位裡面會有一個 No sooner than開頭後面加上日期，那代表說模型不早於這個時個EOL，有No sooner than的欄位請跳過，這個欄位不是一個可以判定的依據
           - 如果找不到該特定版本的日期，請回答 "官方未列出"。
        
        3. **狀態判定**：
           - 只有當 EOL 日期明確存在，且在今天 ({datetime.date.today()}) 的 **未來 3 個月 (90天) 內** 或 **已過期** 時，才回答 "STATUS: EXPIRING"。
           - 如果找不到日期，或日期還很遠(大於90天)，請回答 "STATUS: SAFE"。

        【輸出排版要求 (非常重要)】
        你的回答將會直接嵌入到 Email 中發送給主管，Outlook 無法解析 Markdown，請「絕對不要」使用 Markdown 語法 (例如 **, ##, | 表格, --- 分隔線)。
        請完全使用乾淨的 HTML 標籤 (例如 <b>, <ul>, <li>, <br>) 來進行排版。
        請確保輸出格式類似如下：
        <ul>
            <li><b>官方 EOL 日期：</b>YYYY-MM-DD</li>
            <li><b>狀態判定：</b><span style='color:#d9534f'><b>STATUS: EXPIRING</b></span></li>
            <li><b>詳細資訊：</b>
                請計算 EOL 日期與今天 ({datetime.date.today()}) 的差距。
                - 如果 EOL 日期「晚於」今天，請寫：「距離到期還有 X 天」。
                - 如果 EOL 日期「早於」今天，請寫：「已經過期 X 天」。
                (可視情況補充該模型何時進入 Legacy 階段等資訊)
            </li>
            <li><b>建議：</b>請盡快規劃遷移至...</li>
        </ul>
        請不要加上 ```html 這種程式碼區塊標記，直接輸出純 HTML 文本。
        """
        try:
            result = agent.invoke({
                "input": query_prompt,
                "chat_history": [],
                "user_message": [HumanMessage(content=query_prompt)]
            })
            
            # 處理 LangChain 回傳格式
            raw_output = result.get("output", "")
            output_text = ""
            if isinstance(raw_output, list):
                for block in raw_output:
                    if isinstance(block, dict) and "text" in block:
                        output_text += block["text"]
                    elif isinstance(block, str):
                        output_text += block
            elif isinstance(raw_output, str):
                output_text = raw_output
            else:
                output_text = str(raw_output)

            # 判斷結果
            is_expiring = "STATUS: EXPIRING" in output_text
            eol_cache[(provider, model)] = output_text 
            
            if is_expiring:
                expiring_models.add((provider, model))
                print(f"⚠️  [過期預警] {provider}/{model}")
            else:
                print(f"✅ [安全] {provider}/{model}")
                
            time.sleep(1) # 稍微休息避免 Rate Limit
            
        except Exception as e:
            print(f"❌ 查詢失敗 {provider}/{model}: {e}")

    # Debug: 印出過期清單，確認是否有東西
    print(f"📊 統計：共發現 {len(expiring_models)} 個即將過期的模型: {expiring_models}")

    # ---------------------------------------------------------
    # 3. SRE 通報階段 (寫入週報)
    # ---------------------------------------------------------
    print("📝 正在更新 SRE 維運週報...")
    
    sre_alerts = [
        (p, m) for p, m in expiring_models 
        if (p, m) in settings.SRE_MODEL_WATCHLIST
    ]
    
    if sre_alerts:
        alert_msg = "以下模型即將 EOL (3個月內): " + ", ".join([f"{p}/{m}" for p, m in sre_alerts])
        
        log_prompt = f"""
        請使用 'log_incident_for_weekly_report' 工具記錄一條維運 Warning。
        - error: "Model Lifecycle Alert (EOL)"
        - detail: "{alert_msg}。請參考官方文件並規劃升級。"
        必要參數如下：
        - reporter: "System_Auto_Scanner" (系統自動排程)
        - status: "Pending" (待確認遷移計畫)
        - description: "發現 {len(expiring_models)} 個模型即將在近期 EOL，請 SRE 團隊確認。"
        """
        try:
            agent.invoke({
                "input": log_prompt,
                "chat_history": [],
                "user_message": [HumanMessage(content=log_prompt)]
            })
            print("✅ 已寫入 SRE 週報。")
        except Exception as e:
            print(f"❌ 寫入週報失敗: {e}")
    else:
        print("🎉 SRE 清單中沒有即將過期的模型。")

    # ---------------------------------------------------------
    # 4. 發送總整版通知信 (給指定的主管/負責窗口)
    # ---------------------------------------------------------
    print("📧 正在準備發送總整版 EOL 通知信...")
    
    if not expiring_models:
        print("✅ 沒有任何模型過期，無需寄送通知信。")
        return
        
    # --- 區塊 A：整理全域過期模型的詳細資訊 ---
    global_models_html = ""
    for p, m in expiring_models:
        eol_info = eol_cache.get((p, m), "請自行查詢官方文件")
        
        # 清理 LLM 可能加上去的 markdown 標籤
        eol_info = eol_info.replace("```html", "").replace("```", "").strip()
        
        global_models_html += f"""
        <li style='margin-bottom: 25px; list-style-type: none;'>
            <h4 style='margin: 0 0 10px 0; color: #c92a2a; border-bottom: 1px solid #eee; padding-bottom: 5px; font-family: sans-serif;'>
                🚨 {p} / {m}
            </h4>
            <div style='background-color: #fdf2f2; border-left: 4px solid #c92a2a; padding: 15px; font-size: 14px; line-height: 1.6; font-family: sans-serif;'>
                {eol_info}
            </div>
        </li>
        """

    # --- 區塊 B：整理受影響的專案清單 ---
    impacted_projects_html = ""
    for project in settings.PM_PROJECT_WATCHLIST:
        proj_name = project["project_name"]
        pm_name = project.get("pm_name", "Project Team")
        
        # 找出該專案中，有哪些模型在過期清單裡
        proj_expiring_models = []
        for p, m in project["models"]:
            if (p, m) in expiring_models:
                proj_expiring_models.append(f"{p}/{m}")
        
        # 如果這個專案有中槍，就把他加進名單
        if proj_expiring_models:
            models_str = "、".join(proj_expiring_models)
            impacted_projects_html += f"""
            <li style='margin-bottom: 15px; font-family: sans-serif; font-size: 15px;'>
                <b>【{proj_name}】</b> (專案聯絡人: {pm_name}) <br>
                <span style='color: #c92a2a; font-size: 14px;'>⚠️ 需處理模型：{models_str}</span>
            </li>
            """

    if not impacted_projects_html:
        print("✅ 雖然有模型過期，但追蹤中的專案並未受到影響。")
        return

    # --- 取得要通知的目標信箱清單 ---
    # 從 settings 讀取你剛剛新增的 EOL_NOTIFICATION_LIST
    # 如果找不到，就預設寄給工程師 (SRE) 團隊當作備案
    target_email_list = getattr(settings, "EOL_NOTIFICATION_LIST", [settings.ENGINEER_EMAIL])
    
    email_body = f"""
    <div style="font-family: Arial, sans-serif; color: #333;">
        <h3>各位主管與維運負責人 您好,</h3>
        <p>這是來自 SRE 團隊 <b>Wuli Agent</b> 的自動巡檢通知。</p>
        <p style="color: #c92a2a; font-weight: bold; background-color: #ffe6e6; padding: 10px; border-radius: 5px;">
            🚨 系統偵測到以下模型即將在 3 個月內停止支援 (EOL) 或已過期，請協助通知對應的專案 PM 確認並及早規劃遷移。
        </p>
        
        <h3 style="margin-top: 30px; color: #333; border-bottom: 2px solid #eee; padding-bottom: 5px;">📁 受影響的專案與對應模型</h3>
        <ul style="padding-left: 20px; margin: 0;">
            {impacted_projects_html}
        </ul>

        <h3 style="margin-top: 35px; color: #c92a2a; border-bottom: 2px solid #eee; padding-bottom: 5px;">⚠️ 過期模型詳細官方資訊</h3>
        <ul style="padding: 0; margin: 0;">
            {global_models_html}
        </ul>
        
        <p style="margin-top: 30px;">請各位負責人協助轉達，並請專案團隊與 SRE 團隊討論模型升級或遷移計畫。</p>
        <hr style="border: 0; border-top: 1px solid #eee; margin: 20px 0;">
        <p style="font-size: 12px; color: #777;"><i>Best Regards,<br>Wuli Ops Agent 🤖</i></p>
    </div>
    """
    
    subject = "[Action Required] 🚨 全域模型 EOL 預警與受影響專案通知"
    
    # 呼叫 Python 寄信函式，統一寄給你設定的目標清單
    if send_email_report(subject, email_body, to_emails=target_email_list):
        print(f"✅ 已成功寄出總整版 EOL 通知信！(收件人: {target_email_list})")
    else:
        print(f"❌ 總整版 EOL 通知信寄送失敗。")

# --- 啟動排程器 ---
def start_scheduler():
    scheduler = BackgroundScheduler()
    
    # 1. 每週五 17:00 寄送 SRE 週報
    scheduler.add_job(generate_and_send_weekly_report, CronTrigger(day_of_week='fri', hour=17, minute=0))
    
    # 2. 每週五 10:00 執行 EOL 巡檢
    scheduler.add_job(run_weekly_eol_scan, CronTrigger(day_of_week='fri', hour=10, minute=0))
    
    scheduler.start()
    print("🚀 Wuli 排程器已啟動 (每週五 17:00 寄送週報 / 10:00 EOL 檢查)")

# --- 以下為手動測試區塊 ---
if __name__ == "__main__":
    print("🚀 手動測試模式啟動：開始執行 EOL 掃描...")
    run_weekly_eol_scan()
    print("🏁 測試執行完畢！")