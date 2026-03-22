<template>
  <div class="chat-view page-view active" id="view-chat">
    <div class="quick-actions">
      <button 
        v-for="quickBtn in quickButtons" 
        :key="quickBtn.text"
        class="quick-btn" 
        :data-quick="quickBtn.text"
        :data-action="quickBtn.text === '测试预览' ? 'test-preview' : null"
        @click="sendQuick(quickBtn.text)"
      >
        {{ quickBtn.label }}
      </button>
    </div>
    <div class="chat-container">
      <div class="chat-messages" id="chatMessages" ref="chatMessagesRef">
        <div 
          v-for="(msg, idx) in messages" 
          :key="idx"
          :class="['message', msg.role]"
        >
          <div v-html="msg.content"></div>
          <div class="time">{{ msg.time }}</div>
        </div>
        <div v-if="isLoading" class="message ai">
          <div><span class="status-dot online"></span> 处理中...</div>
        </div>
      </div>
      <div class="right-panel">
        <div class="panel-header">{{ currentTask ? '当前任务' : '当前任务' }}</div>
        <div class="panel-content" id="taskPanel">
          <template v-if="currentTask">
            <div class="task-card">
              <div class="task-header">{{ currentTask.title }}</div>
              <div>{{ currentTask.description }}</div>
              <table v-if="currentTask.items && currentTask.items.length > 0" class="data-table" style="margin-top:10px;">
                <thead>
                  <tr>
                    <th v-for="(key, idx) in Object.keys(currentTask.items[0])" :key="idx">
                      {{ key }}
                    </th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(item, iIdx) in currentTask.items" :key="iIdx">
                    <td v-for="(value, vIdx) in Object.values(item)" :key="vIdx">
                      {{ value }}
                    </td>
                  </tr>
                </tbody>
              </table>
              <div class="task-actions">
                <button class="btn btn-success btn-sm" data-action="confirm-task" @click="confirmTask" :disabled="isExecuting">
                  {{ isExecuting ? '执行中...' : '确认执行' }}
                </button>
                <button class="btn btn-secondary btn-sm" data-action="cancel-task" @click="cancelTask" :disabled="isExecuting">取消</button>
              </div>
            </div>
          </template>
          <template v-else-if="proRuntimeTask">
            <div class="task-card">
              <div class="task-header">{{ proRuntimeTask.title }}</div>
              <div style="margin-top:6px;">
                <span :class="['task-item-status', proRuntimeTask.statusClass]">
                  {{ proRuntimeTask.statusText }}
                </span>
              </div>
              <div style="margin-top:10px; color:#6b7280; font-size:13px;">
                {{ proRuntimeTask.description }}
              </div>
            </div>
          </template>
          <div v-else class="empty-state">暂无任务</div>
        </div>
      </div>
    </div>
    <div class="input-area">
      <div class="input-toolbar">
        <button class="toolbar-btn" id="newConversationBtn" title="新建对话" @click="newConversation">➕ 新对话</button>
        <button class="toolbar-btn" id="historyPanelBtn" title="历史记录" @click="showHistoryPanel">📜 历史</button>
      </div>
      <div class="input-wrapper">
        <textarea 
          id="messageInput"
          rows="2" 
          placeholder="说「生成发货单」或「当前用的哪个模板」「用户列表」「打印标签」等..."
          v-model="messageInput"
          @keydown="handleKeyDown"
        ></textarea>
        <button class="btn btn-primary" id="sendMessageBtn" @click="sendMessage">发送</button>
      </div>
    </div>

    <div v-if="showHistory" class="modal show">
      <div class="modal-content">
        <div class="modal-header">
          历史对话
          <span class="close" @click="showHistory = false">×</span>
        </div>
        <div class="modal-body">
          <div v-if="historySessions.length === 0" class="empty-state">暂无历史</div>
          <div
            v-for="session in historySessions"
            :key="session.session_id"
            class="task-card"
            style="margin-bottom:8px; cursor:pointer;"
            @click="loadSession(session.session_id)"
          >
            <div class="task-header">{{ session.title || '新会话' }}</div>
            <div>{{ session.message_count || 0 }} 条消息</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick, onBeforeUnmount } from 'vue';
import { useRouter } from 'vue-router';
import chatApi from '../api/chat';

const router = useRouter();

