/**
 * 微信服务模块 - 使用 SSE (Server-Sent Events) 进行状态监控
 */

// SSE 连接实例
let wechatStatusEventSource = null;

async function checkWechatLoginStatus() {
    try {
        const response = await fetch('/api/wechat/status');
        if (!response.ok) {
            showWechatStatusIndicator(false);
            return false;
        }
        const contentType = response.headers.get('content-type') || '';
        if (!contentType.includes('application/json')) {
            showWechatStatusIndicator(false);
            return false;
        }
        const data = await response.json();
        if (data.success && data.logined) {
            showWechatStatusIndicator(true);
            return true;
        } else {
            showWechatStatusIndicator(false);
            return false;
        }
    } catch (error) {
        console.error('检测微信登录状态失败:', error);
        showWechatStatusIndicator(false);
        return false;
    }
}

function showWechatStatusIndicator(isLoggedIn) {
    const indicator = document.getElementById('wechatStatusIndicator');
    const statusDot = document.getElementById('wechatStatusDot');
    const statusText = document.getElementById('wechatStatusText');
    
    if (statusDot) {
        if (isLoggedIn) {
            statusDot.classList.add('logged-in');
        } else {
            statusDot.classList.remove('logged-in');
        }
    }
    
    if (statusText) {
        statusText.textContent = isLoggedIn ? '微信已登录' : '微信未登录';
    }
    
    if (indicator) {
        indicator.classList.add('show');
    }
}

function hideWechatStatusIndicator() {
    const indicator = document.getElementById('wechatStatusIndicator');
    if (!indicator) {
        return;
    }
    indicator.classList.remove('show');
}

async function showQRCodePopup() {
    // 旧二维码弹窗已弃用：扫码面板由 pro_feature_widget.js 的十二面体面板统一渲染
    return;
    const popup = document.getElementById('qrcodePopup');
    const qrcodeImage = document.getElementById('qrcodeImage');
    const qrcodeStatus = document.getElementById('qrcodeStatus');
    
    if (!popup || !qrcodeImage || !qrcodeStatus) {
        console.error('找不到二维码弹窗元素');
        return;
    }
    
    popup.classList.remove('hide');
    popup.classList.add('show');
    isQRCodePopupOpen = true;
    
    expandBlueRings();
    
    qrcodeStatus.textContent = '正在获取二维码...';
    qrcodeImage.style.opacity = '0.3';
    
    try {
        await triggerWechatLogin();
        
        qrcodeImage.src = '/api/wechat/qrcode?ts=' + Date.now();
        qrcodeImage.style.opacity = '1';
        qrcodeStatus.textContent = '请使用手机微信扫描二维码登录';
        
        qrcodeImage.onerror = function() {
            console.warn('二维码加载失败，2秒后重试...');
            if (qrcodeStatus) qrcodeStatus.textContent = '二维码加载中，请稍候...';
            setTimeout(() => {
                this.src = '/api/wechat/qrcode?ts=' + Date.now();
            }, 2000);
        };
        
        // 使用 SSE 替代轮询
        startWechatStatusMonitoring();
    } catch (error) {
        console.error('获取二维码失败:', error);
        if (qrcodeStatus) {
            qrcodeStatus.textContent = '获取二维码失败，请刷新重试';
            qrcodeStatus.style.color = '#ff4444';
        }
    }
}

function closeQRCodePopup() {
    // #region agent log
    fetch('/api/debug/client-log',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({runId:'pre-fix-2',hypothesisId:'H5',location:'modules/wechat.js:closeQRCodePopup',message:'called',data:{}})}).catch(()=>{});
    // #endregion agent log
    const popup = document.getElementById('qrcodePopup');
    
    popup.classList.remove('show');
    popup.classList.add('hide');
    isQRCodePopupOpen = false;
    
    collapseBlueRings();
    
    // 停止 SSE 监控
    stopWechatStatusMonitoring();
    
    setTimeout(() => {
        popup.classList.remove('hide');
    }, 400);
}

