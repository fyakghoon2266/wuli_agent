CUSTOM_CSS = """
/* 覆寫 gradio 頭貼 container 大小 */
.avatar-container.svelte-1nr59td {
    width: 50px !important;
    height: 50px !important;
    border-radius: 50% !important;
    flex-shrink: 0 !important;
}

/* 再把圖本身放大，填滿 container */
.avatar-container.svelte-1nr59td img {
    width: 100% !important;
    height: 100% !important;
    border-radius: 50% !important;
    object-fit: cover !important;
}

.message-row img {
    margin: 0px !important;
    }

.avatar-container img {
    padding: 0px !important;
    }

/* 訊息本體稍微留一點空間 */
#wuli-chatbot .message {
    padding-top: 6px !important;
    padding-bottom: 6px !important;
}

/* ==== RWD: 平板 / 手機共用調整 (寬度 <= 768px) ==== */
@media (max-width: 768px) {
    /* 整個 gradio 外框稍微縮一點邊距 */
    .gradio-container {
        padding: 8px !important;
    }

/* Chatbot 高度縮短，不要佔滿整個畫面 */
#wuli-chatbot {
    height: 320px !important;
}

/* 標題文字縮小 */
.gradio-container h1, 
.gradio-container h2 {
    font-size: 1.1rem !important;
}

    /* 頭貼適度縮小一點 */
.avatar-container.svelte-1nr59td {
        width: 56px !important;
        height: 56px !important;
    }
}

/* ==== RWD: 手機窄版 (寬度 <= 480px) ==== */
@media (max-width: 480px) {
    /* 根容器幾乎貼邊，符合手機感 */
    .gradio-container {
        padding: 4px !important;
    }

    /* Chatbot 高度再縮，避免輸入框被擠出畫面 */
    #wuli-chatbot {
        height: 260px !important;
    }

    /* 泡泡字體再小一點 */
    #wuli-chatbot .message {
        font-size: 0.9rem !important;
    }

    /* 頭貼再縮小 */
    #wuli-chatbot .avatar-container.svelte-1nr59td {
        width: 48px !important;
        height: 48px !important;
    }

    /* 輸入框的 label 可以隱藏，只保留框本身，省空間 */
    label[for*="textbox"] {
        display: none !important;
    }

    /* Textbox padding 小一點，讓畫面更緊湊 */
    textarea {
        font-size: 0.9rem !important;
        padding: 6px 8px !important;
    }
}

"""

AUTO_FOCUS_JS = """
() => {
    const el = document.getElementById('chat-input');
    const textarea = el?.querySelector('textarea');
    if (!textarea) return;

    if (window.wuliFocusTimer) clearInterval(window.wuliFocusTimer);

    window.wuliFocusTimer = setInterval(() => {
        if (!textarea.disabled) {
            textarea.focus();
            clearInterval(window.wuliFocusTimer);
            window.wuliFocusTimer = null;
        }
    }, 100);
}
"""