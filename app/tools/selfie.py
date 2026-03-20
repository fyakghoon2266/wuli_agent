# app/tools/selfie.py
import os
import random
from langchain.tools import tool

from app.utils.logging import get_logger

logger = get_logger(__name__)

# ==========================================
# 設定區：照片與情境對照表
# ==========================================

# 照片存放目錄
WULI_PHOTO_DIR = "app/images/wuli"
MILU_PHOTO_DIR = "app/images/milu"

# 🔥 照片與情境的對照表 (Key: 檔名, Value: 情境列表)
# 程式會先隨機選一張照片，再從該照片的列表中隨機選一句話。
WULI_MOOD_MAP = {
    # --- 第一批 (7張) ---

    # 1. 縮成一團睡覺 (米色背景)
    "IMG_1234.jpg": [
        "Power Saving Mode: ON. 目前已進入深度休眠模式 🟢",
        "正在夢境中跑 Regression Test，請勿打擾...",
        "別看我睡著了，我的耳朵還在聽 Alert 的聲音呢。",
        "Shhh... 我正在進行大腦磁碟重組 (Defragmentation)。"
    ],

    # 2. 仰躺翻肚大睡 (床上)
    "IMG_0027.JPG": [
        "⚠️ 警告：系統核心溫度過高，已啟動緊急散熱協定 (翻肚)！",
        "這姿勢能最大化我的 Wi-Fi 接收訊號，以便監控雲端服務 📡",
        "這就是經歷了一整週 Deployment 之後的我在週末的樣子...",
        "我已躺平，這週剩下的 Bug 就交給你了 (揮手)。"
    ],

    # 3. 趴在木地板上監控 (母雞蹲)
    "IMG_6922.JPG": [
        "我在檢查機房地板層的基礎設施是否穩固。(其實是地板比較涼快)",
        "正在進行底層網路封包監聽... 目前一切正常。",
        "隨時準備好起跑去修復 Bug！(目前蓄力進度 85%)",
        "今天的值班工程師是我，有什麼問題請趴下來跟我說。"
    ],

    # 4. 縮成一團睡覺 (米色背景，角度不同)
    "IMG_7347.JPG": [
        "已進入待機模式 (Standby)，有 P0 級事故再叫醒我...",
        "充電中... 目前電量 45% 🔋，預計還需要 3 個罐罐的時間充滿。",
        "夢到全世界的伺服器都達到 100% Uptime... 真香...",
        "Zzz... SELECT * FROM dreams WHERE type = 'tuna'..."
    ],

    # 5. 大頭自拍 (看鏡頭)
    "IMG_7436.JPG": [
        "等等，讓我近距離檢查一下你的螢幕... 你的 Code 縮排好像怪怪的？🧐",
        "這是我做 Code Review 時的嚴肅表情。(盯——)",
        "早安... 或是晚安？維運貓貓是沒有時差的。",
        "怎麼樣？這麼近看我，是不是被我的帥氣震懾到了？✨"
    ],

    # 6. 驚恐/大眼側看 (躺著)
    "IMG_7776.JPG": [
        "什麼！？你說你把 Root Key 放在公開 Repo 裡！？🙀",
        "我聽到了... 那個是 PagerDuty 通知的聲音嗎？(驚)",
        "別動！我偵測到異常流量！(其實只是逗貓棒動了一下)",
        "這眼神代表我對你剛剛 Merge 的那段程式碼感到... 非常震驚。"
    ],

    # 7. 側躺沙發回眸 (棕色椅子)
    "IMG_8211.JPG": [
        "我就這樣靜靜地看著你 Deploy 到 Production... 😏",
        "這就是所謂的『NOC (Network Operations Couch)』沙發監控中心。",
        "你剛剛是不是又動了 DB？我看著你喔... 👀",
        "Draw me like one of your French DevOps engineers. (誤)"
    ],
    
   "IMG_7404.JPG": [
        "嗯？我好像聽到有人說『我只是稍微改了一下 Production 的設定』...？",
        "被你發現我躲在這裡偷懶了！(趕快假裝在看 Log)",
        "這眼神是在確認：你剛剛提交的那行程式碼真的有測過嗎？",
        "誰？誰在那邊？喔... 是你啊，嚇我一跳，我以為是 PM 來看進度了。"
    ],

    "IMG_8192.JPG": [
        "這不是在玩，我是在對這個頑強的 Bug 進行物理攻擊！(咬)",
        "專注... 專注... 解決問題就像啃這根木頭一樣，要充滿毅力！😤",
        "我在測試這個新硬體設備的耐咬度... 目前測試結果：還算堅固。",
        "Debug 到壓力太大時的標準舒壓方式。"
    ],

    "IMG_0045.JPG": [
        "這就是經歷了一整晚 P1 事故後的我... 請勿打擾。",
        "已進入飛航模式 ✈️，拒絕接收任何 Alert 通知。",
        "夢裡什麼都有... 夢裡的 API Response Time 都是 10ms 以下...",
        "正在把記憶體裡的暫存資料寫入長期睡眠硬碟中..."
    ],

    "wuli_send.jpge": [
        "這包是我最愛的皇家飼料",
        "如果你滿意我的服務可以寄這包飼料給我唷",
        "我很樂意幫大家消滅這個熱量大魔王"
    ],

    "IMG_9398.JPG": [
        "已進入待機模式 (Standby)，有 P0 級事故再叫醒我...",
        "充電中... 目前電量 45% 🔋，預計還需要 3 個罐罐的時間充滿。",
        "夢到全世界的伺服器都達到 100% Uptime... 真香...",
        "Zzz... SELECT * FROM dreams WHERE type = 'tuna'..."
    ],


}