function generateSessionId() {
  return Date.now().toString(36) + Math.random().toString(36).substr(2);
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

const messages = ref([
  {
    role: 'ai',
    content: '您好！我是您的 AI 智能助手。<div style="margin-top: 8px;">我可以帮您：</div><ul style="margin: 8px 0 0 20px;"><li>查询产品信息和价格</li><li>管理出货单和订单</li><li>查看原材料库存</li><li>打印产品标签</li></ul><div style="margin-top: 8px;">请直接输入您的需求</div>',
    time: new Date().toLocaleTimeString('zh-CN', {hour: '2-digit', minute: '2-digit'})
  }
]);

const messageInput = ref('');
const isLoading = ref(false);
const isExecuting = ref(false);
const currentTask = ref(null);
const proRuntimeTask = ref(null);
const currentSessionId = ref(localStorage.getItem('ai_session_id') || generateSessionId());
const showHistory = ref(false);
const historySessions = ref([]);
const chatMessagesRef = ref(null);
let legacyAutoActionHandler = null;
let proRuntimeClearTimer = null;
let switchViewHandler = null;

const quickButtons = [
  { text: '查一下A001的价格', label: '查产品' },
  { text: '有哪些客户？', label: '客户列表' },
  { text: '今天的出货单', label: '出货单' },
  { text: '库存不足的材料', label: '库存预警' },
  { text: '帮我打印A001标签', label: '打印标签' },
  { text: '测试预览', label: '测试预览' }
];

const scrollToBottom = () => {
  nextTick(() => {
    if (chatMessagesRef.value) {
      chatMessagesRef.value.scrollTop = chatMessagesRef.value.scrollHeight;
    }
  });
};

const addMessage = (content, role) => {
  const time = new Date().toLocaleTimeString('zh-CN', {hour: '2-digit', minute: '2-digit'});
  const safeContent = escapeHtml(content).replace(/\n/g, '<br>');
  messages.value.push({
    role: role,
    content: safeContent,
    time: time
  });
  scrollToBottom();
};

const saveMessage = async (role, content) => {
  try {
    await chatApi.saveMessage({
      session_id: currentSessionId.value,
      user_id: 'default',
      role: role,
      content: content
    });
  } catch (e) {
    console.error('保存消息失败:', e);
  }
};

const requestUnifiedChat = async (message) => {
  return chatApi.sendUnifiedChat({ message });
};

const handlePendingUnitProductsImport = async (userMessage) => {
  try {
    const storageKey = 'xcagiPendingUnitProductsImport';
    let pending = window && window.__xcagiPendingUnitProductsImport;

    // Support cross-refresh: restore pending import from localStorage if window state is lost.
    if (!pending) {
      try {
        const raw = localStorage.getItem(storageKey);
        if (raw) pending = JSON.parse(raw);
        if (pending && window) window.__xcagiPendingUnitProductsImport = pending;
      } catch (_) {}
    }

    // Ensure pending import belongs to current chat session.
    if (pending && pending.session_id && pending.session_id !== currentSessionId.value) {
      try {
        delete window.__xcagiPendingUnitProductsImport;
      } catch (_) {}
      try {
        localStorage.removeItem(storageKey);
      } catch (_) {}
      return false;
    }

    if (!pending || !pending.saved_name || !pending.stage) return false;

    const msgTrim = String(userMessage || '').trim();
    const stage = String(pending.stage || 'confirm_filename');
    const candidates = Array.isArray(pending.unit_candidates) ? pending.unit_candidates : [];

    const clearPending = () => {
      try { delete window.__xcagiPendingUnitProductsImport; } catch (_) {}
      try { localStorage.removeItem(storageKey); } catch (_) {}
    };

    const pushAi = async (text) => {
      addMessage(text, 'ai');
      await saveMessage('ai', text);
    };

    const doImport = async (unitNameToUse) => {
      const unitName = (unitNameToUse || '').trim();
      const body = {
        saved_name: pending.saved_name,
        unit_name: unitName,
        create_purchase_unit: true,
        skip_duplicates: true
      };

      try {
        const res = await fetch('/api/ai/sqlite/import_unit_products', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body)
        });

        const json = await res.json().catch(() => ({}));
        if (res.ok && json && json.success) {
          clearPending();
          const text = json.message || `导入成功：${body.unit_name}`;
          await pushAi(text);
        } else {
          const errMsg = (json && json.message) ? json.message : '导入失败（未知错误）';
          const text = '导入失败：' + errMsg;
          await pushAi(text);
        }
      } catch (e) {
        await pushAi('导入请求失败：' + (e && e.message ? e.message : String(e)));
      }
    };

    // 解析“改成/改为”
    const renameMatch = msgTrim.match(/^(改成|改为)\s*(.+)$/);

    if (stage === 'confirm_filename') {
      const yesMatch = /^(是|确认|确定|导入|开始导入|执行|添加购买单位)/.test(msgTrim);
      const noMatch = /^(否|取消|不导入|不要|别导入|不用|停止)/.test(msgTrim);

      if (renameMatch && renameMatch[2]) {
        await doImport(renameMatch[2]);
        return true;
      }
      if (noMatch) {
        pending.stage = 'choose_candidate';
        if (candidates.length > 0) {
          const list = candidates
            .slice(0, 10)
            .map((u, i) => `${i + 1})${u}`)
            .join('  ');
          await pushAi('好的。我从该库里提取到一些“购买单位”候选：' + list + '。回复序号或直接输入名称即可导入。');
        } else {
          await pushAi('我从该库里没有提取到购买单位候选。请你直接回复“改成 <名称>”。');
        }
        return true;
      }
      if (yesMatch) {
        const guess = (pending.unit_name_guess || '').trim();
        if (guess) {
          await doImport(guess);
        } else {
          // If we can't guess unit_name, fall back to candidate/input flow.
          pending.stage = 'choose_candidate';
          if (candidates.length > 0) {
            const list = candidates
              .slice(0, 10)
              .map((u, i) => `${i + 1})${u}`)
              .join('  ');
            await pushAi('好的。但我没法从文件名猜到购买单位名称。候选如下：' + list + '。回复序号或直接输入名称即可导入。');
          } else {
            await pushAi('我从该库里没有提取到购买单位候选。请你直接回复“改成 <名称>”。');
          }
        }
        return true;
      }

      await pushAi('没太明白。请回复：是 / 否 / 改成 <名称>。');
      return true;
    }

    if (stage === 'choose_candidate') {
      const cancelMatch = /^(取消|不导入|不要|别导入|不用|停止|算了)/.test(msgTrim);
      if (cancelMatch) {
        clearPending();
        const text = '已取消导入。';
        await pushAi(text);
        return true;
      }
      if (renameMatch && renameMatch[2]) {
        await doImport(renameMatch[2]);
        return true;
      }
      const numMatch = msgTrim.match(/^(\d{1,2})$/) || msgTrim.match(/^(\d{1,2})号$/);
      if (numMatch && numMatch[1]) {
        const idx = parseInt(numMatch[1], 10) - 1;
        if (idx >= 0 && idx < candidates.length) {
          await doImport(candidates[idx]);
          return true;
        }
      }
      // 兜底：把用户输入当作名称
      if (msgTrim.length >= 2 && !/^(是|否|确认|确定|导入|取消)/.test(msgTrim)) {
        await doImport(msgTrim);
        return true;
      }
      await pushAi('请回复候选序号（如 1/2/3）或直接输入购买单位名称。');
      return true;
    }

    return false;
  } catch (_) {
    // 不影响正常聊天
    return false;
  }
};

