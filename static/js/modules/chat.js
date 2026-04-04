function initConversation() {
    localStorage.setItem('ai_session_id', currentSessionId);
    bindChatControls();
    loadConversationHistory();
}
window.initConversation = initConversation;

function isVueChatOwner() {
    return !!window.__VUE_CHAT_OWNS_INPUT__;
}

let chatControlsBound = false;
function bindChatControls() {
    if (chatControlsBound) return;
    chatControlsBound = true;

    if (isVueChatOwner()) {
        return;
    }

    const newConversationBtn = document.getElementById('newConversationBtn');
    if (newConversationBtn) {
        newConversationBtn.addEventListener('click', newConversation);
    }

    const historyPanelBtn = document.getElementById('historyPanelBtn');
    if (historyPanelBtn) {
        historyPanelBtn.addEventListener('click', loadHistoryPanel);
    }

    const sendMessageBtn = document.getElementById('sendMessageBtn');
    if (sendMessageBtn) {
        sendMessageBtn.addEventListener('click', sendMessage);
    }

    const messageInput = document.getElementById('messageInput');
    if (messageInput) {
        messageInput.addEventListener('keydown', handleKeyDown);
    }

    document.querySelectorAll('.quick-btn[data-quick]').forEach(btn => {
        btn.addEventListener('click', () => sendQuick(btn.getAttribute('data-quick') || ''));
    });

    // 购买单位导入成功后刷新右侧用户名单，使新增项立即可见
    window.addEventListener('customers-imported', function () {
        if (typeof loadCustomers === 'function') {
            setTimeout(function () { loadCustomers(); }, 100);
        }
    });

    const previewBtn = document.querySelector('.quick-btn[data-action="test-preview"]');
    if (previewBtn) {
        previewBtn.addEventListener('click', testPreviewAnimation);
    }
}

function loadConversationHistory() {
    fetch(API_BASE + '/api/conversations/' + currentSessionId)
        .then(r => {
            if (!r.ok) return { success: false, messages: [] };
            return r.json();
        })
        .then(data => {
            if (data.success && data.messages && data.messages.length > 0) {
                const container = document.getElementById('chatMessages');
                container.innerHTML = '';
                data.messages.forEach(msg => {
                    addMessage(msg.content, msg.role);
                });
            }
        })
        .catch(err => console.error('加载历史记录失败:', err));
}

function saveMessage(role, content) {
    fetch(API_BASE + '/api/conversations/message', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            session_id: currentSessionId,
            user_id: 'default',
            role: role,
            content: content
        })
    }).catch(err => console.error('保存消息失败:', err));
}

function loadHistoryPanel() {
    fetch(API_BASE + '/api/conversations/sessions?limit=20')
        .then(r => r.json())
        .then(data => {
            if (data.success && data.sessions) {
                showHistoryPanel(data.sessions);
            }
        })
        .catch(err => console.error('加载历史失败:', err));
}

function showHistoryPanel(sessions) {
    const panel = document.createElement('div');
    panel.className = 'history-panel';
    panel.id = 'historyPanel';
    panel.innerHTML = `
        <div class="history-header">
            <h3>历史对话</h3>
            <button id="closeHistoryPanelBtn">×</button>
        </div>
        <div class="history-list">
            ${sessions.map(s => `
                <div class="history-item" data-session-id="${escapeHtml(s.session_id)}">
                    <div class="history-title">${escapeHtml(s.title || '新会话')}</div>
                    <div class="history-meta">${Number(s.message_count || 0)} 条消息</div>
                </div>
            `).join('')}
        </div>
    `;
    document.body.appendChild(panel);
    panel.classList.add('show');
    const closeBtn = document.getElementById('closeHistoryPanelBtn');
    if (closeBtn) {
        closeBtn.addEventListener('click', closeHistoryPanel);
    }
    panel.querySelectorAll('.history-item[data-session-id]').forEach(item => {
        item.addEventListener('click', () => loadSession(item.getAttribute('data-session-id')));
    });
}

function closeHistoryPanel() {
    const panel = document.getElementById('historyPanel');
    if (panel) panel.classList.remove('show');
}

function loadSession(sessionId) {
    currentSessionId = sessionId;
    localStorage.setItem('ai_session_id', sessionId);
    loadConversationHistory();
    closeHistoryPanel();
}

function newConversation() {
    currentSessionId = generateSessionId();
    localStorage.setItem('ai_session_id', currentSessionId);
    document.getElementById('chatMessages').innerHTML = '';
}

function sendMessage() {
    const input = document.getElementById('messageInput');
    const message = input.value.trim();
    if (!message) return;

    // 如果当前处于“购买单位产品列表库”的多轮确认阶段，优先走 sendChatMessage
    // （避免 __VUE_CHAT_SEND__ 绕过 pending 拦截逻辑）
    try {
        const storageKey = 'xcagiPendingUnitProductsImport';
        let pending = window && window.__xcagiPendingUnitProductsImport;

        // If window state is lost (e.g. refresh), restore from localStorage.
        if (!pending) {
            try {
                const raw = localStorage.getItem(storageKey);
                if (raw) pending = JSON.parse(raw);
                if (pending && window) window.__xcagiPendingUnitProductsImport = pending;
            } catch (_) {}
        }

        if (pending && pending.saved_name && pending.stage) {
            sendChatMessage(message);
            if (input) input.value = '';
            return;
        }
    } catch (_) {}

    if (typeof window.__VUE_CHAT_SEND__ === 'function') {
        window.__VUE_CHAT_SEND__(message);
        if (input) input.value = '';
        return;
    }

    console.log('🔍 sendMessage 收到的消息:', message);

    // 专业模式且为任务类消息时，走 Jarvis 流程（进入任务获取态、执行工具、右侧下载）
    if (document.body && document.body.classList.contains('pro-mode-active') &&
        typeof window.isProTaskAcquisitionMessage === 'function' && window.isProTaskAcquisitionMessage(message) &&
        typeof window.jarvisSendMessage === 'function') {
        window.jarvisSendMessage(message);
        if (input) input.value = '';
        return;
    }

    sendChatMessage(message);
}

