import os
import json
import time
import glob

# --- 設定區 ---
LOG_DIR = "log"  # 資料夾名稱
LOG_FILENAME = "chat_history.jsonl" # 目前正在寫入的檔案
LOG_PATH = os.path.join(LOG_DIR, LOG_FILENAME)

MAX_FILE_SIZE = 5 * 1024 * 1024  # 限制單一檔案最大 5MB
BACKUP_COUNT = 10                # 最多保留 10 份舊檔案 (超過就刪除最舊的)

def save_chat_log(user_msg, bot_msg):
    """
    將對話紀錄寫入 Log，並自動執行 House Keeping。
    """
    # 1. 確保 log 資料夾存在
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR)

    # 2. House Keeping (檔案輪替)
    # 檢查檔案是否存在且超過大小限制
    if os.path.exists(LOG_PATH) and os.path.getsize(LOG_PATH) > MAX_FILE_SIZE:
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        # 將舊檔案改名，例如: chat_history_20251217_172000.jsonl
        backup_name = os.path.join(LOG_DIR, f"chat_history_{timestamp}.jsonl")
        
        try:
            os.rename(LOG_PATH, backup_name)
            print(f"[Log] 檔案過大，已封存為: {backup_name}")
        except Exception as e:
            print(f"[Log] 檔案輪替失敗: {e}")

        # 3. 清理過舊的檔案 (只保留最新的 BACKUP_COUNT 份)
        # 找出所有備份檔 (chat_history_*.jsonl)
        backup_files = sorted(glob.glob(os.path.join(LOG_DIR, "chat_history_*.jsonl")))
        
        while len(backup_files) > BACKUP_COUNT:
            oldest_file = backup_files.pop(0) # 取得最舊的一個
            try:
                os.remove(oldest_file)
                print(f"[Log] 刪除過期 Log: {oldest_file}")
            except Exception as e:
                print(f"[Log] 刪除失敗: {e}")

    # 4. 準備寫入資料
    log_entry = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "user_query": str(user_msg), # 確保轉成字串防呆
        "bot_response": str(bot_msg)
    }

    # 5. Append 模式寫入 (JSONL 格式)
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
    except Exception as e:
        print(f"[Log] 寫入失敗: {e}")