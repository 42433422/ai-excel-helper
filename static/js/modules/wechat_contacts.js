/**
 * 专业版 · 微信联系人列表（内嵌视图，不跳转）
 */
let wechatContactsAll = [];

/** 仅当响应为 JSON 且 OK 时解析，否则抛出明确错误，避免把 HTML 当 JSON 解析 */
function parseJsonResponse(r) {
    var ct = (r.headers.get('Content-Type') || '').toLowerCase();
    if (!r.ok) throw new Error('请求失败: HTTP ' + r.status);
    if (ct.indexOf('application/json') === -1) {
        throw new Error('接口返回了非 JSON（可能是 404），请确认通过正确地址打开控制台并已启动后端服务');
    }
    return r.json();
}

function loadWechatContacts() {
    const container = document.getElementById('wechatContactsListContainer');
    if (!container) return;
    container.innerHTML = '<div class="empty-state">加载中...</div>';
    const typeEl = document.getElementById('wechatContactTypeFilter');
    const typeParam = (typeEl && typeEl.value) ? typeEl.value : 'all';
    const apiBase = typeof API_BASE !== 'undefined' ? API_BASE : '';
    const url = apiBase + '/api/wechat_contacts' + (typeParam !== 'all' ? '?type=' + encodeURIComponent(typeParam) : '');
    // 先确保联系人缓存有基础数据（若为空则自动从解密库复制并导入一遍），再拉取星标列表
    fetch(apiBase + '/api/wechat_contacts/ensure_contact_cache')
        .then(function(r) { if (r.ok) return r.json(); return {}; })
        .catch(function() { return {}; })
        .then(function() {
            return fetch(url).then(parseJsonResponse);
        })
        .then(function(data) {
            if (data.success) {
                wechatContactsAll = data.data || [];
                filterWechatContacts();
            } else {
                container.innerHTML = '<div class="empty-state">加载失败: ' + (data.message || '') + '</div>';
            }
        })
        .catch(function(e) {
            container.innerHTML = '<div class="empty-state">' + (e && e.message ? e.message : '加载失败: 网络错误') + '</div>';
        });
}

function filterWechatContacts() {
    const searchEl = document.getElementById('wechatContactSearch');
    const q = (searchEl && searchEl.value || '').trim().toLowerCase();
    const list = q ? wechatContactsAll.filter(function(c) {
        var name = (c.contact_name || '').toLowerCase();
        var remark = (c.remark || '').toLowerCase();
        var wxid = (c.wechat_id || '').toLowerCase();
        return name.indexOf(q) !== -1 || remark.indexOf(q) !== -1 || wxid.indexOf(q) !== -1;
    }) : wechatContactsAll;
    renderWechatContacts(list);
}

