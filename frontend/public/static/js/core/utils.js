let currentView = 'chat';
let currentSessionId = localStorage.getItem('ai_session_id') || generateSessionId();
let currentTask = null;
let currentJarvisTask = null;
let wechatStatusCheckInterval = null;
let isQRCodePopupOpen = false;
let cameraStream = null;

function escapeHtml(value) {
    return String(value ?? '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

window.escapeHtml = escapeHtml;

function generateSessionId() {
    return 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
}
