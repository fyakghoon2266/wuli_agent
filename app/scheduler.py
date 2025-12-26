import json
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

# 引入 LLM Factory 來做摘要 (如果你有的話，沒有的話可以直接用字串拼接)
from app.llm_factory import AgentSingleton
# 引入剛剛的 log 路徑
from app.tools.incident import LOG_FILE, _save_logs
from app.config import settings

# 設定你的 Email 資訊 (建議移到 .env)
SMTP_SERVER = settings.SMTP_SERVER
SMTP_PORT = settings.SMTP_PORT
SMTP_USER = settings.SENDER_EMAIL
SMTP_PASSWORD = settings.SENDER_PASSWORD
GAIA_TEAM_EMAIL = settings.ENGINEER_EMAIL

def send_email_report(subject, body):
    """發送 HTML 信件的底層函式"""
    msg = MIMEMultipart()
    msg['From'] = SMTP_USER
    msg['To'] = GAIA_TEAM_EMAIL
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'html')) # 支援 HTML 格式

    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()
        print("📧 週報發送成功！")
        return True
    except Exception as e:
        print(f"❌ 發信失敗: {str(e)}")
        return False

def generate_and_send_weekly_report():
    """
    每週五執行的主邏輯：
    1. 讀取 JSON
    2. 如果有資料 -> 整理 -> 發信 -> 清空 JSON
    3. 如果沒資料 -> 略過
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

    # --- 整理內容 ---
    # 這裡可以直接用 Python 字串拼接，也可以呼叫 LLM 美化
    # 為了穩定，我們先用 HTML 模板拼接
    
    rows_html = ""
    for log in logs:
        rows_html += f"""
        <tr style="border-bottom: 1px solid #ddd;">
            <td style="padding: 10px;">{log['timestamp']}</td>
            <td style="padding: 10px;">{log['reporter']}</td>
            <td style="padding: 10px; color: #d9534f;">{log['error']}</td>
            <td style="padding: 10px; color: #5cb85c;">{log['solution']}</td>
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
                <th style="padding: 10px;">錯誤現象</th>
                <th style="padding: 10px;">解決方案</th>
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
    if send_email_report(f"[Gaia Ops] Wuli 週報 - {len(logs)} 件事故彙整", email_body):
        # 發送成功後，備份並清空原始檔案，讓下週重新開始
        # 實務上建議改名備份 (例如 weekly_incidents_20251226.json)
        # 這裡簡單做：直接清空
        _save_logs([])
        print("🧹 已清空週報暫存檔，準備迎接下週。")

# --- 啟動排程器 ---
def start_scheduler():
    scheduler = BackgroundScheduler()
    # 設定每週五 17:00 執行 (day_of_week='fri', hour=17, minute=0)
    
    scheduler.add_job(generate_and_send_weekly_report, CronTrigger(day_of_week='fri', hour=17, minute=0))
    
    # 測試用：每 1 分鐘執行一次 (開發時可以把下面這行打開測試)
    # scheduler.add_job(generate_and_send_weekly_report, 'interval', minutes=1)
    
    scheduler.start()
    print("🚀 Wuli 排程器已啟動 (每週五 17:00 寄送週報)")