function sendChatMessage(message, options = {}) {
    addMessage(message, 'user');
    saveMessage('user', message);
    document.getElementById('messageInput').value = '';

    const loadingId = showLoading();
    
    if (options.thinkingId) {
        const thinkingMsg = document.querySelector(`[data-message-id="${options.thinkingId}"]`);
        if (thinkingMsg) {
            thinkingMsg.remove();
        }
    }

    // 专业版模式切换指令本地优先，避免被后端上下文误判为业务意图。
    try {
        const isProModeActive = !!(document.body && document.body.classList.contains('pro-mode-active'));
        const compact = String(message || '').trim().toLowerCase().replace(/\s+/g, '');
        const wantsWorkMode = compact === '工作模式' || compact === '切换工作模式' || compact === '进入工作模式'
            || compact === 'workmode' || compact === 'switchtoworkmode' || compact === 'enterworkmode';
        const wantsMonitorMode = compact === '监控模式' || compact === '切换监控模式' || compact === '进入监控模式'
            || compact === 'monitormode' || compact === 'switchtomonitormode' || compact === 'entermonitormode';
        if (isProModeActive && (wantsWorkMode || wantsMonitorMode)) {
            removeLoading(loadingId);
            if (wantsMonitorMode) {
                if (typeof window.setMonitorModeFromChat === 'function') {
                    window.setMonitorModeFromChat(true);
                    if (typeof window.refreshWorkModeMonitorList === 'function') window.refreshWorkModeMonitorList();
                    addMessage('正在切换到监控模式...', 'ai');
                    saveMessage('ai', '正在切换到监控模式...');
                } else {
                    addMessage('监控模式入口不可用，已保持当前模式不变。', 'ai');
                    saveMessage('ai', '监控模式入口不可用，已保持当前模式不变。');
                }
            } else {
                if (typeof window.setWorkModeFromChat === 'function') {
                    window.setWorkModeFromChat(true);
                    if (typeof window.refreshWorkModeMonitorList === 'function') window.refreshWorkModeMonitorList();
                    addMessage('正在切换到工作模式...', 'ai');
                    saveMessage('ai', '正在切换到工作模式...');
                } else {
                    addMessage('工作模式入口不可用，已保持当前模式不变。', 'ai');
                    saveMessage('ai', '工作模式入口不可用，已保持当前模式不变。');
                }
            }
            return;
        }
    } catch (_) {}

    // pending import：当文件上传识别到“购买单位产品列表库”后，用户回复是/否/改成... 将触发导入
    try {
        const storageKey = 'xcagiPendingUnitProductsImport';
        let pending = window && window.__xcagiPendingUnitProductsImport;

        // Restore pending import state if window variable is lost (e.g. refresh).
        if (!pending) {
            try {
                const raw = localStorage.getItem(storageKey);
                if (raw) pending = JSON.parse(raw);
                if (pending && window) window.__xcagiPendingUnitProductsImport = pending;
            } catch (_) {}
        }

        // Ensure pending import belongs to the current chat session.
        try {
            const curSessionId = localStorage.getItem('ai_session_id') || '';
            if (pending && pending.session_id && pending.session_id !== curSessionId) {
                try { delete window.__xcagiPendingUnitProductsImport; } catch (_) {}
                try { localStorage.removeItem(storageKey); } catch (_) {}
                return;
            }
        } catch (_) {}

        if (pending && pending.saved_name && pending.stage) {
            const msgTrim = String(message || '').trim();
            const stage = String(pending.stage || 'confirm_filename');
            const candidates = Array.isArray(pending.unit_candidates) ? pending.unit_candidates : [];

            const clearPending = () => {
                try { delete window.__xcagiPendingUnitProductsImport; } catch (_) {}
                try { localStorage.removeItem(storageKey); } catch (_) {}
            };

            const addAi = (text) => {
                removeLoading(loadingId);
                addMessage(text, 'ai');
                try { saveMessage('ai', text); } catch (_) {}
            };

            const doImport = (unitNameToUse) => {
                const body = {
                    saved_name: pending.saved_name,
                    unit_name: (unitNameToUse || '').trim(),
                    create_purchase_unit: true,
                    skip_duplicates: true
                };
                return fetch(API_BASE + '/api/ai/sqlite/import_unit_products', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(body)
                }).then(r => r.json()).then(res => {
                    if (res && res.success) {
                        clearPending();
                        const msg = res.message || `导入成功：${body.unit_name}`;
                        addAi(msg);
                    } else {
                        const errMsg = (res && res.message) ? res.message : '导入失败（未知错误）';
                        addAi('导入失败：' + errMsg);
                    }
                }).catch(e => {
                    addAi('导入请求失败：' + (e && e.message ? e.message : String(e)));
                });
            };

            // 解析“改成/改为”
            const renameMatch = msgTrim.match(/^(改成|改为)\s*(.+)$/);

            if (stage === 'confirm_filename') {
                const yesMatch = /^(是|确认|确定|导入|开始导入|执行|添加购买单位)/.test(msgTrim);
                const noMatch = /^(否|取消|不导入|不要|别导入|不用|停止)/.test(msgTrim);

                if (renameMatch && renameMatch[2]) {
                    doImport(renameMatch[2]);
                    return;
                }
                if (noMatch) {
                    pending.stage = 'choose_candidate';
                    if (candidates.length > 0) {
                        const list = candidates
                            .slice(0, 10)
                            .map((u, i) => `${i + 1})${u}`)
                            .join('  ');
                        addAi('好的。我从该库里提取到一些“购买单位”候选：' + list + '。回复序号或直接输入名称即可导入。');
                    } else {
                        addAi('我从该库里没有提取到购买单位候选。请你直接回复“改成 <名称>”。');
                    }
                    return;
                }
                if (yesMatch) {
                    const guess = (pending.unit_name_guess || '').trim();
                    if (guess) {
                        doImport(guess);
                        return;
                    }
                    // If we can't guess unit_name, ask user to pick an available candidate.
                    pending.stage = 'choose_candidate';
                    if (candidates.length > 0) {
                        const list = candidates
                            .slice(0, 10)
                            .map((u, i) => `${i + 1})${u}`)
                            .join('  ');
                        addAi('好的。但我没法从文件名猜到购买单位名称。候选如下：' + list + '。回复序号或直接输入名称即可导入。');
                    } else {
                        addAi('我从该库里没有提取到购买单位候选。请你直接回复“改成 <名称>”。');
                    }
                    return;
                }

                addAi('没太明白。请回复：是 / 否 / 改成 <名称>。');
                return;
            }

            if (stage === 'choose_candidate') {
                const cancelMatch = /^(取消|不导入|不要|别导入|不用|停止|算了)/.test(msgTrim);
                if (cancelMatch) {
                    clearPending();
                    removeLoading(loadingId);
                    addMessage('已取消导入。', 'ai');
                    try { saveMessage('ai', '已取消导入。'); } catch (_) {}
                    return;
                }

                if (renameMatch && renameMatch[2]) {
                    doImport(renameMatch[2]);
                    return;
                }

                const numMatch = msgTrim.match(/^(\d{1,2})$/) || msgTrim.match(/^(\d{1,2})号$/);
                if (numMatch && numMatch[1]) {
                    const idx = parseInt(numMatch[1], 10) - 1;
                    if (idx >= 0 && idx < candidates.length) {
                        doImport(candidates[idx]);
                        return;
                    }
                }

                // 兜底：把用户输入当作名称
                if (msgTrim.length >= 2 && !/^(是|否|确认|确定|导入|取消)/.test(msgTrim)) {
                    doImport(msgTrim);
                    return;
                }

                addAi('请回复候选序号（如 1/2/3）或直接输入购买单位名称。');
                return;
            }
        }
    } catch (e) {
        // 不影响正常聊天
        console.warn('pending import intercept failed:', e);
    }

    callUnifiedChat({
        message: message,
        isWechatCheck: options.isWechatCheck || false
    }).then(data => {
        removeLoading(loadingId);
        if (data.success) {
            addMessage(data.response, 'ai');
            saveMessage('ai', data.response);
            if (data.task) showTaskConfirm(data.task);
            
            if (data.autoAction) {
                console.log('🔧 检测到自动操作:', data.autoAction);
                console.log('🔧 proFeatureWidget存在:', !!window.proFeatureWidget);
                handleAutoAction(data.autoAction, message);
            }
        } else {
            addMessage('处理失败: ' + data.message, 'ai');
        }
    }).catch(e => {
        removeLoading(loadingId);
        addMessage('连接失败: ' + e.message, 'ai');
    });
}

