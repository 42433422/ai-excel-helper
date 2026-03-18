// 微信扫描面板和消息查看功能

function showWechatScanPanel() {
    const panel = document.getElementById('wechatScanPanel');
    const qrImg = document.getElementById('wechatQrCode');
    const loading = document.getElementById('scanLoading');
    const status = document.getElementById('scanStatus');
    
    if (!panel) return;
    
    panel.style.display = 'block';
    if (qrImg) qrImg.style.display = 'none';
    if (loading) {
        loading.style.display = 'block';
        loading.textContent = '正在获取二维码...';
    }
    if (status) status.textContent = '正在获取二维码...';
    
    fetch('/api/wechat/status')
        .then(r => r.json())
        .then(data => {
            if (!data.logged_in) {
                if (qrImg) {
                    qrImg.src = '/api/wechat/qrcode?ts=' + Date.now();
                    qrImg.onload = function() {
                        if (loading) loading.style.display = 'none';
                        if (qrImg) qrImg.style.display = 'inline';
                        if (status) status.textContent = '请使用手机微信扫描上方二维码';
                    };
                    qrImg.onerror = function() {
                        if (loading) loading.textContent = '二维码加载失败，请重试';
                    };
                }
            } else {
                if (loading) loading.style.display = 'none';
                if (status) status.textContent = '✓ 已登录';
            }
        })
        .catch(() => {
            if (loading) loading.textContent = '获取状态失败';
        });
}

function closeWechatScan() {
    const panel = document.getElementById('wechatScanPanel');
    if (panel) panel.style.display = 'none';
}

function showWechatMessages() {
    const messagesPanel = document.getElementById('wechatMessagesPanel');
    const messagesList = document.getElementById('wechatMessagesList');
    
    if (!messagesPanel) return;
    
    messagesPanel.style.display = 'block';
    
    // 加载消息
    fetch('/api/wechat/messages?limit=50')
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                displayWechatMessages(data.data, messagesList);
            } else {
                messagesList.innerHTML = '<div class="error">加载消息失败：' + data.message + '</div>';
            }
        })
        .catch(err => {
            messagesList.innerHTML = '<div class="error">加载消息失败：' + err + '</div>';
        });
}

function displayWechatMessages(messages, container) {
    if (!container) return;
    
    if (!messages || messages.length === 0) {
        container.innerHTML = '<div class="empty">暂无消息</div>';
        return;
    }
    
    let html = '';
    messages.forEach(msg => {
        const isSelf = msg.is_self;
        const time = msg.time || '';
        const from = msg.from || '未知';
        const content = msg.content || '';
        
        html += `
            <div class="message-item ${isSelf ? 'self' : 'received'}">
                <div class="message-header">
                    <span class="message-from">${from}</span>
                    <span class="message-time">${time}</span>
                </div>
                <div class="message-content">${escapeHtml(content)}</div>
            </div>
        `;
    });
    
    container.innerHTML = html;
}

function closeWechatMessages() {
    const panel = document.getElementById('wechatMessagesPanel');
    if (panel) panel.style.display = 'none';
}

function logoutWechat() {
    if (!confirm('确定要退出微信登录吗？')) return;
    
    fetch('/api/wechat/logout', { method: 'POST' })
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                alert('已退出登录');
                location.reload();
            } else {
                alert('退出失败：' + data.message);
            }
        })
        .catch(err => {
            alert('退出失败：' + err);
        });
}

function clearWechatMessages() {
    if (!confirm('确定要清空消息历史吗？此操作不可恢复。')) return;
    
    fetch('/api/wechat/clear_messages', { method: 'POST' })
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                alert('已清空消息历史');
                showWechatMessages(); // 刷新消息列表
            } else {
                alert('清空失败：' + data.message);
            }
        })
        .catch(err => {
            alert('清空失败：' + err);
        });
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function initWechatScanHandler() {
    const originalSendMessage = window.sendMessage;
    window.sendMessage = function() {
        const input = document.getElementById('messageInput');
        const message = input ? input.value.trim() : '';
        if (!message) return;

        if (message.toLowerCase().includes('微信') || message.toLowerCase().includes('wechat')) {
            if (typeof addMessage === 'function') addMessage(message, 'user');
            if (input) input.value = '';
            showWechatScanPanel();
            return;
        }

        if (originalSendMessage) {
            originalSendMessage.apply(this, arguments);
        }
    };
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initWechatScanHandler);
} else {
    initWechatScanHandler();
}