function renderWechatContacts(contacts) {
    const container = document.getElementById('wechatContactsListContainer');
    if (!container) return;
    if (!contacts || contacts.length === 0) {
        container.innerHTML = '<div class="empty-state">' + (wechatContactsAll.length ? '没有匹配的联系人' : '暂无星标联系人，请在上方搜索后星标') + '</div>';
        return;
    }
    const esc = function(s) { return (s || '-').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/"/g, '&quot;'); };
    let html = '<div class="wechat-contact-list-form">';
    contacts.forEach(function(c) {
        var name = esc(c.contact_name);
        var remark = esc(c.remark);
        var wxid = esc(c.wechat_id);
        var cJson = JSON.stringify(c).replace(/"/g, '&quot;');
        var typeLabel = (c.contact_type || 'contact') === 'group' ? '群聊' : '联系人';
        var typeClass = (c.contact_type || 'contact') === 'group' ? 'wechat-type-badge group' : 'wechat-type-badge contact';
        html += '<div class="wechat-contact-form-item">';
        html += '<div class="wechat-contact-fields">';
        html += '<div class="wechat-contact-row"><span class="wechat-contact-label">类型</span><span class="' + typeClass + '">' + esc(typeLabel) + '</span></div>';
        html += '<div class="wechat-contact-row"><span class="wechat-contact-label">微信昵称/备注名</span><span class="wechat-contact-value">' + name + '</span></div>';
        html += '<div class="wechat-contact-row"><span class="wechat-contact-label">备注</span><span class="wechat-contact-value">' + remark + '</span></div>';
        html += '<div class="wechat-contact-row"><span class="wechat-contact-label">微信号</span><span class="wechat-contact-value">' + wxid + '</span></div>';
        html += '</div>';
        html += '<div class="wechat-contact-actions">';
        html += '<button type="button" class="btn btn-primary" data-contact-name="' + esc(c.contact_name) + '" onclick="openWechatChat(this)" title="在微信 PC 中搜索并打开与该联系人的对话框（需微信已打开且与本站同机）">打开对话框</button>';
        html += '<button type="button" class="btn btn-primary" data-contact-name="' + esc(c.contact_name) + '" onclick="sendWechatMessage(this)" title="打开对话框并用剪贴板发送消息（闭环：监控聊天→找联系人→发消息）">发送消息</button>';
        html += '<button type="button" class="btn btn-secondary" data-contact-id="' + c.id + '" data-contact-name="' + esc(c.contact_name) + '" onclick="showWechatContactChat(this)" title="查看已保存的最近聊天记录">查看聊天记录</button>';
        html += '<button type="button" class="btn btn-primary" data-contact-id="' + c.id + '" data-contact-name="' + esc(c.contact_name) + '" onclick="refreshWechatContactMessages(this)" title="从本地解密库拉取最近50条并保存到该联系人上下文，供AI识别意图">刷新聊天记录</button>';
        html += '<button type="button" class="btn btn-secondary" data-contact-id="' + c.id + '" data-contact-name="' + esc(c.contact_name) + '" onclick="setCurrentWechatContact(this)" title="将此人设为当前对话对象，发消息时会带上其聊天上下文">设为对话对象</button>';
        html += '<button type="button" class="btn btn-secondary" onclick="editWechatContact(' + cJson + ')">编辑</button>';
        html += '<button type="button" class="btn btn-secondary" data-contact-id="' + c.id + '" data-contact-name="' + esc(c.contact_name) + '" data-remark="' + esc(c.remark) + '" data-wechat-id="' + esc(c.wechat_id) + '" data-contact-type="' + esc(c.contact_type || 'contact') + '" onclick="unstarWechatContact(this)" title="从列表移除，仍可通过搜索再次星标">取消星标</button>';
        html += '<button type="button" class="btn btn-danger" onclick="deleteWechatContact(' + c.id + ')">删除</button>';
        html += '</div></div>';
    });
    html += '</div>';
    container.innerHTML = html;
}

function saveWechatContactFromForm() {
    const nameEl = document.getElementById('wechatContactName');
    const remarkEl = document.getElementById('wechatContactRemark');
    const wxIdEl = document.getElementById('wechatContactWxId');
    if (!nameEl) return;
    const contactName = nameEl.value.trim();
    const remark = remarkEl && remarkEl.value ? remarkEl.value.trim() : '';
    const wechatId = wxIdEl && wxIdEl.value ? wxIdEl.value.trim() : '';
    if (!contactName) {
        alert('请输入微信昵称/备注名');
        return;
    }
    const typeEl = document.getElementById('wechatContactTypeAdd');
    const contactType = (typeEl && typeEl.value) ? typeEl.value : 'contact';
    const apiBase = typeof API_BASE !== 'undefined' ? API_BASE : '';
    fetch(apiBase + '/api/wechat_contacts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ contact_name: contactName, remark: remark, wechat_id: wechatId, contact_type: contactType })
    })
        .then(parseJsonResponse)
        .then(function(data) {
            if (data.success) {
                nameEl.value = '';
                if (remarkEl) remarkEl.value = '';
                if (wxIdEl) wxIdEl.value = '';
                loadWechatContacts();
            } else {
                alert('添加失败: ' + (data.message || ''));
            }
        })
        .catch(function(e) { alert('添加失败: ' + (e && e.message ? e.message : '网络错误')); });
}

function clearWechatContactForm() {
    const nameEl = document.getElementById('wechatContactName');
    const remarkEl = document.getElementById('wechatContactRemark');
    const wxIdEl = document.getElementById('wechatContactWxId');
    if (nameEl) nameEl.value = '';
    if (remarkEl) remarkEl.value = '';
    if (wxIdEl) wxIdEl.value = '';
}

function editWechatContact(c) {
    const idEl = document.getElementById('wechatContactEditId');
    const nameEl = document.getElementById('wechatContactEditName');
    const remarkEl = document.getElementById('wechatContactEditRemark');
    const wxIdEl = document.getElementById('wechatContactEditWxId');
    const typeEl = document.getElementById('wechatContactEditType');
    const modal = document.getElementById('wechatContactEditModal');
    if (!idEl || !nameEl || !modal) return;
    idEl.value = c.id;
    nameEl.value = c.contact_name || '';
    if (remarkEl) remarkEl.value = c.remark || '';
    if (wxIdEl) wxIdEl.value = c.wechat_id || '';
    if (typeEl) typeEl.value = (c.contact_type || 'contact') === 'group' ? 'group' : 'contact';
    modal.classList.add('active');
}

function saveWechatContactEdit() {
    const idEl = document.getElementById('wechatContactEditId');
    const nameEl = document.getElementById('wechatContactEditName');
    const remarkEl = document.getElementById('wechatContactEditRemark');
    const wxIdEl = document.getElementById('wechatContactEditWxId');
    const modal = document.getElementById('wechatContactEditModal');
    if (!idEl || !nameEl) return;
    const id = idEl.value;
    const contactName = nameEl.value.trim();
    const remark = remarkEl ? remarkEl.value.trim() : '';
    const wechatId = wxIdEl ? wxIdEl.value.trim() : '';
    if (!contactName) {
        alert('请输入微信昵称/备注名');
        return;
    }
    const typeEl = document.getElementById('wechatContactEditType');
    const contactType = (typeEl && typeEl.value) ? typeEl.value : 'contact';
    const apiBase = typeof API_BASE !== 'undefined' ? API_BASE : '';
    fetch(apiBase + '/api/wechat_contacts/' + id, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ contact_name: contactName, remark: remark, wechat_id: wechatId, contact_type: contactType })
    })
        .then(parseJsonResponse)
        .then(function(data) {
            if (data.success) {
                if (modal) modal.classList.remove('active');
                loadWechatContacts();
            } else {
                alert('更新失败: ' + (data.message || ''));
            }
        })
        .catch(function(e) { alert('更新失败: ' + (e && e.message ? e.message : '网络错误')); });
}