const sendMessage = async () => {
  const domInput = document.getElementById('messageInput');
  const raw = messageInput.value || (domInput && domInput.value) || '';
  const message = raw.trim();
  if (!message || isLoading.value) return;

  addMessage(message, 'user');
  saveMessage('user', message);
  messageInput.value = '';
  isLoading.value = true;

  try {
    // pending import：当文件上传识别到“购买单位产品列表库”后，用户回复是/否/改成... 将触发导入
    const handled = await handlePendingUnitProductsImport(message);
    if (handled) return;

    const data = await requestUnifiedChat(message);
    
    if (data.success) {
      addMessage(data.response, 'ai');
      saveMessage('ai', data.response);
      
      if (data.task) {
        showTaskConfirm(data.task);
      }
      
      if (data.autoAction) {
        handleAutoAction(data.autoAction, message);
      }
    } else {
      addMessage('处理失败: ' + data.message, 'ai');
    }
  } catch (e) {
    addMessage('连接失败: ' + (e.message || '未知错误'), 'ai');
  } finally {
    isLoading.value = false;
  }
};

const sendQuick = (text) => {
  messageInput.value = text;
  sendMessage();
};

const handleKeyDown = (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
};

const showTaskConfirm = (task) => {
  currentTask.value = task;
};

const confirmTask = async () => {
  if (!currentTask.value || isExecuting.value) return;

  const task = currentTask.value;
  const apiUrl = task.api_url;
  const method = (task.method || 'POST').toUpperCase();

  if (!apiUrl) {
    addMessage('任务执行失败：缺少 API 地址', 'ai');
    currentTask.value = null;
    return;
  }

  isExecuting.value = true;

  try {
    let result;
    if (method === 'GET') {
      result = await fetch(apiUrl);
    } else {
      result = await fetch(apiUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(task.payload || {})
      });
    }

    const data = await result.json().catch(() => ({}));

    if (result.ok) {
      const successMsg = data.message || data.msg || '任务执行成功';
      addMessage('✓ ' + successMsg, 'ai');

      if (task.switch_view) {
        handleAutoAction({ type: task.switch_view });
      }
    } else {
      const errMsg = (data && (data.message || data.msg || data.error)) || `执行失败 (HTTP ${result.status})`;
      addMessage('✗ 任务执行失败：' + errMsg, 'ai');
    }
  } catch (e) {
    addMessage('✗ 任务执行失败：' + (e.message || '网络错误'), 'ai');
  } finally {
    isExecuting.value = false;
    currentTask.value = null;
  }
};