function callUnifiedChat(payload) {
    const headers = {'Content-Type': 'application/json'};
    return fetch(API_BASE + '/api/ai/chat-unified', {
        method: 'POST',
        headers,
        body: JSON.stringify(payload || {})
    }).then(async (r) => {
        if (r.status === 404) {
            return fetch(API_BASE + '/api/ai/chat', {
                method: 'POST',
                headers,
                body: JSON.stringify(payload || {})
            }).then(rr => rr.json());
        }
        return r.json();
    });
}

function sendQuick(msg) {
    document.getElementById('messageInput').value = msg;
    sendMessage();
}

function handleAutoAction(action, userMessage = '') {
    console.log('🔧 执行自动操作:', action);
    console.log('🔧 action.type:', action.type);
    console.log('🔧 proFeatureWidget存在:', !!window.proFeatureWidget);
    if (action && action.type === 'show_products_float') {
        window.dispatchEvent(new CustomEvent('xcagi:open-assistant-float', {
            detail: { feature: 'products', query: action.query || userMessage || '' }
        }));
        return;
    }
    
    if (!window.proFeatureWidget) {
        console.log('⚠️ proFeatureWidget未初始化，尝试初始化');
        if (typeof initProFeatureWidget === 'function') {
            initProFeatureWidget();
        }
    }
    
    switch(action.type) {
        case 'show_login':
        case 'show_contacts':
            // 微信相关功能已移除，不再调用
            break;
        case 'show_products':
            showProductsPanel(action.query);
            break;
        case 'show_customers':
            showUserListInRightPanel(userMessage);
            break;
        case 'export_customers_xlsx':
            exportCustomersXlsx();
            break;
        case 'show_print':
            showPrintPanel();
            break;
        case 'show_materials':
            showMaterialsPanel();
            break;
        case 'show_orders':
            showOrdersPanel();
            break;
        case 'show_file_upload':
            showFileUploadPanel(action.purpose);
            break;
        case 'show_labels_export':
            if (action.labels && Array.isArray(action.labels) && action.labels.length > 0) {
                showLabelsExportPanelWithLabels(action.labels);
            } else {
                showLabelsExportPanel();
            }
            break;
        case 'set_work_mode':
            if (typeof window.setWorkModeFromChat === 'function') {
                window.setWorkModeFromChat(!!action.enabled);
            }
            break;
        case 'show_monitor':
            // 监控模式只走独立入口；缺失时保持当前模式，避免静默串扰。
            if (typeof window.setMonitorModeFromChat === 'function') {
                window.setMonitorModeFromChat(true);
            } else {
                console.warn('[pro-runtime] monitor mode entry missing; skip fallback to work mode');
                if (typeof addMessage === 'function') {
                    addMessage('监控模式入口不可用，已保持当前模式不变。', 'ai');
                }
                break;
            }
            if (typeof window.refreshWorkModeMonitorList === 'function') {
                window.refreshWorkModeMonitorList();
            }
            break;
        case 'show_wechat_messages':
            // 微信消息功能已移除
            break;
        case 'show_images':
            showMediaPanel('image', action.source);
            break;
        case 'show_videos':
            showMediaPanel('video', action.source);
            break;
        case 'already_logged':
            break;
        case 'tool_call':
            console.log('🔧 执行工具调用:', action.tool_key, action.params);
            if (action.tool_key === 'products') {
                const query = action.params?.model_number || action.params?.keyword || action.query || '';
                const unitName = action.params?.unit_name || '';
                showProductsPanel(query, unitName);
            } else if (action.tool_key === 'customers') {
                showCustomersPanel();
            } else if (action.tool_key === 'shipments') {
                showOrdersPanel();
            } else if (action.tool_key === 'print_label') {
                showPrintPanel();
            } else if (action.tool_key === 'materials') {
                showMaterialsPanel();
            } else if (action.tool_key === 'show_labels_export') {
                showLabelsExportPanel();
            }
            break;
        default:
            console.log('未知操作类型:', action.type);
    }
}

// 暴露给专业模式（Jarvis）统一复用
window.__legacyHandleAutoAction = handleAutoAction;
if (!window.__VUE_HANDLE_AUTO_ACTION__) {
    window.handleAutoAction = handleAutoAction;
}

function showProductsPanel(query, unitName) {
    const isProModeActive = !!(document.body && document.body.classList.contains('pro-mode-active'));
    if (isProModeActive && window.proFeatureWidget && typeof window.proFeatureWidget.showFeature === 'function') {
        const config = { query: query || '' };
        if (unitName) config.unit_name = unitName;
        window.proFeatureWidget.showFeature('product_query', config);
        return;
    }

    // 非专业版优先使用统一视图切换，避免依赖旧的 href 菜单结构
    if (typeof switchView === 'function') {
        switchView('products');
    } else {
        const productsMenu = document.querySelector('.menu-item[data-view="products"]');
        const productsLink = document.querySelector('a[href*="database"], a[href*="products"]');
        if (productsMenu) productsMenu.click();
        else if (productsLink) productsLink.click();
    }

    if (query) {
        setTimeout(() => {
            const searchInput = document.getElementById('productSearch')
                || document.querySelector('input[placeholder*="搜索"], input[id*="search"]');
            if (searchInput) {
                searchInput.value = query;
                searchInput.dispatchEvent(new Event('input'));
            }
        }, 280);
    }
}

