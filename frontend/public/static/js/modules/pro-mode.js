(function() {
    const PRO_TRANSITION_TEXTS = [
        '加载专业模式核心模块',
        '接入产品数据库',
        '同步原材料库存',
        '载入出货单历史记录',
        '激活客户管理引擎',
        '启用智能标签打印',
        '优化工作流',
        '深度解析业务语义',
        '校准自动化执行系统'
    ];
    const REQUIRED_PRO_TOOLS = [
        { tool_key: 'products', name: '产品管理' },
        { tool_key: 'customers', name: '客户管理' },
        { tool_key: 'materials', name: '原材料' },
        { tool_key: 'orders', name: '出货单' },
        { tool_key: 'shipment_generate', name: '生成发货单' },
        { tool_key: 'shipments', name: '出货订单' },
        { tool_key: 'print', name: '标签打印' },
        { tool_key: 'print_label', name: '打印标签' },
        { tool_key: 'shipment_template', name: '发货单模板' },
        { tool_key: 'excel_decompose', name: 'Excel模板分解' },
        { tool_key: 'upload_file', name: '文件上传' },
        { tool_key: 'system', name: '系统设置' },
        { tool_key: 'database', name: '数据库管理' }
    ];

    let isProMode = false;
    let isProModeTransitioning = false;
    let jarvisInitialized = false;
    let isRecording = false;
    let recognition = null;
    let currentAudio = null;
    let isPlaying = false;
    let voiceQueue = [];
    let speechSynth = window.speechSynthesis;
    let ttsApiUrl = 'http://localhost:8080';
    let digitalRainCtx = null;
    let digitalRainDrops = [];
    let digitalRainCharTypeByColumn = [];
    let digitalRainActive = false;
    let digitalRainAnimationId = null;
    let proModeTools = [];
    let displayProTools = [];
    let ringToolBuckets = [[], []];
    let ringIndexByToken = new Map();
    let runtimeProgressTimer = null;
    let runtimeFinishTimer = null;
    let uploadStatusListenerBound = false;
    let proTaskContext = {
        current_task: '',
        current_tool: '',
        status: 'idle',
        updated_at: null,
        recent_tasks: []
    };
    let proTaskAcquisitionActive = false;
    let isWorkMode = false;
    let workModeIntervalId = null;
    let lastMessageSourceSize = undefined;

    /** 订单流程第二步：商标/商标导出，同流程未结束，不触发球的复位 */
    function isLabelsExportStepMessage(msg) {
        if (!msg || typeof msg !== 'string') return false;
        const t = msg.trim();
        return /商标|商标导出|标签导出|下载标签/.test(t);
    }

    function isProTaskAcquisitionMessage(msg) {
        if (!msg || typeof msg !== 'string') return false;
        const t = msg.trim();
        if (t.length < 5) return false;
        // 商标/商标导出：不进入任务确认球，直接由后端硬规则打开下载面板
        if (/^商标导出?$|^标签导出$|^下载标签$/.test(t) || (t.length <= 6 && /商标|标签导出/.test(t))) return false;
        const hasPrint = /^打印/.test(t) || t.includes('打印');
        const hasShipment = /^发货单|生成发货单|开发货单|发货单生成/.test(t);
        const hasLabel = /标签/.test(t);
        const orderLike = /桶|规格|公斤|kg|白底|面漆|稀释剂|色漆|\d+\s*桶|\d+\s*公斤/i.test(t);
        // 纯订单（如「七彩乐园1桶9803规格28」）也进入任务获取：同时有规格和桶/数量
        const pureOrderLike = orderLike && /规格/.test(t) && (/\d+\s*桶|桶\s*\d+/.test(t) || /\d+\s*公斤|公斤\s*\d+/i.test(t));
        return (hasPrint && orderLike) || (hasShipment && orderLike) || (hasLabel && orderLike) || pureOrderLike;
    }

    function enterProTaskAcquisitionState(orderText) {
        proTaskAcquisitionActive = true;
        const overlay = document.getElementById('proModeOverlay');
        const panel = document.getElementById('proOrderFloatPanel');
        const textEl = document.getElementById('proOrderFloatText');
        const downloadWrap = document.getElementById('proOrderFloatDownload');
        if (overlay) overlay.classList.add('task-acquiring');
        if (panel) panel.setAttribute('aria-hidden', 'false');
        if (textEl) textEl.textContent = orderText || '';
        if (downloadWrap) downloadWrap.setAttribute('data-hidden', 'true');
        if (overlay && overlay.classList.contains('work-mode')) {
            createFallingText('加载中WORKMODE0123456789处理任务', 35);
        }
    }

    function exitProTaskAcquisitionState() {
        if (!proTaskAcquisitionActive) return;
        proTaskAcquisitionActive = false;
        const overlay = document.getElementById('proModeOverlay');
        const panel = document.getElementById('proOrderFloatPanel');
        const textEl = document.getElementById('proOrderFloatText');
        const downloadWrap = document.getElementById('proOrderFloatDownload');
        if (overlay) overlay.classList.remove('task-acquiring');
        if (panel) panel.setAttribute('aria-hidden', 'true');
        if (textEl) textEl.textContent = '';
        if (downloadWrap) downloadWrap.setAttribute('data-hidden', 'true');
    }

    const WORK_MODE_INTERVAL_MS = 10000; // 10 秒

    function startWorkModePolling() {
        if (workModeIntervalId) return;
        const apiBase = (typeof API_BASE !== 'undefined' ? API_BASE : '');
        function tick() {
            fetch(apiBase + '/api/wechat_contacts/message_source_size')
                .then(function(r) { return r.json(); })
                .then(function(data) {
                    if (!data || data.size === undefined) return;
                    var size = data.size;
                    if (lastMessageSourceSize === undefined) {
                        lastMessageSourceSize = size;
                        return;
                    }
                    if (size !== lastMessageSourceSize) {
                        fetch(apiBase + '/api/wechat_contacts/refresh_messages_cache', { method: 'POST' })
                            .then(function(r) { return r.json(); })
                            .then(function(res) {
                                lastMessageSourceSize = size;
                                if (res.success) {
                                    if (typeof jarvisAddMessage === 'function') {
                                        jarvisAddMessage('工作模式：消息库有更新，已复制解密并刷新 ' + (res.contacts_refreshed || 0) + ' 个星标联系人聊天记录。', 'ai');
                                    }
                                    fetchWorkModeFeed();
                                }
                            })
                            .catch(function() { lastMessageSourceSize = size; });
                    }
                })
                .catch(function() {});
        }
        tick();
        workModeIntervalId = setInterval(tick, WORK_MODE_INTERVAL_MS);
    }

    function stopWorkModePolling() {
        if (workModeIntervalId) {
            clearInterval(workModeIntervalId);
            workModeIntervalId = null;
        }
        lastMessageSourceSize = undefined;
    }

    function escapeHtml(s) {
        if (s == null || s === undefined) return '';
        var div = document.createElement('div');
        div.textContent = s;
        return div.innerHTML;
    }

    function fetchWorkModeFeed() {
        var apiBase = (typeof API_BASE !== 'undefined' ? API_BASE : '');
        return fetch(apiBase + '/api/wechat_contacts/work_mode_feed?per_contact=10')
            .then(function(r) { return r.json(); })
            .then(function(data) {
                if (data && data.success && Array.isArray(data.feed)) {
                    renderMonitorList(data.feed);
                }
            })
            .catch(function() {});
    }

    function renderMonitorList(feed) {
        var wrap = document.getElementById('jarvisMonitorListWrap');
        var list = document.getElementById('jarvisMonitorList');
        var floatWrap = document.getElementById('jarvisMonitorFloatWrap');
        if (!wrap || !list) return;
        list.innerHTML = '';
        if (floatWrap) floatWrap.innerHTML = '';
        if (!feed || feed.length === 0) {
            list.innerHTML = '<div class="jarvis-monitor-empty">暂无星标联系人，请先添加监控</div>';
            return;
        }
        var n = feed.length;
        var radius = 420;
        feed.forEach(function(item, i) {
            var name = (item.contact_name || ('ID ' + item.contact_id));
            var messages = item.messages || [];
            var block = document.createElement('div');
            block.className = 'jarvis-monitor-contact';
            var nameEl = document.createElement('div');
            nameEl.className = 'jarvis-monitor-contact-name';
            nameEl.textContent = name;
            block.appendChild(nameEl);
            if (messages.length === 0) {
                var empty = document.createElement('div');
                empty.className = 'jarvis-monitor-empty';
                empty.textContent = '暂无聊天记录';
                block.appendChild(empty);
            } else {
                messages.slice(-5).forEach(function(m) {
                    var isSelf = m.role === 'self';
                    var label = (m.sender_name != null && String(m.sender_name).trim() !== '') ? String(m.sender_name).trim() : (isSelf ? '我' : '对方');
                    var text = (m.text || '').trim().replace(/\n/g, ' ');
                    if (!text) return;
                    var msgEl = document.createElement('div');
                    msgEl.className = 'jarvis-monitor-msg msg-' + (isSelf ? 'self' : 'other');
                    msgEl.innerHTML = '<span class="msg-role">[' + escapeHtml(label) + ']</span> ' + escapeHtml(text.substring(0, 80)) + (text.length > 80 ? '…' : '');
                    block.appendChild(msgEl);
                });
            }
            list.appendChild(block);

            if (floatWrap) {
                var angleDeg = (360 / n) * i - 90;
                var angleRad = (angleDeg * Math.PI) / 180;
                var x = radius * Math.sin(angleRad);
                var y = -radius * Math.cos(angleRad);
                var card = document.createElement('div');
                card.className = 'jarvis-monitor-float-card';
                card.style.setProperty('--float-delay', (i * 0.12) + 's');
                card.style.left = '50%';
                card.style.top = '50%';
                card.style.transform = 'translate(calc(-50% + ' + x + 'px), calc(-50% + ' + y + 'px))';
                var inner = document.createElement('div');
                inner.className = 'jarvis-monitor-float-card-inner';
                var cardName = document.createElement('div');
                cardName.className = 'jarvis-monitor-float-card-name';
                cardName.textContent = name;
                inner.appendChild(cardName);
                var cardMsgs = document.createElement('div');
                cardMsgs.className = 'jarvis-monitor-float-card-msgs';
                if (messages.length === 0) {
                    cardMsgs.textContent = '暂无聊天记录';
                } else {
                    messages.slice(-10).forEach(function(m) {
                        var isSelf = m.role === 'self';
                        var label = (m.sender_name != null && String(m.sender_name).trim() !== '') ? String(m.sender_name).trim() : (isSelf ? '我' : '对方');
                        var text = (m.text || '').trim().replace(/\n/g, ' ');
                        if (!text) return;
                        var p = document.createElement('div');
                        p.className = 'jarvis-monitor-float-card-msg msg-' + (isSelf ? 'self' : 'other');
                        p.innerHTML = '<span class="msg-role">[' + escapeHtml(label) + ']</span> ' + escapeHtml(text.substring(0, 36)) + (text.length > 36 ? '…' : '');
                        cardMsgs.appendChild(p);
                    });
                }
                inner.appendChild(cardMsgs);
                card.appendChild(inner);
                floatWrap.appendChild(card);
            }
        });
    }

    window.setWorkModeFromChat = function(enabled) {
        if (!isProMode) return;
        var ov = document.getElementById('proModeOverlay');
        var monitorWrap = document.getElementById('jarvisMonitorListWrap');
        var floatWrap = document.getElementById('jarvisMonitorFloatWrap');
        if (!ov) return;
        isWorkMode = !!enabled;
        if (isWorkMode) {
            ov.classList.add('work-mode');
            ov.classList.add('work-mode-entering');
            if (monitorWrap) monitorWrap.style.display = 'block';
            if (floatWrap) { floatWrap.style.display = 'block'; floatWrap.setAttribute('aria-hidden', 'false'); }
            if (typeof createFallingText === 'function') {
                createFallingText('工作模式WORKMODE', 28);
            }
            var apiBase = (typeof API_BASE !== 'undefined' ? API_BASE : '');
            fetch(apiBase + '/api/wechat_contacts/refresh_messages_cache', { method: 'POST' })
                .then(function(r) { return r.json(); })
                .then(function(res) {
                    if (res.success && typeof jarvisAddMessage === 'function') {
                        var msg = '工作模式：已从解密库复制并刷新星标聊天';
                        if (res.contacts_refreshed != null) msg += '（' + res.contacts_refreshed + ' 人）';
                        msg += '；每 10 秒检测消息库变化，有变化时自动复制并刷新。';
                        jarvisAddMessage(msg, 'ai');
                    }
                    // 获取星标联系人列表并发送开场白
                    fetch(apiBase + '/api/wechat_contacts?type=all')
                        .then(function(r) { return r.json(); })
                        .then(function(contactsData) {
                            if (contactsData && contactsData.contacts && contactsData.contacts.length > 0) {
                                var introMsg = '您好，我是您的 AI 助理，目前已经开始实时监控，很高兴为您处理发货单相关事宜';
                                var contactList = contactsData.contacts;
                                var sentCount = 0;
                                contactList.forEach(function(contact) {
                                    fetch(apiBase + '/api/wechat_contacts/send_message', {
                                        method: 'POST',
                                        headers: { 'Content-Type': 'application/json' },
                                        body: JSON.stringify({ contact_name: contact.contact_name, message: introMsg })
                                    }).then(function() {
                                        sentCount++;
                                        if (sentCount === contactList.length && typeof jarvisAddMessage === 'function') {
                                            jarvisAddMessage('工作模式：已向 ' + sentCount + ' 位星标联系人发送开场白', 'ai');
                                        }
                                    }).catch(function() {
                                        sentCount++;
                                    });
                                });
                            }
                        }).catch(function() {});
                    fetchWorkModeFeed();
                })
                .catch(function() { fetchWorkModeFeed(); });
            startWorkModePolling();
            window.setTimeout(function() {
                ov.classList.remove('work-mode-entering');
            }, 2000);
        } else {
            ov.classList.remove('work-mode-entering');
            ov.classList.add('work-mode-exiting');
            if (typeof createFallingText === 'function') {
                createFallingText('退出工作模式', 22);
            }
            stopWorkModePolling();
            if (monitorWrap) monitorWrap.style.display = 'none';
            if (floatWrap) { floatWrap.style.display = 'none'; floatWrap.setAttribute('aria-hidden', 'true'); floatWrap.innerHTML = ''; }
            var list = document.getElementById('jarvisMonitorList');
            if (list) list.innerHTML = '';
            window.setTimeout(function() {
                ov.classList.remove('work-mode-exiting');
                ov.classList.remove('work-mode');
            }, 1600);
        }
    };

    window.refreshWorkModeMonitorList = function() {
        if (isWorkMode) fetchWorkModeFeed();
    };

    function showProPanelDownload(filename) {
        console.log('showProPanelDownload 被调用，文件名:', filename);
        const wrap = document.getElementById('proOrderFloatDownload');
        const link = document.getElementById('proOrderFloatDownloadLink');
        const panel = document.getElementById('proOrderFloatPanel');
        const overlay = document.getElementById('proModeOverlay');
        console.log('wrap 元素:', wrap);
        console.log('link 元素:', link);
        console.log('panel 元素:', panel);
        if (!wrap || !link) {
            console.error('未找到下载面板元素');
            return;
        }
        
        // 确保面板可见（如果之前被隐藏了）
        if (panel) {
            panel.setAttribute('aria-hidden', 'false');
            panel.style.opacity = '1';
            panel.style.pointerEvents = 'auto';
        }
        if (overlay) {
            overlay.classList.add('task-acquiring');
        }
        
        const apiBase = (typeof API_BASE !== 'undefined' ? API_BASE : '');
        const url = apiBase + '/outputs/' + encodeURIComponent(filename);
        console.log('下载 URL:', url);
        link.setAttribute('href', url);
        link.setAttribute('download', filename);
        link.onclick = function(e) {
            e.preventDefault();
            fetch(url, { method: 'GET' })
                .then(r => r.ok ? r.blob() : Promise.reject(new Error('下载失败')))
                .then(blob => {
                    const blobUrl = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = blobUrl;
                    a.download = filename;
                    a.style.display = 'none';
                    document.body.appendChild(a);
                    a.click();
                    setTimeout(function() { a.remove(); URL.revokeObjectURL(blobUrl); }, 0);
                })
                .catch(() => { if (typeof jarvisAddMessage === 'function') jarvisAddMessage('下载失败', 'ai'); });
        };
        wrap.removeAttribute('data-hidden');
    }

    function extractPageTexts() {
        const texts = [];
        const centerX = window.innerWidth / 2;
        const centerY = window.innerHeight / 2;
        
        const positions = [
            { left: centerX, top: centerY - 120 },
            { left: centerX - 200, top: centerY - 60 },
            { left: centerX + 200, top: centerY - 60 },
            { left: centerX - 150, top: centerY + 20 },
            { left: centerX + 150, top: centerY + 20 },
            { left: centerX, top: centerY + 80 },
            { left: centerX - 250, top: centerY + 80 },
            { left: centerX + 250, top: centerY + 80 },
            { left: centerX - 100, top: centerY - 150 },
            { left: centerX + 100, top: centerY - 150 }
        ];
        
        positions.forEach(pos => {
            texts.push({
                text: '',
                left: pos.left,
                top: pos.top,
                fontSize: '16px',
                fontFamily: 'Segoe UI',
                color: '#00ffff'
            });
        });
        
        return texts;
    }

    function runTurboTransition(exitCallback) {
        const overlay = document.getElementById('transitionOverlay');
        const texts = extractPageTexts();
        const centerX = window.innerWidth / 2;
        const centerY = window.innerHeight / 2;
        
        overlay.innerHTML = '';
        overlay.style.display = 'block';
        
        if (texts.length === 0) {
            texts.push({text: '智能助手', left: centerX, top: centerY - 50, fontSize: '32px', fontFamily: 'Segoe UI'});
            texts.push({text: '产品管理', left: centerX, top: centerY + 20, fontSize: '24px', fontFamily: 'Segoe UI'});
            texts.push({text: '客户查询', left: centerX, top: centerY + 80, fontSize: '24px', fontFamily: 'Segoe UI'});
        }
        
        texts.forEach((item, i) => {
            const el = document.createElement('div');
            el.className = 'transition-text';
            el.textContent = PRO_TRANSITION_TEXTS[i % PRO_TRANSITION_TEXTS.length];

            el.style.setProperty('--start-left', item.left + 'px');
            el.style.setProperty('--start-top', item.top + 'px');
            el.style.animationDelay = (i * 0.06) + 's';
            overlay.appendChild(el);
        });
        
        void overlay.offsetWidth;
        overlay.classList.add('entering');
        
        setTimeout(() => {
            overlay.classList.remove('entering');
            overlay.style.display = 'none';
        }, 700);
    }

    function runTurboExitTransition(exitCallback) {
        const overlay = document.getElementById('transitionOverlay');
        const texts = extractPageTexts();
        const centerX = window.innerWidth / 2;
        const centerY = window.innerHeight / 2;
        
        overlay.innerHTML = '';
        overlay.style.display = 'block';
        
        if (texts.length === 0) {
            texts.push({text: '智能助手', left: centerX, top: centerY - 50, fontSize: '32px', fontFamily: 'Segoe UI'});
            texts.push({text: '产品管理', left: centerX, top: centerY + 20, fontSize: '24px', fontFamily: 'Segoe UI'});
            texts.push({text: '客户查询', left: centerX, top: centerY + 80, fontSize: '24px', fontFamily: 'Segoe UI'});
        }
        
        texts.forEach((item, i) => {
            const el = document.createElement('div');
            el.className = 'transition-text';
            el.textContent = PRO_TRANSITION_TEXTS[i % PRO_TRANSITION_TEXTS.length];

            el.style.setProperty('--start-left', item.left + 'px');
            el.style.setProperty('--start-top', item.top + 'px');
            el.style.animationDelay = (i * 0.06) + 's';
            overlay.appendChild(el);
        });
        
        void overlay.offsetWidth;
        overlay.classList.add('exiting');
        
        setTimeout(() => {
            overlay.classList.remove('exiting');
            overlay.style.display = 'none';
        }, 700);
    }

    function initDigitalRain() {
        const canvas = document.getElementById('digitalRainCanvas');
        if (!canvas) return;
        
        const ctx = canvas.getContext('2d');
        digitalRainCtx = ctx;
        
        canvas.width = window.innerWidth;
        canvas.height = window.innerHeight;
        
        const fontSize = 16;
        const columns = Math.floor(canvas.width / fontSize);
        digitalRainDrops = [];
        digitalRainCharTypeByColumn = [];
        
        for (let i = 0; i < columns; i++) {
            digitalRainDrops[i] = Math.random() * -150;
            digitalRainCharTypeByColumn[i] = i % 2 === 0 ? '1' : '0';
        }
        
        digitalRainActive = true;
        animateDigitalRain();
    }

    function animateDigitalRain() {
        if (!digitalRainActive || !digitalRainCtx) return;
        
        const canvas = digitalRainCtx.canvas;
        const fontSize = 16;
        const overlay = document.getElementById('proModeOverlay');
        const isWorkModeTaskAcquiring = overlay && overlay.classList.contains('work-mode') && overlay.classList.contains('task-acquiring');
        
        digitalRainCtx.fillStyle = 'rgba(0, 0, 0, 0.1)';
        digitalRainCtx.fillRect(0, 0, canvas.width, canvas.height);
        
        digitalRainCtx.fillStyle = isWorkModeTaskAcquiring ? 'rgba(255, 80, 80, 0.75)' : 'rgba(0, 100, 0, 0.7)';
        digitalRainCtx.font = fontSize + 'px "Courier New", monospace';
        digitalRainCtx.textAlign = 'center';
        
        const columnCount = digitalRainDrops.length;
        for (let i = 0; i < columnCount; i++) {
            const xPos = i * fontSize + fontSize / 2;
            const currentChar = digitalRainCharTypeByColumn[i];
            digitalRainCtx.fillText(currentChar, xPos, digitalRainDrops[i] * fontSize);
            
            if (digitalRainDrops[i] * fontSize > canvas.height && Math.random() > 0.985) {
                digitalRainDrops[i] = 0;
            }
            
            digitalRainDrops[i] += 0.025;
        }
        
        digitalRainAnimationId = requestAnimationFrame(animateDigitalRain);
    }

    function stopDigitalRain() {
        digitalRainActive = false;
        if (digitalRainAnimationId) {
            cancelAnimationFrame(digitalRainAnimationId);
            digitalRainAnimationId = null;
        }
        
        const canvas = document.getElementById('digitalRainCanvas');
        if (canvas && digitalRainCtx) {
            digitalRainCtx.clearRect(0, 0, canvas.width, canvas.height);
        }
    }

    function createFallingText(text, count) {
        const container = document.getElementById('fallingTextContainer');
        if (!container) return;
        
        container.innerHTML = '';
        
        const chars = text.split('');
        const containerWidth = window.innerWidth;
        
        for (let i = 0; i < count; i++) {
            const char = document.createElement('span');
            char.className = 'falling-char';
            char.textContent = chars[Math.floor(Math.random() * chars.length)];
            
            char.style.left = (Math.random() * (containerWidth - 50)) + 'px';
            char.style.top = '-50px';
            char.style.animationDelay = (Math.random() * 0.3) + 's';
            char.style.animationDuration = (0.6 + Math.random() * 0.4) + 's';
            
            container.appendChild(char);
        }
        
        setTimeout(() => {
            container.innerHTML = '';
        }, 1200);
    }

    function runFallingTextEnter() {
        const techChars = 'PRO MODE初始化系统加载中AITONYSTARK0123456789';
        createFallingText(techChars, 30);
    }

    function runFallingTextExit() {
        const container = document.getElementById('fallingTextContainer');
        if (!container) return;
        
        container.innerHTML = '';
        
        const techChars = 'PRO MODE退出系统关闭中AI0123456789';
        const chars = techChars.split('');
        const containerWidth = window.innerWidth;
        
        for (let i = 0; i < 30; i++) {
            const char = document.createElement('span');
            char.className = 'falling-char';
            char.textContent = chars[Math.floor(Math.random() * chars.length)];
            
            char.style.left = (Math.random() * (containerWidth - 50)) + 'px';
            char.style.top = '100vh';
            char.style.animationDelay = (Math.random() * 0.3) + 's';
            char.style.animationDuration = (0.6 + Math.random() * 0.4) + 's';
            
            container.appendChild(char);
        }
        
        setTimeout(() => {
            container.innerHTML = '';
        }, 1500);
    }

    function createEnergyParticles() {
        const container = document.getElementById('energyParticles');
        if (!container) return;
        
        container.innerHTML = '';
        
        const centerX = window.innerWidth / 2;
        const centerY = window.innerHeight / 2;
        const particleCount = 40;
        
        for (let i = 0; i < particleCount; i++) {
            const particle = document.createElement('div');
            particle.className = 'energy-particle';
            
            const angle = (i / particleCount) * Math.PI * 2;
            const distance = 150 + Math.random() * 250;
            const tx = Math.cos(angle) * distance;
            const ty = Math.sin(angle) * distance;
            
            particle.style.left = centerX + 'px';
            particle.style.top = centerY + 'px';
            particle.style.setProperty('--tx', tx + 'px');
            particle.style.setProperty('--ty', ty + 'px');
            particle.style.animationDelay = (Math.random() * 0.3) + 's';
            
            container.appendChild(particle);
        }
        
        setTimeout(() => {
            container.innerHTML = '';
        }, 1500);
    }

    function createExitEnergyParticles() {
        const container = document.getElementById('energyParticles');
        if (!container) return;
        
        container.innerHTML = '';
        
        const centerX = window.innerWidth / 2;
        const centerY = window.innerHeight / 2;
        const particleCount = 40;
        
        for (let i = 0; i < particleCount; i++) {
            const particle = document.createElement('div');
            particle.className = 'energy-particle';
            
            const angle = (i / particleCount) * Math.PI * 2;
            const distance = 150 + Math.random() * 250;
            const tx = Math.cos(angle) * distance;
            const ty = Math.sin(angle) * distance;
            
            particle.style.left = (centerX + tx) + 'px';
            particle.style.top = (centerY + ty) + 'px';
            particle.style.setProperty('--tx', tx + 'px');
            particle.style.setProperty('--ty', ty + 'px');
            particle.style.animationDelay = (i * 0.02) + 's';
            
            container.appendChild(particle);
        }
        
        setTimeout(() => {
            container.innerHTML = '';
        }, 1500);
    }

    const proProductVisualState = {
        companyName: '',
        companyPool: [],
        productPool: []
    };

    function ensureProProductVisualNodes() {
        const overlay = document.getElementById('proModeOverlay');
        if (!overlay) return null;

        let orbitLayer = document.getElementById('proProductOrbitLayer');
        if (!orbitLayer) {
            orbitLayer = document.createElement('div');
            orbitLayer.id = 'proProductOrbitLayer';
            orbitLayer.className = 'pro-product-orbit-layer';
            overlay.appendChild(orbitLayer);
        }

        let infoBadge = document.getElementById('proProductInfoBadge');
        if (!infoBadge) {
            infoBadge = document.createElement('div');
            infoBadge.id = 'proProductInfoBadge';
            infoBadge.className = 'pro-product-info-badge';
            overlay.appendChild(infoBadge);
        }

        return { orbitLayer, infoBadge };
    }

    function clearProProductVisualClasses() {
        document.body.classList.remove(
            'pro-product-stage-choose',
            'pro-product-stage-company',
            'pro-product-stage-product'
        );
    }

    function distributeOrbitTokens(ringEl, items, className, radius, onTokenClick) {
        const list = Array.isArray(items) ? items : [];
        const total = list.length;
        if (total === 0) return;
        list.forEach((text, index) => {
            const clickable = typeof onTokenClick === 'function';
            const token = document.createElement(clickable ? 'button' : 'span');
            if (clickable) token.type = 'button';
            token.className = className;
            const label = document.createElement('span');
            label.className = 'orbit-token-label';
            label.textContent = String(text || '');
            token.appendChild(label);
            token.setAttribute('data-value', String(text || ''));
            const angle = (360 / total) * index;
            token.style.transform = `rotate(${angle}deg) translate(${radius}px) rotate(${-angle}deg)`;
            if (clickable) {
                token.addEventListener('click', (evt) => {
                    evt.preventDefault();
                    evt.stopPropagation();
                    const siblings = ringEl.querySelectorAll(`.${className}`);
                    siblings.forEach((node) => node.classList.remove('selected'));
                    token.classList.add('selected');
                    onTokenClick(String(text || ''));
                });
            }
            ringEl.appendChild(token);
        });
    }

    function renderCompanyRing(orbitLayer, companyNames, selectedCompany) {
        if (!orbitLayer) return;
        const ring = document.createElement('div');
        ring.className = `pro-product-company-ring${selectedCompany ? ' locked' : ''}`;
        ring.classList.add('dir-normal');
        ring.style.setProperty('--ring-duration', '22s');
        orbitLayer.appendChild(ring);

        if (selectedCompany) {
            const selected = document.createElement('span');
            selected.className = 'pro-company-token selected';
            selected.textContent = selectedCompany;
            selected.style.transform = 'rotate(0deg) translate(245px)';
            ring.appendChild(selected);
            return;
        }

        const names = (Array.isArray(companyNames) ? companyNames : []).slice(0, 24);
        distributeOrbitTokens(ring, names, 'pro-company-token', 245, (companyName) => {
            if (window.proFeatureWidget && typeof window.proFeatureWidget.selectProductCompanyByName === 'function') {
                window.proFeatureWidget.selectProductCompanyByName(companyName);
            }
        });
    }

    function renderProductRings(orbitLayer, products) {
        if (!orbitLayer) return;
        const list = Array.isArray(products) ? products : [];
        let offset = 0;
        let ringIndex = 0;
        while (offset < list.length) {
            const capacity = 10 + ringIndex * 2; // 10, 12, 14...
            const chunk = list.slice(offset, offset + capacity);
            if (chunk.length === 0) break;

            const ring = document.createElement('div');
            ring.className = 'pro-product-ring';
            ring.style.setProperty('--ring-size', String(520 + ringIndex * 96));
            ring.style.setProperty('--ring-duration', `${22 + ringIndex * 3}s`);
            ring.style.setProperty('--ring-dir', ringIndex % 2 === 0 ? 'normal' : 'reverse');
            ring.classList.add(ringIndex % 2 === 0 ? 'dir-normal' : 'dir-reverse');
            orbitLayer.appendChild(ring);

            distributeOrbitTokens(ring, chunk, 'pro-product-token', 260 + ringIndex * 48, (productName) => {
                if (window.proFeatureWidget && typeof window.proFeatureWidget.selectProductItemByName === 'function') {
                    window.proFeatureWidget.selectProductItemByName(productName);
                }
            });
            offset += capacity;
            ringIndex += 1;
        }
    }

    function setProProductQueryStage(stage, payload) {
        const next = payload || {};
        const nodes = ensureProProductVisualNodes();
        clearProProductVisualClasses();

        if (!nodes) return;
        const { orbitLayer, infoBadge } = nodes;
        orbitLayer.innerHTML = '';
        infoBadge.classList.remove('show');
        infoBadge.textContent = '';

        if (stage === 'idle') {
            proProductVisualState.companyName = '';
            proProductVisualState.companyPool = [];
            proProductVisualState.productPool = [];
            return;
        }

        if (Array.isArray(next.companies)) {
            proProductVisualState.companyPool = next.companies.slice(0, 40);
        }
        if (Array.isArray(next.products)) {
            proProductVisualState.productPool = next.products.slice(0, 120);
        }
        if (next.company) {
            proProductVisualState.companyName = String(next.company);
        }

        if (stage === 'companies') {
            document.body.classList.add('pro-product-stage-choose');
            renderCompanyRing(orbitLayer, proProductVisualState.companyPool, '');
            return;
        }

        if (stage === 'company_selected') {
            document.body.classList.add('pro-product-stage-company');
            renderProductRings(orbitLayer, proProductVisualState.productPool);
            return;
        }

        if (stage === 'product_selected') {
            document.body.classList.add('pro-product-stage-product');
            renderProductRings(orbitLayer, proProductVisualState.productPool);
            const productId = Number(next.product_id || 0);
            const unitName = String(next.unit_name || proProductVisualState.companyName || '');
            const customerId = Number(next.customer_id || 0);
            const name = String(next.name || '产品');
            const model = String(next.model || '');
            const price = Number(next.price || 0).toFixed(2);
            const esc = (v) => String(v)
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;')
                .replace(/"/g, '&quot;')
                .replace(/'/g, '&#39;');
            infoBadge.innerHTML = `
                <div class="pro-product-editor" data-product-id="${productId}" data-unit-name="${esc(unitName)}" data-customer-id="${customerId}">
                    <div class="pro-product-editor-title">${unitName ? `${esc(unitName)} / 产品编辑` : '产品编辑'}</div>
                    <div class="pro-product-editor-grid">
                        <label>名称</label>
                        <input type="text" class="pro-product-editor-input" data-field="name" value="${esc(name)}">
                        <label>型号</label>
                        <input type="text" class="pro-product-editor-input" data-field="model_number" value="${esc(model)}">
                        <label>单价</label>
                        <input type="number" step="0.01" class="pro-product-editor-input" data-field="price" value="${price}">
                    </div>
                    <button type="button" class="pro-product-editor-save" data-action="save-product">保存产品</button>
                </div>
            `;
            const saveBtn = infoBadge.querySelector('[data-action="save-product"]');
            if (saveBtn) {
                saveBtn.addEventListener('click', async () => {
                    const editor = infoBadge.querySelector('.pro-product-editor');
                    if (!editor) return;
                    const id = Number(editor.getAttribute('data-product-id') || 0);
                    if (!id) return;
                    const uname = String(editor.getAttribute('data-unit-name') || '');
                    const cid = Number(editor.getAttribute('data-customer-id') || 0);
                    const inputName = editor.querySelector('[data-field="name"]');
                    const inputModel = editor.querySelector('[data-field="model_number"]');
                    const inputPrice = editor.querySelector('[data-field="price"]');
                    const basePayload = {
                        name: (inputName?.value || '').trim(),
                        model_number: (inputModel?.value || '').trim(),
                        price: Number(inputPrice?.value || 0)
                    };
                    const payloadPrimary = {
                        ...basePayload,
                        ...(uname ? { unit_name: uname } : {}),
                        ...(cid > 0 ? { customer_id: cid } : {})
                    };
                    saveBtn.disabled = true;
                    const oldText = saveBtn.textContent;
                    saveBtn.textContent = '保存中...';
                    try {
                        const apiBase = (typeof API_BASE !== 'undefined' ? API_BASE : '');
                        let res = await fetch(`${apiBase}/api/products/${id}`, {
                            method: 'PUT',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify(payloadPrimary)
                        });
                        let json;
                        try {
                            json = await res.json();
                        } catch (e) {
                            json = { success: false, message: '响应格式异常' };
                        }
                        if (!json.success) {
                            // 兼容重试：去掉单位参数按主库更新
                            res = await fetch(`${apiBase}/api/products/${id}`, {
                                method: 'PUT',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify(basePayload)
                            });
                            try {
                                json = await res.json();
                            } catch (e) {
                                json = { success: false, message: '响应格式异常' };
                            }
                        }
                        if (!json.success) throw new Error(json.message || '保存失败');
                        saveBtn.textContent = '已保存';
                        setTimeout(() => {
                            saveBtn.textContent = oldText;
                            saveBtn.disabled = false;
                        }, 700);
                    } catch (e) {
                        saveBtn.textContent = `失败: ${e.message || '未知错误'}`;
                        setTimeout(() => {
                            saveBtn.textContent = oldText;
                            saveBtn.disabled = false;
                        }, 1200);
                    }
                });
            }
            infoBadge.classList.add('show');
        }
    }

    function resetAllProTransientState() {
        // 一键回到专业版待机态（不退出专业版）
        setProProductQueryStage('idle', {});
        clearRuntimeVisualState();
        stopDigitalRain();
        stopJarvisVoice();

        window.currentJarvisTask = null;
        const taskPanel = document.getElementById('jarvisTaskPanel');
        if (taskPanel) taskPanel.remove();

        if (window.proFeatureWidget && typeof window.proFeatureWidget.hide === 'function') {
            window.proFeatureWidget.hide();
        }
        if (typeof window.hideProFeature === 'function') {
            window.hideProFeature();
        }

        updateJarvisStatus('READY');
    }

    function bindCoreResetAction() {
        const overlay = document.getElementById('proModeOverlay');
        if (!overlay) return;

        let hotspot = document.getElementById('proCoreResetHotspot');
        if (!hotspot) {
            hotspot = document.createElement('button');
            hotspot.type = 'button';
            hotspot.id = 'proCoreResetHotspot';
            hotspot.className = 'pro-core-reset-hotspot';
            hotspot.title = '点击核心重置专业态；工作模式下点击可一键退出工作模式';
            hotspot.setAttribute('aria-label', '点击核心重置专业态；工作模式下点击可一键退出工作模式');
            overlay.appendChild(hotspot);
            hotspot.addEventListener('click', (evt) => {
                evt.preventDefault();
                evt.stopPropagation();
                if (isWorkMode) {
                    setWorkModeFromChat(false);
                    return;
                }
                resetAllProTransientState();
            });
        }
    }

    function toggleProMode() {
        if (isProModeTransitioning) return;
        
        const overlay = document.getElementById('proModeOverlay');
        const toggle = document.getElementById('proModeToggle');
        
        if (!isProMode) {
            isProModeTransitioning = true;
            isProMode = true;
            document.body.classList.add('pro-mode-active');
            
            overlay.style.display = 'flex';
            void overlay.offsetWidth;
            overlay.classList.add('entering');
            
            createEnergyParticles();
            
            setTimeout(() => {
                runFallingTextEnter();
            }, 100);
            
            checkWechatLoginStatus();
            
            setTimeout(() => {
                requestAnimationFrame(() => {
                    overlay.classList.add('active');
                    overlay.classList.remove('entering');
                    bindCoreResetAction();
                    isProModeTransitioning = false;
                });
            }, 1200);
            
            toggle.classList.add('active');
            initJarvisChat();
        } else {
            isProModeTransitioning = true;
            
            overlay.classList.add('exiting');
            createExitEnergyParticles();
            runFallingTextExit();
            stopDigitalRain();
            
            toggle.classList.remove('active');
            
            setTimeout(() => {
                overlay.classList.remove('active');
            }, 300);
            
            setTimeout(() => {
                overlay.style.display = 'none';
                overlay.classList.remove('exiting');
                overlay.classList.remove('work-mode');
                isProMode = false;
                isWorkMode = false;
                stopWorkModePolling();
                isProModeTransitioning = false;
                document.body.classList.remove('pro-mode-active');
                setProProductQueryStage('idle', {});
                clearRuntimeVisualState();
                hideWechatStatusIndicator();
                stopWechatStatusPolling();
                if (window.proFeatureWidget && typeof window.proFeatureWidget.hide === 'function') {
                    window.proFeatureWidget.hide();
                }
                if (typeof window.hideProFeature === 'function') {
                    window.hideProFeature();
                }
            }, 1500);
        }
    }

    function initJarvisChat() {
        if (jarvisInitialized) return;
        jarvisInitialized = true;
        bindUploadStatusListener();

        loadProModeTools().finally(() => {
            createCodeRings();
            createIconRing();
            clearRuntimeVisualState();
            monitorToolUsage();
        });

        const chatContainer = document.getElementById('jarvisChatMessages');
        if (chatContainer && chatContainer.children.length === 0) {
            jarvisAddMessage('您好，我是修茈。我可以帮您控制整个系统：产品管理、原材料仓库、出货单、客户管理、标签打印等。请告诉我您需要做什么？', 'ai');
        }

        const voiceBtn = document.getElementById('jarvisVoiceBtn');
        if (!voiceBtn) return;

        let pressTimer = null;
        let isInputMode = false;

        voiceBtn.addEventListener('mousedown', function(e) {
            pressTimer = setTimeout(function() {
                startVoiceInput();
            }, 300);
        });
        
        voiceBtn.addEventListener('mouseup', function(e) {
            if (pressTimer) {
                clearTimeout(pressTimer);
                pressTimer = null;
                if (!isRecording) {
                    if (!isInputMode) {
                        toggleInputMode();
                    }
                }
            }
            stopVoiceInput();
        });
        
        voiceBtn.addEventListener('mouseleave', function(e) {
            if (pressTimer) {
                clearTimeout(pressTimer);
                pressTimer = null;
            }
            stopVoiceInput();
        });

        voiceBtn.addEventListener('touchstart', function(e) {
            e.preventDefault();
            pressTimer = setTimeout(function() {
                startVoiceInput();
            }, 300);
        });
        voiceBtn.addEventListener('touchend', function(e) {
            e.preventDefault();
            if (pressTimer) {
                clearTimeout(pressTimer);
                pressTimer = null;
                if (!isRecording) {
                    if (!isInputMode) {
                        toggleInputMode();
                    }
                }
            }
            stopVoiceInput();
        });

        function toggleInputMode() {
            isInputMode = !isInputMode;
            const voiceInput = document.getElementById('voiceInput');
            const voiceBtnContent = document.getElementById('voiceBtnContent');
            
            if (isInputMode) {
                voiceBtn.classList.add('input-mode');
                voiceInput.style.display = 'block';
                setTimeout(function() {
                    voiceInput.focus();
                }, 100);
                updateJarvisStatus('输入模式');
                
                voiceInput.addEventListener('keydown', function(e) {
                    if (e.key === 'Enter') {
                        const message = voiceInput.value.trim();
                        if (message) {
                            jarvisSendMessage(message);
                            voiceInput.value = '';
                            toggleInputMode();
                        }
                    }
                    if (e.key === 'Escape') {
                        toggleInputMode();
                    }
                });
            } else {
                voiceBtn.classList.remove('input-mode');
                voiceInput.style.display = 'none';
                updateJarvisStatus('READY');
            }
        }

        let spacePressTimer = null;

        document.addEventListener('keydown', function(e) {
            if (e.code === 'Space' && !e.repeat && isProMode) {
                e.preventDefault();
                spacePressTimer = setTimeout(function() {
                    startVoiceInput();
                }, 300);
            }
        });

        document.addEventListener('keyup', function(e) {
            if (e.code === 'Space' && isProMode) {
                e.preventDefault();
                if (spacePressTimer) {
                    clearTimeout(spacePressTimer);
                    spacePressTimer = null;
                    if (!isRecording && !isInputMode) {
                        toggleInputMode();
                    }
                }
                stopVoiceInput();
            }
        });

        if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
            const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
            recognition = new SpeechRecognition();
            recognition.continuous = false;
            recognition.interimResults = true;
            recognition.lang = 'zh-CN';

            recognition.onstart = function() {
                isRecording = true;
                voiceBtn.classList.add('recording');
                updateJarvisStatus('正在聆听...');
            };

            recognition.onresult = function(event) {
                let finalTranscript = '';
                let interimTranscript = '';
                for (let i = event.resultIndex; i < event.results.length; i++) {
                    if (event.results[i].isFinal) {
                        finalTranscript += event.results[i][0].transcript;
                    } else {
                        interimTranscript += event.results[i][0].transcript;
                    }
                }
                if (finalTranscript) {
                    jarvisSendMessage(finalTranscript.trim());
                }
                if (typeof setVoiceButtonLoadingText === 'function') {
                    var show = interimTranscript || finalTranscript || '正在聆听...';
                    setVoiceButtonLoadingText(show);
                }
            };

            recognition.onerror = function(event) {
                console.error('Speech recognition error:', event.error);
                stopVoiceInput();
                updateJarvisStatus('ERROR: ' + event.error);
                setTimeout(() => updateJarvisStatus('READY'), 2000);
            };

            recognition.onend = function() {
                stopVoiceInput();
            };
        } else {
            voiceBtn.addEventListener('click', function() {
                const message = prompt('请输入您的指令:');
                if (message && message.trim()) {
                    jarvisSendMessage(message.trim());
                }
            });
            updateJarvisStatus('语音不可用 - 点击输入');
        }
    }

    function setVoiceButtonLoadingText(text) {
        var loadingEl = document.getElementById('voiceLoadingText');
        var voiceBtn = document.getElementById('jarvisVoiceBtn');
        var btnTextEl = voiceBtn && voiceBtn.querySelector ? voiceBtn.querySelector('.btn-text') : null;
        if (!loadingEl) return;
        if (text) {
            loadingEl.textContent = text;
            loadingEl.classList.add('visible');
            if (btnTextEl) btnTextEl.style.display = 'none';
        } else {
            loadingEl.textContent = '';
            loadingEl.classList.remove('visible');
            if (btnTextEl) btnTextEl.style.display = '';
        }
    }

    function startVoiceInput() {
        if (isRecording) return;
        
        if (recognition) {
            isRecording = true;
            const voiceBtn = document.getElementById('jarvisVoiceBtn');
            if (voiceBtn) {
                voiceBtn.classList.add('recording');
                setVoiceButtonLoadingText('正在聆听...');
            }
            updateJarvisStatus('正在聆听...');
            try {
                recognition.start();
            } catch(e) {
                console.error('Recognition start error:', e);
                isRecording = false;
                if (voiceBtn) {
                    voiceBtn.classList.remove('recording');
                    setVoiceButtonLoadingText('');
                }
            }
        }
    }

    function stopVoiceInput() {
        if (!isRecording) return;
        
        const voiceBtn = document.getElementById('jarvisVoiceBtn');
        if (voiceBtn) {
            voiceBtn.classList.remove('recording');
            setVoiceButtonLoadingText('');
        }
        
        if (recognition) {
            try {
                recognition.stop();
            } catch(e) {
                console.error('Recognition stop error:', e);
            }
        }
        isRecording = false;
    }

    function updateJarvisStatus(status) {
        const statusEl = document.getElementById('jarvisStatusText');
        if (statusEl) {
            statusEl.textContent = status;
        }
    }

    function jarvisSendMessage(message) {
        if (!message || !message.trim()) return;

        // 只有非订单流程第二步、且非任务获取类消息时才让球复位；商标导出是同流程第二步，球不回来
        if (!isProTaskAcquisitionMessage(message) && !isLabelsExportStepMessage(message)) {
            exitProTaskAcquisitionState();
        }

        // 用户消息阶段就预触发上传入口，避免等待AI回复导致漏触发
        triggerUploadEntryFromText(message);

        if (isProTaskAcquisitionMessage(message)) {
            enterProTaskAcquisitionState(message);
        } else if (isLabelsExportStepMessage(message)) {
            // 商标导出：同流程第二步，主动进入 task-acquiring 使球左移并保持，不回到中间
            enterProTaskAcquisitionState(message.trim() || '商标导出');
        }

        jarvisAddMessage(message, 'user');
        updateJarvisStatus('处理中...');

        callUnifiedChat({
            message: message,
            source: 'pro',
            output_format: 'markdown',
            runtime_context: buildRuntimeContextSnapshot()
        })
        .then(data => {
            if (data.success) {
                startToolRuntimeFromResponse(message, data);
                if (data.toolCall && data.toolCall.tool_id) {
                    executeProToolCall(data.toolCall, message);
                }
                if (data.task && data.task.type !== 'wechat') {
                    jarvisShowTaskConfirm(data.task);
                } else {
                    var replyText = (data.response != null && data.response !== '') ? data.response : '';
                    if (data.autoAction && data.autoAction.type === 'set_work_mode' && !data.autoAction.enabled) {
                        replyText = replyText || '已退出工作模式，球体已恢复为青色；监控列表与每 10 秒刷新已停止。';
                    }
                    if (replyText) jarvisAddMessage(replyText, 'ai');
                }
                // 同步支持 AI 自动操作（与普通聊天一致）
                if (data.autoAction && window.handleAutoAction) {
                    window.handleAutoAction(data.autoAction);
                } else if (typeof data.response === 'string') {
                    // 兜底：当后端未显式返回 autoAction，但文案要求上传时，自动拉起上传入口
                    triggerUploadEntryFromText(data.response);
                }
            } else {
                jarvisAddMessage('处理失败: ' + (data.message || '未知错误'), 'ai');
            }
            updateJarvisStatus('READY');
        })
        .catch(e => {
            jarvisAddMessage('连接失败: ' + e.message, 'ai');
            updateJarvisStatus('连接错误');
            setTimeout(() => updateJarvisStatus('READY'), 3000);
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

    function executeProToolCall(toolCall, originalMessage) {
        const payload = {
            tool_id: toolCall.tool_id,
            action: toolCall.action || '执行',
            params: { ...(toolCall.params || {}) }
        };

        if (!payload.params.order_text && originalMessage) {
            payload.params.order_text = originalMessage;
        }

        updateTaskContextState({
            current_task: payload.action || '执行工具',
            current_tool: payload.tool_id || '',
            status: 'running'
        });
        updateJarvisStatus('工具执行中...');
        setRuntimePanel(payload.tool_id || '工具', payload.action || '执行工具', 35, 'DISPATCH');
        fetch(API_BASE + '/api/tools/execute', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(payload)
        })
        .then(r => {
            setRuntimePanel(payload.tool_id || '工具', payload.action || '执行工具', 75, 'WAITING_RESULT');
            return r.json();
        })
        .then(execResult => {
            let docName = null;
            console.log('专业版执行结果:', execResult);
            if (execResult.success) {
                let msg = execResult.message || '工具执行成功';
                docName = execResult.doc_name || (execResult.data && execResult.data.doc_name) || (execResult.data && execResult.data.document && execResult.data.document.filename);
                console.log('提取的 docName:', docName);
                if (docName) {
                    msg += `\n生成文件：${docName}`;
                }
                jarvisAddMessage(msg, 'ai');
                finishRuntimeProgress('完成');
                updateTaskContextState({
                    status: 'done',
                    current_task: payload.action || '执行工具',
                    current_tool: payload.tool_id || ''
                });
                if (execResult.data && execResult.data.pro_auto_print) {
                    updateJarvisStatus('正在打印...');
                    fetch(API_BASE + '/api/print-last', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: '{}' })
                        .then(r => r.json())
                        .then(printRes => {
                            if (printRes.success) {
                                jarvisAddMessage('已自动打印发货单。', 'ai');
                            } else {
                                jarvisAddMessage('自动打印失败: ' + (printRes.message || '未知'), 'ai');
                            }
                        })
                        .catch(() => jarvisAddMessage('自动打印请求失败', 'ai'))
                        .finally(() => { updateJarvisStatus('READY'); });
                }
            } else {
                jarvisAddMessage('工具执行失败: ' + (execResult.message || '未知错误'), 'ai');
                finishRuntimeProgress('失败');
                updateTaskContextState({
                    status: 'failed',
                    current_task: payload.action || '执行工具',
                    current_tool: payload.tool_id || ''
                });
            }
            if (docName) {
                showProPanelDownload(docName);
                if (typeof window.showShipmentDownloadEntry === 'function') {
                    window.showShipmentDownloadEntry(docName);
                }
                // 专业版：发货单生成成功且生成了标签时，自动打开商标导出面板便于下载
                if (payload.tool_id === 'shipment_generate' && execResult.data && execResult.data.labels && execResult.data.labels.length > 0) {
                    if (typeof window.handleAutoAction === 'function') {
                        window.handleAutoAction({ type: 'show_labels_export' });
                    }
                }
            }
            updateJarvisStatus('READY');
        })
        .catch(err => {
            jarvisAddMessage('工具执行失败: ' + err.message, 'ai');
            finishRuntimeProgress('异常');
            updateTaskContextState({
                status: 'error',
                current_task: payload.action || '执行工具',
                current_tool: payload.tool_id || ''
            });
            updateJarvisStatus('READY');
        });
    }

    function jarvisShowTaskConfirm(task) {
        let itemsHtml = '';
        if (task.items && task.items.length > 0) {
            const keys = Object.keys(task.items[0]);
            itemsHtml = '<div class="jarvis-task-items"><table>' + 
                '<thead><tr>' + keys.map(k => '<th>' + k + '</th>').join('') + '</tr></thead>' +
                '<tbody>' + task.items.map(item => '<tr>' + keys.map(k => '<td>' + item[k] + '</td>').join('') + '</tr>').join('') +
                '</tbody></table></div>';
        }
        
        const taskHtml = `
            <div class="jarvis-task-card">
                <div class="jarvis-task-title">${task.title}</div>
                <div class="jarvis-task-desc">${task.description}</div>
                ${itemsHtml}
                <div class="jarvis-task-actions">
                    <button class="jarvis-task-btn confirm" onclick="jarvisConfirmTask()">确认执行</button>
                    <button class="jarvis-task-btn cancel" onclick="jarvisCancelTask()">取消</button>
                </div>
            </div>
        `;
        
        const container = document.getElementById('jarvisChatMessages');
        if (container) {
            const taskDiv = document.createElement('div');
            taskDiv.className = 'jarvis-msg ai jarvis-task-msg';
            taskDiv.id = 'jarvisTaskPanel';
            taskDiv.innerHTML = taskHtml;
            container.appendChild(taskDiv);
            container.scrollTop = container.scrollHeight;
        }
        window.currentJarvisTask = task;
        updateJarvisStatus('等待确认...');
        
        initDigitalRain();
    }

    function jarvisConfirmTask() {
        if (!window.currentJarvisTask) return;
        const task = window.currentJarvisTask;
        
        jarvisAddMessage('[已确认执行任务]', 'user');
        updateJarvisStatus('执行中...');
        startToolRuntimeFromTask(task);
        
        callUnifiedChat({
            message: '执行任务',
            task_confirm: true,
            task: task,
            source: 'pro',
            output_format: 'markdown',
            runtime_context: buildRuntimeContextSnapshot()
        })
        .then(data => {
            if (data.success) {
                jarvisAddMessage(data.response || '任务执行完成', 'ai');
                finishRuntimeProgress('任务完成');
            } else {
                jarvisAddMessage('执行失败: ' + (data.message || '未知错误'), 'ai');
                finishRuntimeProgress('执行失败');
            }
            updateJarvisStatus('READY');
            window.currentJarvisTask = null;
            const taskPanel = document.getElementById('jarvisTaskPanel');
            if (taskPanel) taskPanel.remove();
            stopDigitalRain();
        })
        .catch(e => {
            jarvisAddMessage('执行失败: ' + e.message, 'ai');
            updateJarvisStatus('READY');
            window.currentJarvisTask = null;
            stopDigitalRain();
            finishRuntimeProgress('执行异常');
        });
    }

    function jarvisCancelTask() {
        jarvisAddMessage('[已取消任务]', 'user');
        window.currentJarvisTask = null;
        const taskPanel = document.getElementById('jarvisTaskPanel');
        if (taskPanel) taskPanel.remove();
        updateJarvisStatus('READY');
        stopDigitalRain();
        finishRuntimeProgress('已取消');
    }

    function playJarvisVoice(text) {
        if (!text) return;
        
        if (isPlaying) {
            stopJarvisVoice();
        }
        
        voiceQueue = [text];
        playNextInQueue();
    }

    function setCoreSpeaking(isSpeaking) {
        const coreScale = document.querySelector('.core-poly-scale');
        if (coreScale) {
            if (isSpeaking) {
                coreScale.classList.add('speaking');
            } else {
                coreScale.classList.remove('speaking');
            }
        }
    }

    function playNextInQueue() {
        if (isPlaying || voiceQueue.length === 0) return;
        
        const text = voiceQueue.shift();
        isPlaying = true;
        setCoreSpeaking(true);
        
        fetch(ttsApiUrl + '/api/tts', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                text: text,
                speakerId: '__1773315555750',
                lang: 'zh'
            })
        })
        .then(r => {
            if (!r.ok) {
                throw new Error('HTTP error, status = ' + r.status);
            }
            const contentType = r.headers.get('content-type');
            if (!contentType || !contentType.includes('application/json')) {
                throw new Error('Response is not JSON');
            }
            return r.json();
        })
        .then(data => {
            if (data.success && data.data && data.data.audioBase64) {
                const audioBase64 = data.data.audioBase64;
                currentAudio = new Audio(audioBase64);
                currentAudio.onended = function() {
                    isPlaying = false;
                    currentAudio = null;
                    setCoreSpeaking(false);
                    playNextInQueue();
                };
                currentAudio.onerror = function() {
                    isPlaying = false;
                    currentAudio = null;
                    setCoreSpeaking(false);
                    useBrowserTTS(text);
                    playNextInQueue();
                };
                currentAudio.play().catch(e => {
                    console.log('TTS播放失败:', e);
                    setCoreSpeaking(false);
                    useBrowserTTS(text);
                });
            } else {
                setCoreSpeaking(false);
                useBrowserTTS(text);
            }
        })
        .catch(e => {
            console.log('TTS API不可用，使用浏览器语音:', e);
            setCoreSpeaking(false);
            useBrowserTTS(text);
        });
    }

    function useBrowserTTS(text) {
        if ('speechSynthesis' in window) {
            speechSynth.cancel();
            
            const utterance = new SpeechSynthesisUtterance(text);
            utterance.lang = 'zh-CN';
            utterance.rate = 1.0;
            utterance.pitch = 1.0;
            utterance.onstart = function() {
                setCoreSpeaking(true);
            };
            utterance.onend = function() {
                isPlaying = false;
                setCoreSpeaking(false);
                playNextInQueue();
            };
            utterance.onerror = function() {
                isPlaying = false;
                setCoreSpeaking(false);
                playNextInQueue();
            };
            isPlaying = true;
            setCoreSpeaking(true);
            speechSynth.speak(utterance);
        } else {
            isPlaying = false;
            setCoreSpeaking(false);
            playNextInQueue();
        }
    }

    function stopJarvisVoice() {
        if (currentAudio) {
            currentAudio.pause();
            currentAudio = null;
        }
        speechSynth.cancel();
        voiceQueue = [];
        isPlaying = false;
        setCoreSpeaking(false);
    }

    function jarvisAddMessage(content, type) {
        const container = document.getElementById('jarvisChatMessages');
        if (!container) return;

        if (type === 'ai' && content && typeof content === 'string') {
            const contentLower = content.toLowerCase();
            if (contentLower.includes('微信') || contentLower.includes('wechat') || 
                contentLower.includes('登录') || contentLower.includes('扫码')) {
                // 微信登录已移除
            }
            triggerUploadEntryFromText(content);
        }

        const time = new Date().toLocaleTimeString('zh-CN', {hour: '2-digit', minute: '2-digit'});
        const div = document.createElement('div');
        div.className = 'jarvis-msg ' + type;
        div.innerHTML = `<div class="msg-text">${content}</div><div class="msg-time">${time}</div>`;
        container.appendChild(div);
        container.scrollTop = container.scrollHeight;
        
        if (type === 'ai') {
            setTimeout(() => playJarvisVoice(content), 300);
        }
    }

    function triggerUploadEntryFromText(text) {
        if (!text || typeof text !== 'string') return;
        const textLower = text.toLowerCase();
        const fileKeywords = [
            '上传', '上传了', '上传内容', '上传文件', '导入文件', '请上传', '请导入', '请选择文件',
            '上传excel', '导入excel', '上传产品', '导入产品', '上传图片',
            'upload', 'import file', 'please upload'
        ];
        const needUpload = fileKeywords.some(keyword => textLower.includes(keyword.toLowerCase()));
        if (!needUpload) return;

        if (window.handleAutoAction) {
            window.handleAutoAction({ type: 'show_file_upload', purpose: 'general' });
            return;
        }
        if (typeof showFileUploadEntry === 'function') {
            showFileUploadEntry();
            return;
        }
        if (typeof openImportWindow === 'function') {
            openImportWindow('general');
        }
    }

    function bindUploadStatusListener() {
        if (uploadStatusListenerBound) return;
        uploadStatusListenerBound = true;
        window.addEventListener('ai-upload-status', function(evt) {
            if (!isProMode) return;
            const detail = (evt && evt.detail) || {};
            if (detail.state === 'pending') {
                updateJarvisStatus('等待上传...');
            } else if (detail.state === 'processing') {
                const pct = Number(detail.percent || 0);
                updateJarvisStatus(`读取中 ${pct}%`);
            } else if (detail.state === 'completed') {
                updateJarvisStatus('读取完成');
                setTimeout(() => updateJarvisStatus('READY'), 1200);
            } else if (detail.state === 'error') {
                updateJarvisStatus('上传失败');
                setTimeout(() => updateJarvisStatus('READY'), 1500);
            }
        });
    }

    function loadProModeTools() {
        const normalizeTool = (tool) => {
            if (!tool || typeof tool !== 'object') return null;
            const normalized = { ...tool };
            if (!normalized.tool_key && normalized.id) {
                normalized.tool_key = String(normalized.id);
            }
            if (!normalized.name && normalized.tool_key) {
                normalized.name = String(normalized.tool_key);
            }
            return normalized;
        };

        const mergeTools = (dbTools, apiTools) => {
            const merged = [];
            const seen = new Set();
            const pushTool = (tool) => {
                const normalized = normalizeTool(tool);
                if (!normalized) return;
                const key = [
                    normalizeToolToken(normalized.tool_key),
                    normalizeToolToken(normalized.id),
                    normalizeToolToken(normalized.name)
                ].find(Boolean);
                if (!key || seen.has(key)) return;
                seen.add(key);
                merged.push(normalized);
            };
            (dbTools || []).forEach(pushTool);
            (apiTools || []).forEach(pushTool);
            REQUIRED_PRO_TOOLS.forEach(pushTool);
            return merged;
        };

        return Promise.allSettled([
            fetch(API_BASE + '/api/db-tools').then(r => r.json()),
            fetch(API_BASE + '/api/tools').then(r => r.json())
        ])
            .then(results => {
                const dbResp = results[0].status === 'fulfilled' ? results[0].value : null;
                const apiResp = results[1].status === 'fulfilled' ? results[1].value : null;

                const dbTools = (dbResp && dbResp.success && Array.isArray(dbResp.tools)) ? dbResp.tools : [];
                let apiTools = [];
                if (apiResp && apiResp.success) {
                    if (Array.isArray(apiResp.tools)) {
                        apiTools = apiResp.tools;
                    } else if (Array.isArray(apiResp)) {
                        apiTools = apiResp;
                    }
                }

                const merged = mergeTools(dbTools, apiTools);
                if (merged.length > 0) {
                    proModeTools = merged;
                } else {
                    proModeTools = dbTools.length > 0 ? dbTools : apiTools;
                }
            })
            .catch(err => {
                console.error('加载工具失败:', err);
            });
    }

    function createCodeRings() {
        const container = document.getElementById('codeRingContainer');
        if (!container) return;
        
        container.innerHTML = '';
        ringToolBuckets = [[], []];
        ringIndexByToken = new Map();

        displayProTools = (proModeTools && proModeTools.length > 0)
            ? proModeTools
            : [
                { tool_key: 'products', name: '产品管理' },
                { tool_key: 'customers', name: '客户管理' },
                { tool_key: 'orders', name: '出货单' },
                { tool_key: 'materials', name: '原材料' },
                { tool_key: 'print', name: '标签打印' },
                { tool_key: 'system', name: '系统控制' }
            ];
        const toolsCount = displayProTools.length;
        const halfCount = Math.ceil(toolsCount / 2);
        
        const rings = [
            { radius: 200, tiltClass: 'ring-tilt-1', startIndex: 0, endIndex: halfCount },
            { radius: 250, tiltClass: 'ring-tilt-2', startIndex: halfCount, endIndex: toolsCount }
        ];
        
        rings.forEach((ringConfig, ringIndex) => {
            const radius = ringConfig.radius;
            const svgWidth = radius * 2 + 200;
            const svgHeight = radius * 2 + 200;
            const centerX = svgWidth / 2;
            const centerY = svgHeight / 2;
            
            const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
            svg.setAttribute('width', svgWidth);
            svg.setAttribute('height', svgHeight);
            svg.setAttribute('viewBox', `0 0 ${svgWidth} ${svgHeight}`);
            svg.style.cssText = `
                position: absolute;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                overflow: visible;
            `;
            
            const defs = document.createElementNS('http://www.w3.org/2000/svg', 'defs');
            
            const pathId = `toolRingPath${ringIndex}`;
            const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
            path.setAttribute('id', pathId);
            path.setAttribute('d', `M ${centerX}, ${centerY - radius} 
                A ${radius} ${radius} 0 1 1 ${centerX - 0.1} ${centerY - radius}`);
            path.setAttribute('fill', 'none');
            defs.appendChild(path);
            
            svg.appendChild(defs);
            
            let ringToolsText = '';
            for (let i = ringConfig.startIndex; i < ringConfig.endIndex; i++) {
                const tool = displayProTools[i];
                let displayText = '';
                if (tool && tool.tool_key) {
                    // 优先使用工具 key，保留中文/英文/数字，仅去掉空白
                    displayText = String(tool.tool_key).replace(/\s+/g, '').substring(0, 8);
                }
                if (!displayText && tool && tool.name) {
                    // 其次使用工具名称原文（支持中文）
                    displayText = String(tool.name).replace(/\s+/g, '').substring(0, 8);
                }
                if (!displayText) {
                    displayText = 'TOOL' + (i + 1);
                }
                ringToolsText += displayText + '    ';
                const tokens = [
                    normalizeToolToken(tool && tool.tool_key),
                    normalizeToolToken(tool && tool.id),
                    normalizeToolToken(tool && tool.name)
                ].filter(Boolean);
                tokens.forEach(token => {
                    ringToolBuckets[ringIndex].push(token);
                    if (!ringIndexByToken.has(token)) {
                        ringIndexByToken.set(token, ringIndex);
                    }
                });
            }
            
            const textPath = document.createElementNS('http://www.w3.org/2000/svg', 'text');
            textPath.setAttribute('class', 'tool-name-text');
            textPath.setAttribute('font-family', "'Courier New', 'Consolas', monospace");
            textPath.setAttribute('font-size', '14');
            textPath.setAttribute('font-weight', 'bold');
            textPath.setAttribute('fill', 'rgba(0, 255, 255, 0.9)');
            textPath.setAttribute('letter-spacing', '2');
            
            const textPathElement = document.createElementNS('http://www.w3.org/2000/svg', 'textPath');
            textPathElement.setAttributeNS('http://www.w3.org/1999/xlink', 'href', `#${pathId}`);
            textPathElement.setAttribute('startOffset', '0%');
            textPathElement.textContent = ringToolsText + ringToolsText;
            
            textPath.appendChild(textPathElement);
            svg.appendChild(textPath);
            
            const ringWrapper = document.createElement('div');
            ringWrapper.className = `code-ring ${ringConfig.tiltClass}`;
            ringWrapper.dataset.ringIndex = String(ringIndex);
            ringWrapper.style.cssText = `
                width: ${svgWidth}px;
                height: ${svgHeight}px;
            `;
            ringWrapper.appendChild(svg);
            
            container.appendChild(ringWrapper);
        });
    }

    function createIconRing() {
        const container = document.getElementById('iconRingContainer');
        if (!container) return;
        container.innerHTML = '';

        const excelIconSvg = '<svg class="excel-icon-svg" viewBox="0 0 24 24" width="28" height="28"><rect width="24" height="24" rx="3" fill="#217346"/><path stroke="#fff" stroke-width="2.2" stroke-linecap="round" fill="none" d="M7 7l10 10M17 7L7 17"/></svg>';
        const icons = [
            {
                key: 'excel_import',
                title: '上传Excel更新购买单位',
                icon: '📥',
                action: () => {
                    if (typeof openImportWindow === 'function') {
                        openImportWindow('customers_import');
                    }
                    if (typeof jarvisAddMessage === 'function') {
                        jarvisAddMessage('请选择购买单位列表 .xlsx 上传，将校验格式并更新。', 'ai');
                    }
                }
            },
            {
                key: 'excel_export',
                title: '导出购买单位Excel',
                iconHtml: excelIconSvg,
                action: () => {
                    const apiBase = (typeof API_BASE !== 'undefined' ? API_BASE : '');
                    const link = document.createElement('a');
                    link.href = `${apiBase}/api/customers/export.xlsx`;
                    link.download = '购买单位列表.xlsx';
                    link.style.display = 'none';
                    document.body.appendChild(link);
                    link.click();
                    setTimeout(() => link.remove(), 0);
                    if (typeof jarvisAddMessage === 'function') {
                        jarvisAddMessage('已开始导出购买单位列表', 'ai');
                    }
                }
            }
        ];

        icons.forEach((item) => {
            const btn = document.createElement('button');
            btn.type = 'button';
            btn.className = 'icon-ring-btn';
            btn.title = item.title;
            if (item.iconHtml) {
                btn.innerHTML = item.iconHtml;
            } else {
                btn.textContent = item.icon || '';
            }
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                if (typeof item.action === 'function') item.action();
            });
            container.appendChild(btn);
        });
        window.createIconRing = createIconRing;
    }

    function normalizeToolToken(value) {
        return String(value || '').trim().toLowerCase();
    }

    function getToolDisplayName(tool) {
        if (!tool) return '未知工具';
        return tool.name || tool.tool_key || String(tool.id || '未知工具');
    }

    function getAllToolCandidates() {
        return (displayProTools && displayProTools.length > 0) ? displayProTools : proModeTools;
    }

    function findToolByCandidates(candidates) {
        const tools = getAllToolCandidates();
        if (!tools || tools.length === 0 || !candidates || candidates.length === 0) return null;
        const normalizedCandidates = candidates.map(normalizeToolToken).filter(Boolean);
        for (let i = 0; i < tools.length; i++) {
            const tool = tools[i];
            const haystack = [
                normalizeToolToken(tool && tool.tool_key),
                normalizeToolToken(tool && tool.id),
                normalizeToolToken(tool && tool.name)
            ].filter(Boolean);
            for (let j = 0; j < normalizedCandidates.length; j++) {
                const candidate = normalizedCandidates[j];
                if (haystack.includes(candidate)) {
                    return tool;
                }
            }
        }
        return null;
    }

    function dedupeCandidates(candidates) {
        const seen = new Set();
        const result = [];
        (candidates || []).forEach(item => {
            const key = normalizeToolToken(item);
            if (!key || seen.has(key)) return;
            seen.add(key);
            result.push(key);
        });
        return result;
    }

    function mapAutoActionToCandidates(type) {
        const map = {
            show_products: ['products'],
            show_customers: ['customers'],
            show_materials: ['materials'],
            show_orders: ['orders', 'shipments'],
            show_print: ['print', 'print_label'],
            show_contacts: ['wechat'],
            show_login: ['wechat'],
            show_wechat_messages: ['wechat'],
            show_images: ['system'],
            show_videos: ['system'],
            show_file_upload: ['system', 'upload_file'],
            show_template_overview: ['shipment_template', 'excel_decompose']
        };
        return map[type] || [];
    }

    function mapTaskTypeToCandidates(type) {
        const t = normalizeToolToken(type);
        const map = {
            products: ['products'],
            customers: ['customers'],
            materials: ['materials'],
            orders: ['orders', 'shipments'],
            shipments: ['orders', 'shipments'],
            shipment_generate: ['shipment_generate', 'orders', 'shipments'],
            print: ['print', 'print_label'],
            wechat: ['wechat'],
            shipment_template: ['shipment_template'],
            excel_decompose: ['excel_decompose']
        };
        return map[t] || (t ? [t] : []);
    }

    function mapMessageToCandidates(message) {
        const text = String(message || '');
        const lower = text.toLowerCase();
        const candidates = [];
        if (text.includes('产品') || text.includes('商品') || text.includes('型号')) candidates.push('products');
        if (text.includes('客户') || text.includes('单位')) candidates.push('customers');
        if (text.includes('原材料') || text.includes('库存')) candidates.push('materials');
        if (text.includes('出货') || text.includes('订单') || text.includes('发货')) candidates.push('orders', 'shipments');
        if (text.includes('生成发货单') || text.includes('开发货单') || text.includes('发货单生成')) candidates.push('shipment_generate', 'orders', 'shipments');
        if (text.includes('打印') || text.includes('标签')) candidates.push('print', 'print_label');
        if (text.includes('微信') || lower.includes('wechat')) candidates.push('wechat');
        if (text.includes('模板')) candidates.push('shipment_template');
        if (text.includes('excel') || text.includes('分解')) candidates.push('excel_decompose');
        if (text.includes('上传') || text.includes('导入') || lower.includes('upload')) candidates.push('upload_file', 'system');
        return candidates;
    }

    function resolveRingIndex(candidates) {
        const normalizedCandidates = dedupeCandidates(candidates);
        if (normalizedCandidates.length === 0) return null;
        for (let i = 0; i < normalizedCandidates.length; i++) {
            const fromMap = ringIndexByToken.get(normalizedCandidates[i]);
            if (fromMap !== undefined && fromMap !== null) {
                return fromMap;
            }
        }
        for (let i = 0; i < ringToolBuckets.length; i++) {
            const bucket = ringToolBuckets[i] || [];
            const hit = normalizedCandidates.some(candidate => bucket.includes(candidate));
            if (hit) return i;
        }
        // 兜底：语义归类，尽量保证“对应环”可停
        const preferredRing0 = ['products', 'customers', 'materials'];
        const preferredRing1 = ['orders', 'shipments', 'shipment_generate', 'print', 'print_label', 'wechat', 'shipment_template', 'excel_decompose', 'system', 'upload_file'];
        if (normalizedCandidates.some(c => preferredRing0.includes(c))) return 0;
        if (normalizedCandidates.some(c => preferredRing1.includes(c))) return 1;
        return null;
    }

    function freezeRingByCandidates(candidates) {
        const targetRing = resolveRingIndex(candidates);
        const rings = document.querySelectorAll('#codeRingContainer .code-ring');
        if (rings.length === 0) return;
        if (targetRing === null) {
            // 最后兜底：至少给出明显“停环反馈”
            rings.forEach(ring => {
                ring.style.animationPlayState = 'paused';
                const svgText = ring.querySelector('.tool-name-text');
                if (svgText) svgText.style.animationPlayState = 'paused';
            });
            return;
        }
        rings.forEach((ring, index) => {
            const state = (index === targetRing) ? 'paused' : 'running';
            ring.style.animationPlayState = state;
            const svgText = ring.querySelector('.tool-name-text');
            if (svgText) {
                svgText.style.animationPlayState = state;
            }
        });
    }

    function unfreezeRings() {
        const rings = document.querySelectorAll('#codeRingContainer .code-ring');
        rings.forEach(ring => {
            ring.style.animationPlayState = 'running';
            const svgText = ring.querySelector('.tool-name-text');
            if (svgText) {
                svgText.style.animationPlayState = 'running';
            }
        });
    }

    function setRuntimePanel(toolName, taskText, progress, status) {
        const toolChip = document.getElementById('runtimeToolChip');
        const taskEl = document.getElementById('runtimeTaskText');
        const progressBar = document.getElementById('runtimeProgressBar');
        const percentEl = document.getElementById('runtimeProgressPercent');
        const statusEl = document.getElementById('runtimeProgressStatus');
        if (toolChip) toolChip.textContent = toolName || '未知工具';
        if (taskEl) taskEl.textContent = taskText || '正在处理任务...';
        if (progressBar) progressBar.style.width = `${Math.max(0, Math.min(100, progress || 0))}%`;
        if (percentEl) percentEl.textContent = `${Math.round(Math.max(0, Math.min(100, progress || 0)))}%`;
        if (statusEl) statusEl.textContent = status || 'RUNNING';
    }

    function setRuntimePanelVisible(visible) {
        const panel = document.getElementById('toolRuntimePanel');
        if (!panel) return;
        if (visible) {
            panel.classList.add('active');
        } else {
            panel.classList.remove('active');
        }
    }

    function animateToolExtract(toolName) {
        const panel = document.getElementById('toolRuntimePanel');
        const layer = document.getElementById('toolExtractLayer');
        if (!panel || !layer) return;
        const panelRect = panel.getBoundingClientRect();
        const token = document.createElement('div');
        token.className = 'tool-extract-token';
        token.textContent = toolName;
        token.style.left = `${window.innerWidth / 2}px`;
        token.style.top = `${window.innerHeight / 2}px`;
        layer.appendChild(token);

        const targetX = panelRect.left + 70;
        const targetY = panelRect.top + 36;
        const animation = token.animate([
            {
                left: `${window.innerWidth / 2}px`,
                top: `${window.innerHeight / 2}px`,
                opacity: 0.2,
                transform: 'translate(-50%, -50%) scale(0.55)'
            },
            {
                left: `${targetX}px`,
                top: `${targetY}px`,
                opacity: 1,
                transform: 'translate(-50%, -50%) scale(1)'
            }
        ], {
            duration: 680,
            easing: 'cubic-bezier(0.2, 0.8, 0.2, 1)'
        });
        animation.onfinish = () => token.remove();
    }

    function clearRuntimeTimers() {
        if (runtimeProgressTimer) {
            clearInterval(runtimeProgressTimer);
            runtimeProgressTimer = null;
        }
        if (runtimeFinishTimer) {
            clearTimeout(runtimeFinishTimer);
            runtimeFinishTimer = null;
        }
    }

    function beginRuntimeProgress(toolName, taskText, candidates) {
        clearRuntimeTimers();
        setRuntimePanelVisible(true);
        freezeRingByCandidates(candidates);
        animateToolExtract(toolName);
        updateTaskContextState({
            current_task: taskText || '执行任务',
            current_tool: toolName || '',
            status: 'running'
        });
        // 事件驱动：进入执行阶段（不再随机模拟进度）
        setRuntimePanel(toolName, taskText, 20, 'MATCHED');
    }

    function finishRuntimeProgress(statusText) {
        clearRuntimeTimers();
        const toolName = document.getElementById('runtimeToolChip') ? document.getElementById('runtimeToolChip').textContent : '未知工具';
        const taskText = document.getElementById('runtimeTaskText') ? document.getElementById('runtimeTaskText').textContent : '任务已处理';
        setRuntimePanel(toolName, taskText, 100, statusText || 'DONE');
        updateTaskContextState({
            current_task: taskText || '任务已处理',
            current_tool: toolName || '',
            status: (statusText || 'DONE').toLowerCase()
        });
        runtimeFinishTimer = setTimeout(() => {
            unfreezeRings();
            setRuntimePanelVisible(false);
        }, 1200);
    }

    function clearRuntimeVisualState() {
        clearRuntimeTimers();
        unfreezeRings();
        setRuntimePanelVisible(false);
        setRuntimePanel('', '', 0, '');
        updateTaskContextState({
            current_task: '',
            current_tool: '',
            status: 'idle'
        });
        const layer = document.getElementById('toolExtractLayer');
        if (layer) {
            layer.innerHTML = '';
        }
    }

    function updateTaskContextState(nextState) {
        const now = new Date().toISOString();
        proTaskContext = {
            ...proTaskContext,
            ...(nextState || {}),
            updated_at: now
        };
        const hasTask = proTaskContext.current_task || proTaskContext.current_tool;
        if (hasTask) {
            const record = {
                task: proTaskContext.current_task || '',
                tool: proTaskContext.current_tool || '',
                status: proTaskContext.status || 'running',
                at: now
            };
            const recent = Array.isArray(proTaskContext.recent_tasks) ? proTaskContext.recent_tasks : [];
            const last = recent.length > 0 ? recent[recent.length - 1] : null;
            const sameAsLast = last && last.task === record.task && last.tool === record.tool && last.status === record.status;
            if (!sameAsLast) {
                proTaskContext.recent_tasks = [...recent, record].slice(-8);
            }
        }
    }

    function buildRuntimeContextSnapshot() {
        const ctx = {
            current_task: proTaskContext.current_task || '',
            current_tool: proTaskContext.current_tool || '',
            status: proTaskContext.status || 'idle',
            updated_at: proTaskContext.updated_at || null,
            recent_tasks: Array.isArray(proTaskContext.recent_tasks) ? proTaskContext.recent_tasks : []
        };
        if (typeof window.currentWechatContactId !== 'undefined' && window.currentWechatContactId != null) {
            ctx.wechat_contact_id = window.currentWechatContactId;
            if (window.currentWechatContactName) ctx.wechat_contact_name = window.currentWechatContactName;
        }
        return ctx;
    }

    function startToolRuntimeFromResponse(message, data) {
        const candidates = [];
        if (data && data.autoAction && data.autoAction.type) {
            candidates.push(...mapAutoActionToCandidates(data.autoAction.type));
        }
        if (data && data.task) {
            candidates.push(...mapTaskTypeToCandidates(data.task.type));
            candidates.push(data.task.tool_id, data.task.tool_key);
        }
        if (data && data.toolCall) {
            candidates.push(data.toolCall.tool_id);
        }
        candidates.push(...mapMessageToCandidates(message));
        const deduped = dedupeCandidates(candidates);
        if (deduped.length === 0) return;

        const tool = findToolByCandidates(deduped);
        const taskText = (data && data.task && (data.task.description || data.task.title))
            || (data && data.response)
            || message
            || '执行任务';
        const toolName = getToolDisplayName(tool) || deduped[0];
        beginRuntimeProgress(toolName, taskText, deduped);
        if (data && data.toolCall) {
            return;
        }
        // 非工具执行场景：按实际响应立即结束（仅保留短动画展示）
        runtimeFinishTimer = setTimeout(() => {
            finishRuntimeProgress('完成');
        }, 300);
    }

    function startToolRuntimeFromTask(task) {
        if (!task) return;
        const candidates = dedupeCandidates([
            ...(mapTaskTypeToCandidates(task.type)),
            task.tool_id,
            task.tool_key
        ]);
        if (candidates.length === 0) return;
        const tool = findToolByCandidates(candidates);
        const toolName = getToolDisplayName(tool) || candidates[0];
        const taskText = [task.title, task.description].filter(Boolean).join(' - ') || '执行任务';
        beginRuntimeProgress(toolName, taskText, candidates);
    }

    function monitorToolUsage() {
        // 保留入口用于未来扩展，当前已改为在真实响应中驱动工具执行可视化
    }

    window.setProProductQueryStage = setProProductQueryStage;
    window.toggleProMode = toggleProMode;
    window.jarvisAddMessageExternal = jarvisAddMessage;
    window.isProTaskAcquisitionMessage = isProTaskAcquisitionMessage;
    window.jarvisSendMessage = jarvisSendMessage;
})();