const cancelTask = () => {
  currentTask.value = null;
};

function mapProRuntimeStatus(status) {
  const s = String(status || '').toLowerCase();
  if (s === 'running' || s === 'in-progress' || s === 'dispatch' || s === 'matched') {
    return { statusText: '进行中', statusClass: 'in-progress' };
  }
  if (s === 'done' || s === 'completed' || s === 'complete') {
    return { statusText: '已完成', statusClass: 'completed' };
  }
  if (s === 'failed' || s === 'failure') {
    return { statusText: '失败', statusClass: 'completed' };
  }
  if (s === 'error' || s === 'exception') {
    return { statusText: '异常', statusClass: 'completed' };
  }
  if (s === 'idle' || s === '') {
    return { statusText: '', statusClass: '' };
  }
  return { statusText: s || '进行中', statusClass: 'in-progress' };
}

function clearProRuntimeTimer() {
  if (proRuntimeClearTimer) {
    clearTimeout(proRuntimeClearTimer);
    proRuntimeClearTimer = null;
  }
}

let lastProRuntimeUpdatedAt = null;
function setProRuntimeTaskFromEvent(evt) {
  // Do not override confirm-style tasks.
  if (currentTask.value) return;

  const payload = evt && evt.detail ? evt.detail : (evt || {});
  const statusRaw = payload.status;
  const s = String(statusRaw || '').toLowerCase();
  if (s === 'idle' || s === '') {
    clearProRuntimeTimer();
    lastProRuntimeUpdatedAt = null;
    proRuntimeTask.value = null;
    return;
  }

  clearProRuntimeTimer();

  const { statusText, statusClass } = mapProRuntimeStatus(statusRaw);
  const title = (payload.current_task || '').trim() || '工具执行';
  const toolName = (payload.current_tool || '').trim();
  const updatedAt = payload.updated_at || '';
  lastProRuntimeUpdatedAt = updatedAt || lastProRuntimeUpdatedAt;

  const timeText = updatedAt
    ? new Date(updatedAt).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
    : '';

  proRuntimeTask.value = {
    title,
    statusText,
    statusClass,
    description: [
      toolName ? `工具：${toolName}` : '',
      timeText ? `更新时间：${timeText}` : '',
    ].filter(Boolean).join('；'),
  };

  // Clear terminal states after a short delay.
  if (['done', 'completed', 'failed', 'error', 'exception'].includes(s)) {
    proRuntimeClearTimer = window.setTimeout(() => {
      if (currentTask.value) return;
      if (!lastProRuntimeUpdatedAt || lastProRuntimeUpdatedAt === updatedAt) {
        proRuntimeTask.value = null;
      }
      proRuntimeClearTimer = null;
    }, 4500);
  }
}

const newConversation = () => {
  currentSessionId.value = generateSessionId();
  localStorage.setItem('ai_session_id', currentSessionId.value);
  // Cancel any pending multi-step imports tied to the previous session.
  try {
    delete window.__xcagiPendingUnitProductsImport;
    localStorage.removeItem('xcagiPendingUnitProductsImport');
  } catch (_) {}
  messages.value = [{
    role: 'ai',
    content: '您好！我是您的 AI 智能助手。<div style="margin-top: 8px;">我可以帮您：</div><ul style="margin: 8px 0 0 20px;"><li>查询产品信息和价格</li><li>管理出货单和订单</li><li>查看原材料库存</li><li>打印产品标签</li></ul><div style="margin-top: 8px;">请直接输入您的需求</div>',
    time: new Date().toLocaleTimeString('zh-CN', {hour: '2-digit', minute: '2-digit'})
  }];
};