function showCustomersPanel() {
    if (typeof switchView === 'function') {
        switchView('customers');
    }
}

let customersExportEntryHideTimer = null;

function ensureCustomersExportEntry() {
    let entry = document.getElementById('customersExportEntry');
    if (entry) return entry;

    entry = document.createElement('div');
    entry.id = 'customersExportEntry';
    entry.className = 'file-upload-entry';
    entry.innerHTML = `
        <span class="entry-icon">⬇️</span>
        <span class="entry-text">下载购买单位XLSX</span>
    `;
    entry.addEventListener('click', () => {
        const url = entry.getAttribute('data-download-url') || '';
        downloadCustomersXlsxFile(url);
    });
    document.body.appendChild(entry);
    return entry;
}

function getFilenameFromDisposition(disposition, fallback = '购买单位列表.xlsx') {
    if (!disposition) return fallback;
    const utf8Match = disposition.match(/filename\*=UTF-8''([^;]+)/i);
    if (utf8Match && utf8Match[1]) {
        try { return decodeURIComponent(utf8Match[1]); } catch (_) {}
    }
    const plainMatch = disposition.match(/filename="?([^"]+)"?/i);
    if (plainMatch && plainMatch[1]) return plainMatch[1];
    return fallback;
}

async function downloadCustomersXlsxFile(url) {
    if (!url) return;
    const entry = document.getElementById('customersExportEntry');
    const textEl = entry ? entry.querySelector('.entry-text') : null;
    const oldText = textEl ? textEl.textContent : '';
    if (textEl) textEl.textContent = '正在下载...';
    if (entry) entry.classList.add('show');
    try {
        const response = await fetch(url, { method: 'GET' });
        if (!response.ok) {
            throw new Error(`下载失败(${response.status})`);
        }
        const blob = await response.blob();
        const filename = getFilenameFromDisposition(
            response.headers.get('content-disposition'),
            '购买单位列表.xlsx'
        );
        const blobUrl = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = blobUrl;
        link.download = filename;
        link.style.display = 'none';
        document.body.appendChild(link);
        link.click();
        setTimeout(() => {
            link.remove();
            URL.revokeObjectURL(blobUrl);
        }, 0);
        if (textEl) textEl.textContent = '已开始下载';
        setTimeout(() => {
            if (textEl) textEl.textContent = oldText || '下载购买单位XLSX';
            if (entry) entry.classList.remove('show');
        }, 1200);
    } catch (err) {
        if (textEl) textEl.textContent = `下载失败: ${(err && err.message) ? err.message : '未知错误'}`;
        setTimeout(() => {
            if (textEl) textEl.textContent = oldText || '下载购买单位XLSX';
        }, 1800);
    }
}

function exportCustomersXlsx() {
    const apiBase = (typeof API_BASE !== 'undefined' ? API_BASE : '');
    const entry = ensureCustomersExportEntry();
    // 后端客户导出接口是 `/api/customers/export`
    const url = `${apiBase}/api/customers/export`;
    entry.setAttribute('data-download-url', url);
    entry.classList.add('show');
    if (typeof hideFileUploadEntry === 'function') {
        hideFileUploadEntry();
    }
    if (customersExportEntryHideTimer) {
        clearTimeout(customersExportEntryHideTimer);
    }
    customersExportEntryHideTimer = setTimeout(() => {
        entry.classList.remove('show');
    }, 20000);
}

let shipmentDownloadEntryHideTimer = null;

function ensureShipmentDownloadEntry() {
    let entry = document.getElementById('shipmentDownloadEntry');
    if (entry) return entry;

    entry = document.createElement('div');
    entry.id = 'shipmentDownloadEntry';
    entry.className = 'file-upload-entry shipment-download-entry';
    entry.innerHTML = `
        <span class="entry-icon">📄</span>
        <span class="entry-text">下载发货单</span>
    `;
    entry.addEventListener('click', () => {
        const url = entry.getAttribute('data-download-url') || '';
        const name = entry.getAttribute('data-download-filename') || '发货单.xlsx';
        if (url) downloadShipmentFile(url, name);
    });
    const uploadEntry = document.getElementById('fileUploadEntry');
    if (uploadEntry && uploadEntry.parentNode) {
        uploadEntry.parentNode.insertBefore(entry, uploadEntry.nextSibling);
    } else {
        document.body.appendChild(entry);
    }
    return entry;
}

function downloadShipmentFile(url, filename) {
    const entry = document.getElementById('shipmentDownloadEntry');
    const textEl = entry ? entry.querySelector('.entry-text') : null;
    const oldText = textEl ? textEl.textContent : '';
    if (textEl) textEl.textContent = '正在下载...';
    if (entry) entry.classList.add('show');
    fetch(url, { method: 'GET' })
        .then(r => {
            if (!r.ok) throw new Error('下载失败');
            return r.blob();
        })
        .then(blob => {
            const blobUrl = URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = blobUrl;
            link.download = filename || '发货单.xlsx';
            link.style.display = 'none';
            document.body.appendChild(link);
            link.click();
            setTimeout(() => {
                link.remove();
                URL.revokeObjectURL(blobUrl);
            }, 0);
            if (textEl) textEl.textContent = '已开始下载';
        })
        .catch(() => {
            if (textEl) textEl.textContent = '下载失败';
        })
        .finally(() => {
            setTimeout(() => {
                if (textEl) textEl.textContent = oldText || '下载发货单';
                if (entry) entry.classList.remove('show');
            }, 1200);
        });
}

function showShipmentDownloadEntry(filename) {
    if (!filename) return;
    const apiBase = (typeof API_BASE !== 'undefined' ? API_BASE : '');
    const entry = ensureShipmentDownloadEntry();
    const url = apiBase + '/outputs/' + encodeURIComponent(filename);
    entry.setAttribute('data-download-url', url);
    entry.setAttribute('data-download-filename', filename);
    const textEl = entry.querySelector('.entry-text');
    if (textEl) textEl.textContent = '下载 ' + (filename.length > 20 ? filename.slice(0, 16) + '…' : filename);
    entry.classList.add('show');
    if (shipmentDownloadEntryHideTimer) clearTimeout(shipmentDownloadEntryHideTimer);
    shipmentDownloadEntryHideTimer = setTimeout(() => {
        entry.classList.remove('show');
        if (textEl) textEl.textContent = '下载发货单';
    }, 60000);
}