function deleteWechatContact(contactId) {
    if (!confirm('确定要删除该微信联系人吗？')) return;
    const apiBase = typeof API_BASE !== 'undefined' ? API_BASE : '';
    fetch(apiBase + '/api/wechat_contacts/' + contactId, { method: 'DELETE' })
        .then(parseJsonResponse)
        .then(function(data) {
            if (data.success) loadWechatContacts();
            else alert('删除失败: ' + (data.message || ''));
        })
        .catch(function(e) { alert('删除失败: ' + (e && e.message ? e.message : '网络错误')); });
}

function showWechatContactChat(btn) {
    const contactId = btn && parseInt(btn.getAttribute('data-contact-id'), 10);
    const contactName = (btn && btn.getAttribute('data-contact-name')) || '';
    if (!contactId) return;
    const apiBase = typeof API_BASE !== 'undefined' ? API_BASE : '';
    const titleEl = document.getElementById('wechatContactChatModalTitle');
    const listEl = document.getElementById('wechatContactChatList');
    const modal = document.getElementById('wechatContactChatModal');
    if (titleEl) titleEl.textContent = '与 ' + (contactName || '该联系人') + ' 的聊天记录';
    if (listEl) listEl.innerHTML = '<div class="empty-state">加载中...</div>';
    if (modal) modal.classList.add('active');
    fetch(apiBase + '/api/wechat_contacts/' + contactId + '/context')
        .then(parseJsonResponse)
        .then(function(data) {
            if (!listEl) return;
            var messages = (data.success && data.messages) ? data.messages : [];
            var esc = function(s) { return (s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/"/g, '&quot;'); };
            if (messages.length === 0) {
                listEl.innerHTML = '<div class="empty-state">暂无聊天记录，请先点击「刷新聊天记录」拉取最近 50 条。</div>';
                return;
            }
            var html = '';
            messages.forEach(function(m) {
                var roleLabel = (m.role === 'self') ? '我' : '对方';
                var timeStr = m.create_time ? new Date(m.create_time * 1000).toLocaleString() : '';
                html += '<div class="wechat-chat-msg" style="margin-bottom:10px;padding:8px 10px;border-radius:8px;' + (m.role === 'self' ? 'background:#e3f2fd;margin-left:24px;' : 'background:#f5f5f5;margin-right:24px;') + '">';
                html += '<div style="font-size:11px;color:#666;margin-bottom:4px;">' + esc(roleLabel) + ' · ' + esc(timeStr) + '</div>';
                html += '<div style="word-break:break-word;white-space:pre-wrap;">' + esc(m.text || '') + '</div>';
                html += '</div>';
            });
            listEl.innerHTML = html;
        })
        .catch(function(e) {
            if (listEl) listEl.innerHTML = '<div class="empty-state">' + (e && e.message ? e.message : '加载失败: 网络错误') + '</div>';
        });
}

function refreshWechatContactMessages(btnOrId) {
    const contactId = typeof btnOrId === 'object' && btnOrId ? parseInt(btnOrId.getAttribute('data-contact-id'), 10) : parseInt(btnOrId, 10);
    if (!contactId) return;
    const apiBase = typeof API_BASE !== 'undefined' ? API_BASE : '';
    const btn = typeof btnOrId === 'object' ? btnOrId : (event && event.target);
    if (btn) { btn.disabled = true; btn.textContent = '刷新中...'; }
    fetch(apiBase + '/api/wechat_contacts/' + contactId + '/refresh_messages', { method: 'POST' })
        .then(parseJsonResponse)
        .then(function(data) {
            if (btn) { btn.disabled = false; btn.textContent = '刷新聊天记录'; }
            if (data.success) {
                alert('已刷新 ' + (data.count || 0) + ' 条聊天记录。' + (data.message || '已保存到该联系人上下文，AI 将据此识别意图。'));
                loadWechatContacts();
            } else {
                alert('刷新失败: ' + (data.message || ''));
            }
        })
        .catch(function(e) {
            if (btn) { btn.disabled = false; btn.textContent = '刷新聊天记录'; }
            alert('刷新失败: ' + (e && e.message ? e.message : '网络错误'));
        });
}

function sendWechatMessage(btn) {
    var contactName = (btn && btn.getAttribute('data-contact-name')) || '';
    if (!contactName) {
        alert('联系人名为空');
        return;
    }
    var msg = prompt('输入要发送的消息（将打开该联系人对话框并发送）：', '');
    if (msg == null || (msg = (msg || '').trim()) === '') return;
    var apiBase = typeof API_BASE !== 'undefined' ? API_BASE : '';
    var oldText = btn.textContent;
    btn.disabled = true;
    btn.textContent = '发送中…';
    fetch(apiBase + '/api/wechat_contacts/send_message', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ contact_name: contactName, message: msg })
    })
        .then(parseJsonResponse)
        .then(function(data) {
            btn.disabled = false;
            btn.textContent = oldText;
            if (data.success) {
                alert(data.message || '已发送');
            } else {
                alert('发送失败: ' + (data.message || ''));
            }
        })
        .catch(function(e) {
            btn.disabled = false;
            btn.textContent = oldText;
            alert('请求失败: ' + (e.message || '网络错误'));
        });
}

