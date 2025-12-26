# ===================== 💎 Gemini 風格 CSS (Button Fix) =====================

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

/* 4. 頭貼設定 */
.avatar-container {
    width: 40px !important;
    height: 40px !important;
    border-radius: 50% !important;
    margin-right: 12px !important;
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

/* 針對所有按鈕做基本設定 */
#chat-input button {
    border: none !important;
    background: transparent !important;
    box-shadow: none !important;
    transition: all 0.2s ease;
}

/* 上傳按鈕 (通常是第一個或有特定 class) */
#chat-input button.upload-button, 
#chat-input button:first-of-type {
    color: #a8c7fa !important;
    padding: 0 10px !important;
}

/* 🔥【修正】送出按鈕 (抓最後一個按鈕) */
#chat-input button:last-of-type {
    color: #a8c7fa !important; /* 亮藍色 */
}

/* 🔥【修正】送出按鈕 (Disabled 鎖定狀態) */
#chat-input button:last-of-type:disabled {
    color: #444746 !important; /* 暗灰色 */
    cursor: not-allowed !important;
    opacity: 0.5 !important;
}

/* 隱藏雜項 */
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
}
</style>
"""

# ===================== 🧠 智慧防呆 JavaScript (修復版) =====================

CHECK_INPUT_JS = """
() => {
    const el = document.getElementById('chat-input');
    if (!el) return;

    const textarea = el.querySelector('textarea');
    // 【修正】不找 id，直接找最後一個按鈕 (那就是送出鍵)
    const buttons = el.querySelectorAll('button');
    const btn = buttons[buttons.length - 1];
    
    if (!textarea || !btn) {
        console.log("Wuli Debug: 找不到輸入框或按鈕");
        return;
    }

    const checkState = () => {
        const text = textarea.value.trim();
        // 檢查是否有圖片 (縮圖 class 通常是 .thumbnail-item 或 img 標籤)
        const hasFile = el.querySelector('img') || el.querySelector('.thumbnail-item') || el.querySelector('.file-preview');

        if (!text && !hasFile) {
            // 沒字且沒圖 -> 鎖定
            btn.disabled = true;
            btn.style.color = "#444746"; 
            btn.style.cursor = "not-allowed";
        } else {
            // 有內容 -> 解鎖
            btn.disabled = false;
            btn.style.color = "#a8c7fa";
            btn.style.cursor = "pointer";
        }
    }

    // 1. 綁定輸入事件
    textarea.addEventListener('input', checkState);

    // 2. 監聽 DOM 變化 (針對圖片上傳)
    const observer = new MutationObserver(checkState);
    observer.observe(el, {subtree: true, childList: true});

    // 3. 自動聚焦
    if (window.wuliFocusTimer) clearInterval(window.wuliFocusTimer);
    window.wuliFocusTimer = setInterval(() => {
        if (!textarea.disabled) {
            textarea.focus();
            clearInterval(window.wuliFocusTimer);
            window.wuliFocusTimer = null;
        }
    }, 100);

    // 4. 初始檢查
    checkState();
}
"""