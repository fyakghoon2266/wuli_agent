# ===================== 💎 Gemini 風格 CSS (大頭像優化版) =====================

GEMINI_STYLE_CSS = """
<style>
/* 1. 全域設定 */
body, .gradio-container {
    background-color: #131314 !important; 
    color: #e3e3e3 !important;
    margin: 0 !important;
    padding: 0 !important;
    height: 100vh !important;
    overflow: hidden !important;
}

footer { display: none !important; }

/* 2. 聊天視窗區域 */
#wuli-chatbot {
    background-color: transparent !important;
    border: none !important;
    box-shadow: none !important;
    height: 100vh !important; 
    overflow-y: auto !important;
    padding-bottom: 130px !important; 
}

/* 3. 對話氣泡 */
.user-message {
    background-color: #2b2d31 !important;
    border-radius: 1.5rem !important;
    border-bottom-right-radius: 0.2rem !important;
    padding: 12px 18px !important;
    width: fit-content !important;
    max-width: 80% !important;
    margin-left: auto !important;
    color: white !important;
}

.bot-message {
    background-color: transparent !important;
    padding: 0px !important;
    width: fit-content !important;
    max-width: 90% !important;
    margin-right: auto !important;
}

/* 4. 頭貼設定 (加大版) */
.avatar-container {
    width: 55px !important;  /* 原本 40px -> 改為 55px */
    height: 55px !important; /* 原本 40px -> 改為 55px */
    border-radius: 50% !important;
    margin-right: 15px !important; /* 間距稍微拉大 */
}
.avatar-container img {
    width: 100% !important;
    height: 100% !important;
    object-fit: cover !important;
}

/* 5. 輸入框區域 (Fixed 置底) */
.input-container {
    position: fixed !important;
    bottom: 25px !important;
    left: 50% !important;
    transform: translateX(-50%) !important;
    width: 90% !important;
    max-width: 850px !important;
    z-index: 9999 !important;
    background: transparent !important;
    padding: 0 !important;
    margin: 0 !important;
}

/* 6. MultimodalTextbox 本體造型 (#chat-input) */
#chat-input {
    background-color: #1e1f20 !important; 
    border: 1px solid #444746 !important;
    border-radius: 32px !important; 
    padding: 6px 12px !important;
    align-items: center !important;
    box-shadow: 0 4px 12px rgba(0,0,0,0.4) !important;
}

#chat-input textarea {
    background-color: transparent !important;
    border: none !important;
    box-shadow: none !important;
    color: white !important;
    font-size: 16px !important;
    padding: 10px !important;
}

/* 按鈕樣式 */
#chat-input button {
    border: none !important;
    background: transparent !important;
    box-shadow: none !important;
    transition: all 0.2s ease;
}

/* 上傳按鈕 */
#chat-input button.upload-button, 
#chat-input button:first-of-type {
    color: #a8c7fa !important;
    padding: 0 10px !important;
}

/* 送出按鈕 (正常) */
#chat-input button:last-of-type {
    color: #a8c7fa !important; 
}

/* 送出按鈕 (Disabled 鎖定) */
#chat-input button:last-of-type:disabled {
    color: #444746 !important; 
    cursor: not-allowed !important;
    opacity: 0.5 !important;
}

.form { background: transparent !important; border: none !important; }
label.svelte-1b6s6s { display: none !important; }
span.svelte-1gfkn6j { display: none !important; }

@media (max-width: 768px) {
    .input-container {
        width: 95% !important;
        bottom: 15px !important;
    }
    #wuli-chatbot {
        padding-bottom: 100px !important;
    }
    /* 手機版可以稍微縮小一點點，避免佔太多空間 */
    .avatar-container {
        width: 45px !important;
        height: 45px !important;
    }
}
</style>
"""

# ===================== 🧠 智慧防呆 JavaScript (保持不變) =====================

CHECK_INPUT_JS = """
() => {
    const el = document.getElementById('chat-input');
    if (!el) return;

    // 定義檢查函式
    const checkState = () => {
        const textarea = el.querySelector('textarea');
        
        // 重新抓取最新的按鈕
        const buttons = el.querySelectorAll('button');
        const btn = buttons[buttons.length - 1]; 

        if (!textarea || !btn) return;

        const text = textarea.value.trim();
        const hasFile = el.querySelector('img') || el.querySelector('.thumbnail-item') || el.querySelector('.file-preview');

        // 判斷邏輯
        if (!text && !hasFile) {
            btn.disabled = true;
            btn.style.color = "#444746"; 
            btn.style.cursor = "not-allowed";
        } else {
            btn.disabled = false;
            btn.style.color = "#a8c7fa";
            btn.style.cursor = "pointer";
        }
    }

    // 1. 綁定輸入事件
    el.addEventListener('input', checkState);

    // 2. 監聽 DOM 變化
    const observer = new MutationObserver((mutations) => {
        checkState();
    });
    observer.observe(el, {subtree: true, childList: true});

    // 3. 自動聚焦
    if (window.wuliFocusTimer) clearInterval(window.wuliFocusTimer);
    window.wuliFocusTimer = setInterval(() => {
        const ta = el.querySelector('textarea');
        if (ta && !ta.disabled) {
            ta.focus();
            clearInterval(window.wuliFocusTimer);
            window.wuliFocusTimer = null;
        }
    }, 100);

    // 4. 初始檢查
    checkState();
}
"""