function expandBlueRings() {
    const rings = document.querySelectorAll('.ring-dashed');
    rings.forEach((ring, index) => {
        setTimeout(() => {
            ring.classList.add('blue-ring', 'expanding');
        }, index * 100);
    });
}

function collapseBlueRings() {
    const rings = document.querySelectorAll('.ring-dashed');
    rings.forEach((ring, index) => {
        setTimeout(() => {
            ring.classList.remove('expanding');
            ring.classList.add('collapsing');
            setTimeout(() => {
                ring.classList.remove('blue-ring', 'collapsing');
            }, 500);
        }, index * 80);
    });
}

async function triggerWechatLogin() {
    // 旧二维码弹窗已弃用
    return;
}

/**
 * 使用 SSE 监控微信登录状态（替代轮询）
 */
function startWechatStatusMonitoring() {
    // 关闭已有的连接
    stopWechatStatusMonitoring();
    
    try {
        console.log('正在建立 SSE 连接监控微信状态...');
        // 旧二维码弹窗已弃用
        return;
        
        wechatStatusEventSource.onopen = function() {
            console.log('SSE 连接已建立');
        };
        
        wechatStatusEventSource.onmessage = function(event) {
            try {
                const data = JSON.parse(event.data);
                console.log('收到 SSE 消息:', data);
                
                if (data.type === 'status') {
                    if (data.logined) {
                        onWechatLoginSuccess();
                    }
                    // 更新状态指示器
                    showWechatStatusIndicator(data.logined);
                } else if (data.type === 'heartbeat') {
                    // 心跳消息，保持连接
                    console.debug('收到心跳');
                }
            } catch (e) {
                console.error('解析 SSE 消息失败:', e);
            }
        };
        
        wechatStatusEventSource.onerror = function(error) {
            console.error('SSE 连接错误:', error);
            // 3秒后重连
            setTimeout(() => {
                if (isQRCodePopupOpen) {
                    console.log('尝试重新建立 SSE 连接...');
                    startWechatStatusMonitoring();
                }
            }, 3000);
        };
        
    } catch (error) {
        console.error('建立 SSE 连接失败:', error);
        // 降级到轮询（备用方案）
        console.warn('SSE 不可用，降级到轮询模式');
        startWechatStatusPollingFallback();
    }
}

function stopWechatStatusMonitoring() {
    if (wechatStatusEventSource) {
        console.log('关闭 SSE 连接');
        wechatStatusEventSource.close();
        wechatStatusEventSource = null;
    }
}

/**
 * 备用：轮询方式（当 SSE 不可用时）
 */
function startWechatStatusPollingFallback() {
    if (wechatStatusCheckInterval) {
        clearInterval(wechatStatusCheckInterval);
    }
    
    wechatStatusCheckInterval = setInterval(async () => {
        try {
            const response = await fetch('/api/wechat/status');
            const data = await response.json();
            
            if (data.success && data.logined) {
                onWechatLoginSuccess();
            }
        } catch (error) {
            console.error('检测登录状态失败:', error);
        }
    }, 5000);
}

function stopWechatStatusPolling() {
    if (wechatStatusCheckInterval) {
        clearInterval(wechatStatusCheckInterval);
        wechatStatusCheckInterval = null;
    }
}

function onWechatLoginSuccess() {
    // 停止监控
    stopWechatStatusMonitoring();
    stopWechatStatusPolling();
    
    showWechatStatusIndicator(true);
    
    const qrcodeStatus = document.getElementById('qrcodeStatus');
    if (qrcodeStatus) {
        qrcodeStatus.textContent = '登录成功！';
        qrcodeStatus.style.color = '#44ff44';
    }
    
    setTimeout(() => {
        closeQRCodePopup();
        if (qrcodeStatus) qrcodeStatus.style.color = '';
    }, 1500);
}

function handleWechatQuestion() {
    // 微信登录由专业悬浮窗的十二面体扫码面板处理
    return;
}

// 页面加载时检查一次状态
document.addEventListener('DOMContentLoaded', () => {
    checkWechatLoginStatus();
});