window.showShipmentDownloadEntry = showShipmentDownloadEntry;

function showUserListInRightPanel(userMessage = '') {
    if (typeof switchView === 'function') {
        switchView('chat');
    }

    const isProModeActive = !!(document.body && document.body.classList.contains('pro-mode-active'));
    if (isProModeActive && window.proFeatureWidget && typeof window.proFeatureWidget.showFeature === 'function') {
        window.proFeatureWidget.showFeature('user_list', { query: userMessage || '' });
        return;
    }

    const panel = document.getElementById('taskPanel');
    if (!panel) return;
    panel.innerHTML = '<div class="empty-state">正在加载用户名单...</div>';

    fetch(API_BASE + '/api/customers')
        .then(r => r.json())
        .then(data => {
            if (!data.success) {
                throw new Error(data.message || '加载失败');
            }
            const customers = data.customers || data.data || [];
            renderUserListPanel(customers, userMessage);
        })
        .catch(err => {
            panel.innerHTML = `<div class="empty-state">加载用户列表失败：${escapeHtml(err.message || '未知错误')}</div>`;
        });
}

function renderUserListPanel(customers, userMessage = '') {
    const panel = document.getElementById('taskPanel');
    const header = document.querySelector('.right-panel .panel-header');
    if (!panel) return;
    if (header) {
        header.innerHTML = '<span>用户名单（可编辑）</span><button class="btn-icon btn-excel" id="panelExportExcelBtn" title="导出购买单位Excel"><svg class="excel-icon-svg" viewBox="0 0 24 24" width="20" height="20"><rect width="24" height="24" rx="3" fill="#217346"/><path stroke="#fff" stroke-width="2.2" stroke-linecap="round" fill="none" d="M7 7l10 10M17 7L7 17"/></svg></button>';
        header.style.display = 'flex';
        header.style.justifyContent = 'space-between';
        header.style.alignItems = 'center';
        const excelBtn = document.getElementById('panelExportExcelBtn');
        if (excelBtn) {
            excelBtn.addEventListener('click', () => exportCustomersXlsx());
        }
    }

    if (!Array.isArray(customers) || customers.length === 0) {
        panel.innerHTML = '<div class="empty-state">暂无用户数据</div>';
        return;
    }

    const apiBase = (typeof API_BASE !== 'undefined' ? API_BASE : '');
    const exportBtn = `
        <div class="user-list-hint" style="display:flex;justify-content:flex-end;margin-bottom:8px;">
            <button class="btn btn-secondary btn-sm" id="exportCustomersXlsxBtn">导出XLSX</button>
        </div>
    `;
    const hint = userMessage
        ? `<div class="user-list-hint">已根据指令展示：${escapeHtml(userMessage)}</div>`
        : '<div class="user-list-hint">支持手动编辑；也支持对话编辑，例如：把用户成都国圣的电话改成13800000000</div>';

    const rows = customers.map(c => {
        const id = Number(c.id || 0);
        const name = escapeHtml(c.customer_name || c.unit_name || c.name || '');
        const contact = escapeHtml(c.contact_person || '');
        const phone = escapeHtml(c.contact_phone || '');
        const address = escapeHtml(c.address || '');
        return `
            <div class="user-edit-card" data-customer-id="${id}">
                <div class="user-edit-title">${name || '未命名用户'}</div>
                <label>联系人</label>
                <input type="text" class="user-edit-input" data-field="contact_person" value="${contact}">
                <label>电话</label>
                <input type="text" class="user-edit-input" data-field="contact_phone" value="${phone}">
                <label>地址</label>
                <input type="text" class="user-edit-input" data-field="address" value="${address}">
                <button class="btn btn-primary btn-sm user-save-btn" data-action="save-user" data-id="${id}">
                    保存
                </button>
            </div>
        `;
    }).join('');

    panel.innerHTML = `${exportBtn}${hint}<div class="user-edit-list">${rows}</div>`;
    const exportBtnEl = document.getElementById('exportCustomersXlsxBtn');
    if (exportBtnEl) {
        exportBtnEl.addEventListener('click', () => {
            exportCustomersXlsx();
        });
    }
    panel.querySelectorAll('[data-action="save-user"]').forEach(btn => {
        btn.addEventListener('click', () => saveUserEdit(btn));
    });
}

function saveUserEdit(button) {
    const customerId = Number(button.getAttribute('data-id') || 0);
    if (!customerId) return;
    const card = button.closest('.user-edit-card');
    if (!card) return;

    const payload = {
        contact_person: (card.querySelector('[data-field="contact_person"]')?.value || '').trim(),
        contact_phone: (card.querySelector('[data-field="contact_phone"]')?.value || '').trim(),
        address: (card.querySelector('[data-field="address"]')?.value || '').trim(),
        discount_rate: 1,
        is_active: 1
    };

    const originalText = button.textContent;
    button.disabled = true;
    button.textContent = '保存中...';

    fetch(API_BASE + '/api/customers/' + customerId, {
        method: 'PUT',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(payload)
    })
        .then(r => r.json())
        .then(data => {
            if (!data.success) {
                throw new Error(data.message || '保存失败');
            }
            button.textContent = '已保存';
            setTimeout(() => {
                button.textContent = originalText;
                button.disabled = false;
            }, 800);
        })
        .catch(err => {
            alert('保存失败: ' + (err.message || '未知错误'));
            button.textContent = originalText;
            button.disabled = false;
        });
}