MILU_MOOD_MAP = {
    "IMG_9995.jpg": ["這是 Milu 睡著的樣子，簡直像天使一樣..."],
    "IMG_0770.jpeg": ["這是 Milu 跟我一起幫爸爸修電腦的樣子，爸爸沒有我們真的不行"],
    "IMG_8287.jpg": ["喵~ 既然你問了，就讓你看看我最親愛的妹妹 Milu 吧！是不是很可愛？(ฅ'ω'ฅ)"],
    "IMG_7879.jpg": ["這是我家的小公主 Milu！她平時可不負責看 Log，只負責鬼靈精怪！✨"],

}

MILU_DEFAULT_MOODS = [
    "喵~ 既然你問了，就讓你看看我最親愛的妹妹 Milu 吧！是不是很可愛？(ฅ'ω'ฅ)",
    "這是我家的小公主 Milu！她平時可不負責看 Log，只負責賣萌喔！✨",
    "登登！這是 Milu 妹妹的照片！看到她，今天 debug 的壓力是不是都消失了呢？",
    "哼哼，雖然我是專業的 SRE 助理，但在可愛這方面，我可能要讓她三分了。"
]


# ==========================================
# 工具主程式
# ==========================================

def get_random_photo_and_mood(photo_dir: str, mood_map: dict, default_moods: list = None):
    """
    通用函式：從指定目錄隨機挑選照片與情境。
    """
    if not os.path.exists(photo_dir):
        logger.error(f"❌ 找不到相簿資料夾: {photo_dir}")
        return None, None
        
    try:
        existing_files = [f for f in os.listdir(photo_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png', '.gif'))]
    except Exception as e:
        logger.error(f"❌ 讀取相簿失敗: {str(e)}")
        return None, None
        
    if not existing_files:
        return None, None

    # 隨機選一張照片
    selected_filename = random.choice(existing_files)
    
    # 決定台詞：如果有專屬對白就用，沒有就用預設對白，再沒有就給通用的一句話
    if selected_filename in mood_map:
        selected_mood = random.choice(mood_map[selected_filename])
    elif default_moods:
        selected_mood = random.choice(default_moods)
    else:
        selected_mood = "這是我隨手拍的一張照片！希望你喜歡！😺"
        
    return selected_filename, selected_mood


@tool("send_photo_album")
def send_photo_album(query: str):
    """
    Call this tool when the user explicitly asks for a photo, selfie, or what you (Wuli) or your sister (Milu) look like.
    Use the 'query' argument to determine if they are asking for Wuli or Milu.
    """
    query_lower = query.lower()
    
    # 判斷使用者是要看誰的照片 (預設是 Wuli)
    is_asking_for_milu = any(keyword in query_lower for keyword in ["milu", "妹妹", "妹"])
    
    if is_asking_for_milu:
        logger.info("🎉 觸發 Milu 彩蛋！準備發送妹妹的照片。")
        target_dir = MILU_PHOTO_DIR
        target_map = MILU_MOOD_MAP
        default_moods = MILU_DEFAULT_MOODS
        alt_text = "Milu's Photo"
    else:
        logger.info("📸 準備發送 Wuli 的自拍照。")
        target_dir = WULI_PHOTO_DIR
        target_map = WULI_MOOD_MAP
        default_moods = None # Wuli 目前都是強關聯，找不到就給預設一句話
        alt_text = "Wuli's Selfie"

    # 取得照片與對白
    selected_filename, selected_mood = get_random_photo_and_mood(target_dir, target_map, default_moods)

    if not selected_filename:
         return "😿 哎呀，我的相簿好像有點問題，找不到照片..."

    # 組合相對路徑
    relative_path = f"{target_dir}/{selected_filename}"
    
    # 組合 Gradio URL (關鍵格式)
    image_url = f"/wuliagent/gradio_api/file={relative_path}"

    # 回傳給 LLM 的指令 (In-context Injection)
    return (
        f"SYSTEM_NOTE: I have randomly selected the photo '{selected_filename}' from the album. "
        f"My specific mood/context for this photo is: '{selected_mood}'. "
        "You MUST incorporate this mood description naturally into your reply to make it feel alive. "
        "Finally, you MUST include the following markdown line EXACTLY at the end of your response:\n\n"
        f"![{alt_text}]({image_url})"
    )