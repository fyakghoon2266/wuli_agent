# ===================== 🌗 Gemini 雙模態適應 CSS =====================

GEMINI_STYLE_CSS = """
<style>
/* 1. 隱藏 Footer */
footer { display: none !important; }

/* 2. 聊天視窗區域 (佈局設定) */
.gradio-container {
    padding: 0 !important;
    max-width: 100% !important;
    height: 100vh !important;
    overflow: hidden !important;
}

#wuli-chatbot {
    background-color: transparent !important;
    border: none !important;
    box-shadow: none !important;
    height: 100vh !important; 
    overflow-y: auto !important;
    /* 底部預留空間給輸入框 */
    padding-bottom: 130px !important; 
}

/* 3. 對話氣泡 (外型圓潤，顏色跟隨主題) */
.user-message {
    /* 使用 Gradio 的強調色變數 (通常是淺色模式=橘/藍, 深色=深橘/深藍) */
    background-color: var(--color-accent-soft) !important;
    border: 1px solid var(--border-color-primary) !important;
    border-radius: 1.5rem !important;
    border-bottom-right-radius: 0.2rem !important;
    padding: 12px 18px !important;
    width: fit-content !important;
    max-width: 80% !important;
    margin-left: auto !important;
    /* 文字顏色自動適應 */
    color: var(--body-text-color) !important;
}

.bot-message {
    background-color: transparent !important;
    padding: 0px !important;
    width: fit-content !important;
    max-width: 90% !important;
    margin-right: auto !important;
    color: var(--body-text-color) !important;
}

/* 4. 頭貼設定 */
.avatar-container {
    width: 55px !important;
    height: 55px !important;
    border-radius: 50% !important;
    margin-right: 15px !important;
    border: 1px solid var(--border-color-primary) !important;
}
.avatar-container img {
    width: 100% !important;
    height: 100% !important;
    object-fit: cover !important;
}

/* 5. 輸入框區域 (Fixed 置底佈局 - 這是 Gemini 的靈魂) */
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

/* 6. 輸入框本體造型 (#chat-input) */
#chat-input {
    /* 【關鍵】背景色使用變數，讓它在淺色模式變白/灰，深色模式變黑/灰 */
    background-color: var(--input-background-fill) !important;
    border: 1px solid var(--border-color-primary) !important;
    border-radius: 32px !important; 
    padding: 6px 12px !important;
    align-items: center !important;
    /* 加上陰影讓它浮起來，淺色深色都適用 */
    box-shadow: 0 4px 12px rgba(0,0,0,0.15) !important;
}

/* 內部 Textarea */
#chat-input textarea {
    background-color: transparent !important;
    border: none !important;
    box-shadow: none !important;
    /* 文字顏色跟隨系統 */
    color: var(--body-text-color) !important;
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

/* 上傳與送出按鈕 (使用 Primary Color) */
#chat-input button.upload-button, 
#chat-input button:first-of-type,
#chat-input button:last-of-type {
    color: var(--color-accent) !important; /* 使用主題強調色 */
    padding: 0 10px !important;
}

/* Disabled 狀態 */
#chat-input button:last-of-type:disabled {
    color: var(--body-text-color-subdued) !important; /* 使用系統定義的「無效文字色」 */
    cursor: not-allowed !important;
    opacity: 0.5 !important;
}

/* 隱藏雜項 */
.form { background: transparent !important; border: none !important; }
label.svelte-1b6s6s { display: none !important; }
span.svelte-1gfkn6j { display: none !important; }

/* 針對深色模式微調陰影，讓它更明顯 */
.dark #chat-input {
    box-shadow: 0 4px 12px rgba(0,0,0,0.4) !important;
}

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

# ===================== 🧠 智慧防呆 JavaScript (不變) =====================

CHECK_INPUT_JS = """
() => {
    const el = document.getElementById('chat-input');
    if (!el) return;

    const checkState = () => {
        const textarea = el.querySelector('textarea');
        const buttons = el.querySelectorAll('button');
        const btn = buttons[buttons.length - 1]; 

        if (!textarea || !btn) return;

        const text = textarea.value.trim();
        const hasFile = el.querySelector('img') || el.querySelector('.thumbnail-item') || el.querySelector('.file-preview');

        if (!text && !hasFile) {
            btn.disabled = true;
            // 這裡不手動改 color，交給 CSS 的 :disabled 選擇器去控制
            btn.style.cursor = "not-allowed";
        } else {
            btn.disabled = false;
            btn.style.cursor = "pointer";
        }
    }

    el.addEventListener('input', checkState);
    const observer = new MutationObserver((mutations) => {
        checkState();
    });
    observer.observe(el, {subtree: true, childList: true});

    if (window.wuliFocusTimer) clearInterval(window.wuliFocusTimer);
    window.wuliFocusTimer = setInterval(() => {
        const ta = el.querySelector('textarea');
        if (ta && !ta.disabled) {
            ta.focus();
            clearInterval(window.wuliFocusTimer);
            window.wuliFocusTimer = null;
        }
    }, 100);

    checkState();
}
"""