function showPrintPanel() {
    var win = document.getElementById('printPanelWindow');
    var statusEl = document.getElementById('printPanelStatus');
    var progressEl = document.getElementById('printPanelProgress');
    var resultsEl = document.getElementById('printPanelResults');
    var startBtn = document.getElementById('printPanelStartBtn');
    if (!win || !statusEl) return;

    win.classList.add('show');
    progressEl.style.display = 'none';
    progressEl.textContent = '';
    resultsEl.innerHTML = '';
    statusEl.textContent = '正在连接打印机...';
    if (startBtn) { startBtn.disabled = false; startBtn.textContent = '开始打印'; }

    var apiBase = typeof API_BASE !== 'undefined' ? API_BASE : '';
    fetch(apiBase + '/api/printers')
        .then(function(r) { return r.ok ? r.json() : Promise.reject(new Error('获取打印机失败')); })
        .then(function(data) {
            var label = data.classified && data.classified.label_printer;
            var name = label && label.name;
            var connected = label && label.is_connected;
            if (connected && name) {
                statusEl.textContent = '标签打印机已连接：' + name;
            } else {
                statusEl.textContent = '未检测到标签打印机，请检查连接后点击「开始打印」重试。';
            }
        })
        .catch(function(e) {
            statusEl.textContent = '连接打印机失败：' + (e && e.message ? e.message : '请稍后重试');
        });

    if (!window._printPanelBound) {
        window._printPanelBound = true;
        function closePrintPanel() {
            var w = document.getElementById('printPanelWindow');
            if (w) w.classList.remove('show');
        }
        ['printPanelCloseBtn', 'printPanelCloseBtn2'].forEach(function(id) {
            var btn = document.getElementById(id);
            if (btn) btn.addEventListener('click', closePrintPanel);
        });
        if (startBtn) {
            startBtn.addEventListener('click', function() {
                if (startBtn.disabled) return;
                startBtn.disabled = true;
                startBtn.textContent = '打印中...';
                progressEl.style.display = 'block';
                progressEl.textContent = '正在连接打印机并调用打印 API...';
                resultsEl.innerHTML = '';

                fetch(apiBase + '/api/print/all_labels', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: '{}' })
                    .then(function(r) { return r.json(); })
                    .then(function(res) {
                        progressEl.style.display = 'none';
                        startBtn.disabled = false;
                        startBtn.textContent = '开始打印';
                        if (res.success) {
                            statusEl.textContent = res.message || '打印完成';
                            var total = res.total || 0;
                            var successCount = res.success_count != null ? res.success_count : (res.results ? res.results.filter(function(x) { return x.success; }).length : 0);
                            var html = '<p class="labels-export-hint">共 ' + total + ' 张，成功 ' + successCount + ' 张</p>';
                            if (res.results && res.results.length) {
                                html += '<ul class="labels-export-ul">';
                                res.results.forEach(function(item) {
                                    var ok = item.success ? '✓' : '✗';
                                    html += '<li>' + ok + ' ' + (item.filename || '') + (item.message ? ' — ' + item.message : '') + '</li>';
                                });
                                html += '</ul>';
                            }
                            resultsEl.innerHTML = html;
                        } else {
                            statusEl.textContent = '打印失败：' + (res.message || '未知错误');
                            resultsEl.innerHTML = '<p class="labels-export-hint">' + (res.message || '') + '</p>';
                        }
                    })
                    .catch(function(e) {
                        progressEl.style.display = 'none';
                        startBtn.disabled = false;
                        startBtn.textContent = '开始打印';
                        statusEl.textContent = '打印请求失败';
                        resultsEl.innerHTML = '<p class="labels-export-hint">' + (e && e.message ? e.message : '网络错误') + '</p>';
                    });
            });
        }
    }
}

function showMaterialsPanel() {
    const materialsLink = document.querySelector('a[href*="materials"], a[href*="原材料"]');
    if (materialsLink) {
        materialsLink.click();
    }
}

function showOrdersPanel() {
    // 优先使用全局的 switchView
    if (typeof switchView === 'function') {
        switchView('orders');
        return;
    }
    const ordersLink = document.querySelector('a[href*="orders"], a[href*="订单"], a[href*="出货"]');
    if (ordersLink) ordersLink.click();
}

function showFileUploadPanel(purpose) {
    // 专业模式下优先显示右下角科技化入口，避免直接弹窗打断
    const proOverlay = document.getElementById('proModeOverlay');
    const isProModeActive = !!(proOverlay && proOverlay.classList.contains('active'));
    if (isProModeActive && typeof showFileUploadEntry === 'function') {
        showFileUploadEntry();
        return;
    }

    // 优先直接打开导入窗口，并传入用途
    if (typeof openImportWindow === 'function') {
        openImportWindow(purpose || 'general');
        return;
    }
    // 兜底：点击页面右下角入口（fileUploadEntry）
    const entry = document.getElementById('fileUploadEntry');
    if (entry) {
        entry.click();
        return;
    }
}

function showLabelsExportPanel() {
    var win = document.getElementById('labelsExportWindow');
    var listEl = document.getElementById('labelsExportList');
    var floatContainer = document.getElementById('labelFloatPreviews');
    if (!win || !listEl) return;
    _bindLabelPreviewModalClose();
    listEl.innerHTML = '<p class="labels-export-hint">加载中...</p>';
    win.classList.add('show');
    if (floatContainer) {
        floatContainer.classList.remove('hidden');
        floatContainer.innerHTML = '';
    }
    var apiBase = typeof API_BASE !== 'undefined' ? API_BASE : '';
    fetch(apiBase + '/api/print/list_labels')
        .then(function(r) {
            if (!r.ok) {
                return r.json().then(function(err) { throw new Error(err.message || '请求失败 ' + r.status); }).catch(function() { throw new Error('请求失败 ' + r.status); });
            }
            return r.json();
        })
        .then(function(data) {
            if (data && data.success && Array.isArray(data.labels) && data.labels.length > 0) {
                renderLabelPanel(data.labels);
            } else {
                listEl.innerHTML = '<p class="labels-export-hint">暂无标签文件。请先生成发货单，系统会自动生成标签到商标导出。</p>';
                if (floatContainer) { floatContainer.innerHTML = ''; floatContainer.classList.add('hidden'); }
            }
        })
        .catch(function(e) {
            listEl.innerHTML = '<p class="labels-export-hint">加载失败：' + (e && e.message ? e.message : '请稍后重试') + '。</p>';
            if (floatContainer) { floatContainer.innerHTML = ''; floatContainer.classList.add('hidden'); }
        });
}

function showLabelsExportPanelWithLabels(labels) {
    var win = document.getElementById('labelsExportWindow');
    var listEl = document.getElementById('labelsExportList');
    var floatContainer = document.getElementById('labelFloatPreviews');
    if (!win || !listEl) return;
    _bindLabelPreviewModalClose();
    listEl.innerHTML = '<p class="labels-export-hint">加载中...</p>';
    win.classList.add('show');
    if (floatContainer) {
        floatContainer.classList.remove('hidden');
        floatContainer.innerHTML = '';
    }
    if (labels && Array.isArray(labels) && labels.length > 0) {
        renderLabelPanel(labels);
    } else {
        listEl.innerHTML = '<p class="labels-export-hint">暂无标签文件。请先生成发货单，系统会自动生成标签到商标导出。</p>';
        if (floatContainer) { floatContainer.innerHTML = ''; floatContainer.classList.add('hidden'); }
    }
}