function openWechatChat(btn) {
    var contactName = (btn && btn.getAttribute('data-contact-name')) || '';
    if (!contactName) {
        alert('联系人名为空');
        return;
    }
    var apiBase = typeof API_BASE !== 'undefined' ? API_BASE : '';
    var oldText = btn.textContent;
    btn.disabled = true;
    btn.textContent = '正在打开…';
    fetch(apiBase + '/api/wechat_contacts/open_chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ contact_name: contactName })
    })
        .then(parseJsonResponse)
        .then(function(data) {
            btn.disabled = false;
            btn.textContent = oldText;
            if (data.success) {
                alert(data.message || '已打开对话框');
            } else {
                alert('打开失败: ' + (data.message || ''));
            }
        })
        .catch(function(e) {
            btn.disabled = false;
            btn.textContent = oldText;
            alert('请求失败: ' + (e.message || '网络错误'));
        });
}

function setCurrentWechatContact(btnOrId) {
    try {
        var contactId = null;
        var contactName = '';
        if (typeof btnOrId === 'object' && btnOrId) {
            contactId = parseInt(btnOrId.getAttribute('data-contact-id'), 10);
            contactName = btnOrId.getAttribute('data-contact-name') || '';
        } else {
            contactId = parseInt(btnOrId, 10);
        }
        window.currentWechatContactId = contactId;
        window.currentWechatContactName = contactName;
        alert('已设为当前对话对象：' + (contactName || contactId) + '。在「智能对话」中发送消息时，将带上该联系人的最近聊天上下文以帮助 AI 识别意图。');
    } catch (e) {}
}