const showHistoryPanel = async () => {
  try {
    const data = await chatApi.getConversations({ limit: 20 });
    if (data.success && data.sessions) {
      historySessions.value = data.sessions;
      showHistory.value = true;
    }
  } catch (e) {
    console.error('加载历史失败:', e);
  }
};

const loadSession = async (sessionId) => {
  currentSessionId.value = sessionId;
  localStorage.setItem('ai_session_id', sessionId);
  showHistory.value = false;
  
  try {
    const data = await chatApi.getConversation(sessionId);
    if (data.success && data.messages && data.messages.length > 0) {
      messages.value = data.messages.map(msg => ({
        role: msg.role,
        content: escapeHtml(msg.content).replace(/\n/g, '<br>'),
        time: new Date().toLocaleTimeString('zh-CN', {hour: '2-digit', minute: '2-digit'})
      }));
    }
  } catch (e) {
    console.error('加载会话失败:', e);
  }
};

const handleAutoAction = (action, userMessage = '') => {
  console.log('[AutoAction] 触发:', action, '| 用户消息:', userMessage);
  const type = action?.type || '';
  const viewMap = {
    'show_chat': 'chat',
    'show_products': 'products',
    'show_materials': 'materials',
    'show_orders': 'orders',
    'show_print': 'print',
    'show_customers': 'customers',
    'show_labels_export': 'print'
  };
  console.log('[AutoAction] 视图映射 type:', type, '-> 目标视图:', viewMap[type] || '未匹配');
  if (viewMap[type]) {
    console.log('[AutoAction] 派发 xcagi:switch-view 事件, detail:', { view: viewMap[type] });
    window.dispatchEvent(new CustomEvent('xcagi:switch-view', { detail: { view: viewMap[type] } }));
  }
  const event = new CustomEvent('auto-action', { detail: { action, userMessage } });
  window.dispatchEvent(event);
  if (typeof legacyAutoActionHandler === 'function') {
    legacyAutoActionHandler(action, userMessage);
  }
};

const loadConversationHistory = async () => {
  try {
    const data = await chatApi.getConversation(currentSessionId.value);
    if (data.success && data.messages && data.messages.length > 0) {
      messages.value = data.messages.map(msg => ({
        role: msg.role,
        content: escapeHtml(msg.content).replace(/\n/g, '<br>'),
        time: new Date().toLocaleTimeString('zh-CN', {hour: '2-digit', minute: '2-digit'})
      }));
    }
  } catch (e) {
    console.error('加载历史记录失败:', e);
  }
};

onMounted(() => {
  legacyAutoActionHandler = typeof window.handleAutoAction === 'function' ? window.handleAutoAction : null;
  window.__VUE_CHAT_SEND__ = async (message) => {
    const text = String(message || '').trim();
    if (!text) return false;
    messageInput.value = text;
    await sendMessage();
    return true;
  };
  window.__VUE_HANDLE_AUTO_ACTION__ = true;
  window.handleAutoAction = handleAutoAction;
  loadConversationHistory();
  window.addEventListener('xcagi:pro-task-status', setProRuntimeTaskFromEvent);

  switchViewHandler = (evt) => {
    const targetView = evt?.detail?.view;
    console.log('[xcagi:switch-view] 收到切换视图事件, targetView:', targetView);
    if (targetView && typeof targetView === 'string') {
      router.push({ name: targetView });
    }
  };
  window.addEventListener('xcagi:switch-view', switchViewHandler);
});

onBeforeUnmount(() => {
  if (window.__VUE_CHAT_SEND__) {
    delete window.__VUE_CHAT_SEND__;
  }
  window.__VUE_HANDLE_AUTO_ACTION__ = false;
  if (legacyAutoActionHandler) {
    window.handleAutoAction = legacyAutoActionHandler;
  }
  window.removeEventListener('xcagi:pro-task-status', setProRuntimeTaskFromEvent);
  window.removeEventListener('xcagi:switch-view', switchViewHandler);
  clearProRuntimeTimer();
});
</script>