function renderLabelPanel(labels) {
    var listEl = document.getElementById('labelsExportList');
    var floatContainer = document.getElementById('labelFloatPreviews');
    if (!listEl) return;
    var base = window.location.origin || (window.location.protocol + '//' + window.location.host);
    var html = '<p class="labels-export-hint" style="margin-bottom:10px;">点击文件名下载标签（共 ' + labels.length + ' 个）</p><ul class="labels-export-ul">';
    labels.forEach(function(item) {
        var url = base + '/api/print/label/' + encodeURIComponent(item.filename);
        var label = (item.order_number || '') + ' 第' + (item.label_number || '') + ' 项';
        html += '<li><a href="' + url + '" download="' + (item.filename || 'label.png') + '" target="_blank" rel="noopener">' + (item.filename || label) + '</a></li>';
    });
    html += '</ul>';
    listEl.innerHTML = html;
    if (floatContainer) {
        var maxPreviews = Math.min(8, labels.length);
        for (var i = 0; i < maxPreviews; i++) {
            var item = labels[i];
            var url = base + '/api/print/label/' + encodeURIComponent(item.filename);
            var img = document.createElement('img');
            img.className = 'label-float-preview';
            img.src = url;
            img.alt = item.filename || ('标签 ' + (i + 1));
            img.loading = 'lazy';
            img.setAttribute('data-download-url', url);
            img.setAttribute('data-filename', item.filename || 'label.png');
            img.addEventListener('click', function (e) {
                e.preventDefault();
                var u = this.getAttribute('data-download-url');
                var f = this.getAttribute('data-filename');
                if (!u) return;
                var modal = document.getElementById('labelPreviewModal');
                var modalImg = document.getElementById('labelPreviewModalImg');
                var modalDownload = document.getElementById('labelPreviewModalDownload');
                if (modal && modalImg && modalDownload) {
                    modalImg.src = u;
                    modalDownload.href = u;
                    modalDownload.download = f;
                    modal.classList.remove('hidden');
                    modal.setAttribute('aria-hidden', 'false');
                }
            });
            floatContainer.appendChild(img);
        }
    }
}

function closeLabelsPanel() {
    var win = document.getElementById('labelsExportWindow');
    if (win) win.classList.remove('show');
    var c = document.getElementById('labelFloatPreviews');
    if (c) { c.innerHTML = ''; c.classList.add('hidden'); }
}

function _bindLabelExportClose() {
    if (window._labelsExportCloseBound) return;
    window._labelsExportCloseBound = true;
    var win = document.getElementById('labelsExportWindow');
    if (!win) return;
    ['labelsExportCloseBtn', 'labelsExportCloseBtn2'].forEach(function(id) {
        var btn = document.getElementById(id);
        if (btn) btn.addEventListener('click', closeLabelsPanel);
    });
}

function _bindLabelPreviewModalClose() {
    if (window._labelPreviewModalBound) return;
    window._labelPreviewModalBound = true;
    var modal = document.getElementById('labelPreviewModal');
    if (!modal) return;
    var backdrop = modal.querySelector('.label-preview-modal-backdrop');
    var closeBtn = modal.querySelector('.label-preview-modal-close');
    function closeModal() {
        modal.classList.add('hidden');
        modal.setAttribute('aria-hidden', 'true');
        var img = document.getElementById('labelPreviewModalImg');
        if (img) img.src = '';
    }
    if (backdrop) backdrop.addEventListener('click', closeModal);
    if (closeBtn) closeBtn.addEventListener('click', closeModal);
}

function showWechatMessagesPanel() {
    if (window.proFeatureWidget && typeof window.proFeatureWidget.showFeature === 'function') {
        window.proFeatureWidget.showFeature('wechat_messages');
    } else {
        const messagesPanel = document.getElementById('wechatMessagesPanel');
        if (messagesPanel) {
            messagesPanel.style.display = 'block';
        }
    }
}

function showMediaPanel(mediaType, source) {
    if (window.proFeatureWidget && typeof window.proFeatureWidget.showMediaPanel === 'function') {
        window.proFeatureWidget.showMediaPanel(mediaType, source);
    } else {
        console.log('⚠️ proFeatureWidget未加载十二面体媒体面板');
        addMessage('📺 媒体面板功能正在加载中...', 'ai');
    }
}

let lastWechatPopupTime = 0;

function addMessage(content, type) {
    if (type === 'ai' && content && typeof content === 'string') {
        const contentLower = content.toLowerCase();
        const now = Date.now();
        
        if (contentLower.includes('微信') || contentLower.includes('wechat') || 
            contentLower.includes('登录') || contentLower.includes('扫码')) {
            
            const timeSinceLastPopup = now - lastWechatPopupTime;
            if (timeSinceLastPopup > 5000) {
                console.log('🤖 AI 消息(addMessage)包含微信关键词，但跳过避免重复弹窗');
            } else {
                console.log('🤖 AI 消息(addMessage)包含微信关键词，但刚显示过，跳过');
            }
        }

        const fileKeywords = [
            '上传文件', '导入文件', '请上传', '请提供', '请导入',
            '需要文件', '读取文件', '处理文件', '分析文件',
            '上传图片', '导入图片', '上传excel', '导入excel',
            '上传文档', '上传csv', '请选择文件', '请拖拽文件',
            'upload', 'import file', 'please upload'
        ];
        const needsFile = fileKeywords.some(keyword => contentLower.includes(keyword.toLowerCase()));
        if (needsFile) {
            console.log('🤖 AI 消息(addMessage)包含文件相关关键词，显示文件上传入口');
            showFileUploadEntry();
        }
    }

    const container = document.getElementById('chatMessages');
    const time = new Date().toLocaleTimeString('zh-CN', {hour: '2-digit', minute: '2-digit'});
    const safeContent = escapeHtml(content).replace(/\n/g, '<br>');
    const safeTime = escapeHtml(time);
    const div = document.createElement('div');
    div.className = 'message ' + type;
    div.innerHTML = `<div>${safeContent}</div><div class="time">${safeTime}</div>`;
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
}

function showLoading() {
    const id = 'loading-' + Date.now();
    const container = document.getElementById('chatMessages');
    const div = document.createElement('div');
    div.className = 'message ai';
    div.id = id;
    div.innerHTML = '<div><span class="status-dot online"></span> 处理中...</div>';
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
    return id;
}

function removeLoading(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
}