function refreshWechatContactCache() {
    var btn = document.getElementById('wechatContactRefreshCacheBtn');
    if (btn) { btn.disabled = true; btn.textContent = '刷新中...'; }
    var apiBase = typeof API_BASE !== 'undefined' ? API_BASE : '';
    fetch(apiBase + '/api/wechat_contacts/refresh_contact_cache', { method: 'POST' })
        .then(parseJsonResponse)
        .then(function(data) {
            if (btn) { btn.disabled = false; btn.textContent = '刷新联系人缓存'; }
            if (data.success) {
                alert(data.message || '已刷新联系人缓存');
            } else {
                alert('刷新失败: ' + (data.message || ''));
            }
        })
        .catch(function(e) {
            if (btn) { btn.disabled = false; btn.textContent = '刷新联系人缓存'; }
            alert('刷新失败: ' + (e && e.message ? e.message : '网络错误'));
        });
}

function refreshWechatMessagesCache() {
    var btn = document.getElementById('wechatContactRefreshMessagesCacheBtn');
    if (btn) { btn.disabled = true; btn.textContent = '刷新中...'; }
    var apiBase = typeof API_BASE !== 'undefined' ? API_BASE : '';
    fetch(apiBase + '/api/wechat_contacts/refresh_messages_cache', { method: 'POST' })
        .then(parseJsonResponse)
        .then(function(data) {
            if (btn) { btn.disabled = false; btn.textContent = '刷新聊天记录缓存'; }
            if (data.success) {
                alert(data.message || '已刷新聊天记录缓存');
            } else {
                alert('刷新失败: ' + (data.message || ''));
            }
        })
        .catch(function(e) {
            if (btn) { btn.disabled = false; btn.textContent = '刷新聊天记录缓存'; }
            alert('刷新失败: ' + (e && e.message ? e.message : '网络错误'));
        });
}

