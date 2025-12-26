# app/tools/selfie.py
import os
import random
from langchain.tools import tool

# ==========================================
# 設定區：照片與情境對照表
# ==========================================

# 照片存放目錄
PHOTO_DIR = "app/images/wuli"

# 🔥 照片與情境的對照表 (Key: 檔名, Value: 情境列表)
# 程式會先隨機選一張照片，再從該照片的列表中隨機選一句話。
PHOTO_MOOD_MAP = {
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


# ==========================================
# 工具主程式
# ==========================================

@tool("send_wuli_photo")
def send_wuli_photo(query: str):
    """
    Call this tool when the user explicitly asks for your photo, selfie, or what you look like.
    """
    # 1. 取得目前資料夾內實際存在的檔案
    if not os.path.exists(PHOTO_DIR):
        return "😿 哎呀，我的相簿資料夾好像不見了..."
    
    try:
        existing_files = os.listdir(PHOTO_DIR)
    except Exception as e:
         return f"😿 讀取相簿失敗: {str(e)}"

    # 2. 過濾出「我們有設定情境」且「實際存在於資料夾」的檔案
    # 這一步很重要，避免你程式碼寫了檔名，但忘記把圖檔放進去
    available_photos = [f for f in existing_files if f in PHOTO_MOOD_MAP]

    if not available_photos:
        # 如果對照表的檔案都找不到，就檢查是否有任何圖片
        image_extensions = ('.jpg', '.jpeg', '.png', '.gif')
        any_images = [f for f in existing_files if f.lower().endswith(image_extensions)]
        
        if any_images:
            # 有圖片但沒設定情境，隨機選一張並給通用回答
            selected_filename = random.choice(any_images)
            selected_mood = "這是我隨手拍的一張照片！希望你喜歡！😺"
        else:
            # 真的沒圖了
            return "😿 我的相簿裡目前空空的，沒照片可以給你看..."
    else:
        # 3. 🔥 核心邏輯：隨機選一張有設定過情境的照片
        selected_filename = random.choice(available_photos)
        # 4. 🔥 從該照片的情境列表中，再隨機選一句話
        selected_mood = random.choice(PHOTO_MOOD_MAP[selected_filename])

    # 5. 組合路徑
    relative_path = f"{PHOTO_DIR}/{selected_filename}"
    
    # 組合 Gradio URL (關鍵格式)
    # 格式: /root_path + /gradio_api + /file= + 相對路徑
    image_url = f"/wuliagent/gradio_api/file={relative_path}"

    # 6. 回傳給 LLM 的指令 (In-context Injection)
    return (
        f"SYSTEM_NOTE: I have randomly selected the photo '{selected_filename}'. "
        f"My specific mood/context for this photo is: '{selected_mood}'. "
        "You MUST incorporate this mood description naturally into your reply to make it feel alive. "
        "Finally, you MUST include the following markdown line EXACTLY at the end of your response:\n\n"
        f"![Wuli's Selfie]({image_url})"
    )