function showTaskConfirm(task) {
    const panel = document.getElementById('taskPanel');
    let itemsHtml = '';
    if (task.items && task.items.length > 0) {
        const keys = Object.keys(task.items[0]);
        itemsHtml = '<table class="data-table" style="margin-top:10px;"><thead><tr>' + 
            keys.map(k => '<th>' + escapeHtml(k) + '</th>').join('') + '</tr></thead><tbody>' +
            task.items.map(item => '<tr>' + keys.map(k => '<td>' + escapeHtml(item[k]) + '</td>').join('') + '</tr>').join('') +
            '</tbody></table>';
    }
    panel.innerHTML = `
        <div class="task-card">
            <div class="task-header">${escapeHtml(task.title)}</div>
            <div>${escapeHtml(task.description)}</div>
            ${itemsHtml}
            <div class="task-actions">
                <button class="btn btn-success btn-sm" data-action="confirm-task">确认执行</button>
                <button class="btn btn-secondary btn-sm" data-action="cancel-task">取消</button>
            </div>
        </div>
    `;
    window.currentTask = task;
    panel.querySelector('[data-action="confirm-task"]')?.addEventListener('click', confirmTask);
    panel.querySelector('[data-action="cancel-task"]')?.addEventListener('click', cancelTask);
}

function confirmTask() {
    alert('任务已确认执行');
    window.currentTask = null;
    document.getElementById('taskPanel').innerHTML = '<div class="empty-state">暂无任务</div>';
}

function cancelTask() {
    window.currentTask = null;
    document.getElementById('taskPanel').innerHTML = '<div class="empty-state">暂无任务</div>';
}

function addTask(taskId, taskName) {
    const panel = document.getElementById('taskPanel');
    const emptyState = panel.querySelector('.empty-state, .task-list-empty');
    if (emptyState) {
        panel.innerHTML = '';
    }
    
    const taskHtml = `
        <div class="task-item" id="task-${taskId}">
            <div class="task-item-header">
                <span class="task-item-name">${taskName}</span>
                <span class="task-item-status in-progress" id="status-${taskId}">进行中</span>
            </div>
            <div class="task-progress-container" id="progress-container-${taskId}">
                <div class="task-progress-bar">
                    <div class="task-progress-fill" id="progress-fill-${taskId}" style="width: 0%"></div>
                </div>
                <div class="task-progress-text">
                    <span id="progress-text-${taskId}">0%</span>
                    <span>处理中...</span>
                </div>
            </div>
            <div id="result-${taskId}" style="display: none;"></div>
        </div>
    `;
    panel.insertAdjacentHTML('afterbegin', taskHtml);
}

function updateTaskProgress(taskId, taskName, progress, status, result = '') {
    const panel = document.getElementById('taskPanel');
    let taskElement = document.getElementById(`task-${taskId}`);
    
    if (!taskElement) {
        addTask(taskId, taskName);
        taskElement = document.getElementById(`task-${taskId}`);
    }
    
    const progressFill = document.getElementById(`progress-fill-${taskId}`);
    const progressText = document.getElementById(`progress-text-${taskId}`);
    const statusElement = document.getElementById(`status-${taskId}`);
    const progressContainer = document.getElementById(`progress-container-${taskId}`);
    const resultContainer = document.getElementById(`result-${taskId}`);
    
    if (status === 'completed') {
        progressFill.style.width = '100%';
        progressText.textContent = '100%';
        statusElement.textContent = '已完成';
        statusElement.className = 'task-item-status completed';
        progressContainer.style.display = 'none';
        
        if (result) {
            resultContainer.innerHTML = `<div class="task-result">${escapeHtml(result)}</div>`;
            resultContainer.style.display = 'block';
        } else {
            resultContainer.innerHTML = `<span class="task-completed-badge">已完成</span>`;
            resultContainer.style.display = 'block';
        }
    } else {
        progressFill.style.width = `${progress}%`;
        progressText.textContent = `${progress}%`;
        statusElement.textContent = '进行中';
        statusElement.className = 'task-item-status in-progress';
        progressContainer.style.display = 'block';
        resultContainer.style.display = 'none';
    }
}

function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
}

function loadPrintProducts() {
    fetch(API_BASE + '/api/products')
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                const select = document.getElementById('printProductSelect');
                select.textContent = '';
                const defaultOption = document.createElement('option');
                defaultOption.value = '';
                defaultOption.textContent = '请选择产品';
                select.appendChild(defaultOption);
                data.data.forEach(p => {
                    const option = document.createElement('option');
                    option.value = p.model_number || '';
                    option.textContent = `${p.model_number || ''} - ${p.name || ''}`;
                    select.appendChild(option);
                });
            }
        });
}

function previewLabel() {
}

function printLabel() {
    const model = document.getElementById('printProductSelect').value;
    const qty = document.getElementById('printQuantity').value;
    if (!model) {
        alert('请选择产品');
        return;
    }
    alert('已将 ' + model + ' 标签发送到打印机，打印数量：' + qty);
}

function saveSettings() {
    alert('设置已保存');
}

function loadUserPreferences() {
    fetch(API_BASE + '/api/preferences?user_id=default')
    .then(r => r.json())
    .then(data => {
        if (data.success && data.preferences) {
            applyUserPreferences(data.preferences);
        }
    })
    .catch(err => console.error('加载用户偏好失败:', err));
}

function applyUserPreferences(prefs) {
    if (prefs.theme) {
        document.body.setAttribute('data-theme', prefs.theme);
    }
    if (prefs.fontSize) {
        document.body.style.fontSize = prefs.fontSize + 'px';
    }
}

function saveUserPreference(key, value) {
    fetch(API_BASE + '/api/preferences', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            user_id: 'default',
            key: key,
            value: value
        })
    }).catch(err => console.error('保存偏好失败:', err));
}

function showProgress() {
    const panel = document.getElementById('progressPanel');
    if (panel) {
        panel.style.display = 'block';
        panel.style.opacity = '0';
        panel.style.transform = 'translateY(20px)';
        setTimeout(() => {
            panel.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
            panel.style.opacity = '1';
            panel.style.transform = 'translateY(0)';
        }, 10);
    }
}

function hideProgress() {
    const panel = document.getElementById('progressPanel');
    if (panel) {
        panel.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
        panel.style.opacity = '0';
        panel.style.transform = 'translateY(20px)';
        setTimeout(() => {
            panel.style.display = 'none';
            panel.style.transform = '';
        }, 300);
    }
}

function updateProgress(percent, task) {
    const panel = document.getElementById('progressPanel');
    if (!panel) return;
    
    if (!panel.style.display || panel.style.display === 'none') {
        showProgress();
    }

    const percentEl = document.getElementById('progressPercent');
    const barFill = document.getElementById('progressBarFill');
    const taskEl = document.getElementById('progressTask');

    if (percentEl) percentEl.textContent = percent + '%';
    if (barFill) barFill.style.width = percent + '%';
    if (taskEl && task) taskEl.textContent = task;

    if (percent >= 100) {
        setTimeout(() => {
            hideProgress();
        }, 500);
    }
}