function searchWechatContactsForStar() {
    var input = document.getElementById('wechatContactSearchForStar');
    var container = document.getElementById('wechatContactSearchResults');
    if (!input || !container) return;
    var q = (input.value || '').trim();
    if (!q) {
        container.innerHTML = '<p class="muted" style="margin:0;font-size:13px;">请输入关键词后点击搜索</p>';
        return;
    }
    container.innerHTML = '<p class="muted" style="margin:0;">搜索中...</p>';
    var apiBase = typeof API_BASE !== 'undefined' ? API_BASE : '';
    fetch(apiBase + '/api/wechat_contacts/search?q=' + encodeURIComponent(q))
        .then(parseJsonResponse)
        .then(function(data) {
            if (!data.success) {
                container.innerHTML = '<p class="muted" style="margin:0;color:#c00;">' + (data.message || '搜索失败') + '</p>';
                return;
            }
            var results = data.results || [];
            if (results.length === 0) {
                container.innerHTML = '<p class="muted" style="margin:0;">未找到匹配的联系人</p>';
                return;
            }
            var esc = function(s) { return (s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/"/g, '&quot;'); };
            var html = '<div style="display:flex;flex-direction:column;gap:6px;">';
            results.forEach(function(r) {
                var displayName = esc(r.display_name || r.nick_name || r.username || '');
                var username = (r.username || '').replace(/"/g, '&quot;');
                var remark = (r.remark || '').replace(/"/g, '&quot;');
                var isGroup = (r.username || '').indexOf('@chatroom') !== -1;
                var typeLabel = isGroup ? '群聊' : '联系人';
                if (r.already_starred) {
                    html += '<div style="display:flex;align-items:center;justify-content:space-between;padding:6px 10px;background:#f0f0f0;border-radius:6px;"><span>' + displayName + ' <small class="muted">' + typeLabel + '</small></span><span style="color:#666;font-size:12px;">已星标</span></div>';
                } else {
                    html += '<div style="display:flex;align-items:center;justify-content:space-between;padding:6px 10px;background:#f8f9fa;border-radius:6px;"><span>' + displayName + ' <small class="muted">' + typeLabel + '</small></span><button type="button" class="btn btn-primary btn-sm" data-display-name="' + displayName + '" data-username="' + username + '" data-remark="' + remark + '" data-is-group="' + (isGroup ? '1' : '0') + '" onclick="starFromSearch(this)">星标</button></div>';
                }
            });
            html += '</div>';
            container.innerHTML = html;
        })
        .catch(function(e) {
            container.innerHTML = '<p class="muted" style="margin:0;color:#c00;">' + (e && e.message ? e.message : '搜索失败') + '</p>';
        });
}

function starFromSearch(btn) {
    var displayName = (btn.getAttribute('data-display-name') || '').replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&quot;/g, '"');
    var username = (btn.getAttribute('data-username') || '').replace(/&quot;/g, '"');
    var remark = (btn.getAttribute('data-remark') || '').replace(/&quot;/g, '"');
    var isGroup = btn.getAttribute('data-is-group') === '1';
    var contactType = isGroup ? 'group' : 'contact';
    var apiBase = typeof API_BASE !== 'undefined' ? API_BASE : '';
    btn.disabled = true;
    btn.textContent = '添加中...';
    fetch(apiBase + '/api/wechat_contacts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ contact_name: displayName, wechat_id: username, remark: remark, contact_type: contactType })
    })
        .then(function(r) {
            return r.json().then(function(data) {
                if (r.ok && data.success) {
                    return data;
                }
                throw new Error(data.message || 'HTTP ' + r.status);
            });
        })
        .then(function(data) {
            loadWechatContacts();
            searchWechatContactsForStar();
            btn.disabled = false;
            btn.textContent = '星标';
        })
        .catch(function(e) {
            var msg = e && e.message ? e.message : '网络错误';
            var url = (apiBase ? apiBase.replace(/\/$/, '') : '') + '/api/wechat_contacts/star_existing';
            fetch(url, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ contact_name: displayName, wechat_id: username })
            })
                .then(function(r) {
                    if (r.status === 404) throw new Error('NOT_FOUND');
                    return r.json().then(function(d) {
                        if (!r.ok) throw new Error(d.message || '');
                        return d;
                    });
                })
                .then(function(d) {
                    if (d.success) {
                        loadWechatContacts();
                        searchWechatContactsForStar();
                    } else {
                        alert('星标失败: ' + (d.message || ''));
                    }
                })
                .catch(function(err) {
                    if (err && err.message === 'NOT_FOUND') {
                        alert('星标失败: 请完全关闭并重新启动「AI 助手」后端，再刷新本页后重试。');
                    } else {
                        alert('星标失败: ' + (err && err.message ? err.message : msg));
                    }
                });
            btn.disabled = false;
            btn.textContent = '星标';
        });
}

function unstarAllWechatContacts() {
    if (!confirm('确定要解除全部星标吗？解除后星标列表将为空，可随时通过搜索重新星标。')) return;
    var apiBase = typeof API_BASE !== 'undefined' ? API_BASE : '';
    fetch(apiBase + '/api/wechat_contacts/unstar_all', { method: 'POST' })
        .then(parseJsonResponse)
        .then(function(data) {
            if (data.success) {
                alert(data.message || '已解除全部星标');
                loadWechatContacts();
            } else {
                alert('操作失败: ' + (data.message || ''));
            }
        })
        .catch(function(e) {
            alert('操作失败: ' + (e && e.message ? e.message : '网络错误'));
        });
}

function unstarWechatContact(btn) {
    var contactId = btn && parseInt(btn.getAttribute('data-contact-id'), 10);
    if (!contactId) return;
    var contactName = (btn.getAttribute('data-contact-name') || '').replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&quot;/g, '"');
    var remark = (btn.getAttribute('data-remark') || '').replace(/&quot;/g, '"');
    var wechatId = (btn.getAttribute('data-wechat-id') || '').replace(/&quot;/g, '"');
    var contactType = (btn.getAttribute('data-contact-type') || 'contact').replace(/&quot;/g, '"');
    if (!contactName) {
        alert('无法获取联系人名称');
        return;
    }
    var apiBase = typeof API_BASE !== 'undefined' ? API_BASE : '';
    fetch(apiBase + '/api/wechat_contacts/' + contactId, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ contact_name: contactName, remark: remark, wechat_id: wechatId, contact_type: contactType, is_starred: 0 })
    })
        .then(parseJsonResponse)
        .then(function(data) {
            if (data.success) loadWechatContacts();
            else alert('取消星标失败: ' + (data.message || ''));
        })
        .catch(function(e) {
            alert('取消星标失败: ' + (e && e.message ? e.message : '网络错误'));
        });
}
