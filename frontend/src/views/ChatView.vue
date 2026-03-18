<template>
  <div class="chat-view page-view active" id="view-chat">
    <div class="quick-actions">
      <button 
        v-for="quickBtn in quickButtons" 
        :key="quickBtn.text"
        class="quick-btn" 
        @click="sendQuick(quickBtn.text)"
      >
        {{ quickBtn.label }}
      </button>
    </div>
    <div class="chat-container">
      <div class="chat-messages" ref="chatMessagesRef">
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
        <div class="panel-content">
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
                <button class="btn btn-success btn-sm" @click="confirmTask">确认执行</button>
                <button class="btn btn-secondary btn-sm" @click="cancelTask">取消</button>
              </div>
            </div>
          </template>
          <div v-else class="empty-state">暂无任务</div>
        </div>
      </div>
    </div>
    <div class="input-area">
      <div class="input-toolbar">
        <button class="toolbar-btn" @click="newConversation" title="新建对话">➕ 新对话</button>
        <button class="toolbar-btn" @click="showHistoryPanel" title="历史记录">📜 历史</button>
      </div>
      <div class="input-wrapper">
        <textarea 
          v-model="messageInput"
          rows="2" 
          placeholder="说「生成发货单」或「当前用的哪个模板」「用户列表」「打印标签」等..."
          @keydown="handleKeyDown"
        ></textarea>
        <button class="btn btn-primary" @click="sendMessage" :disabled="isLoading">发送</button>
      </div>
    </div>

    <div v-if="showHistory" class="history-panel show">
      <div class="history-header">
        <h3>历史对话</h3>
        <button @click="showHistory = false">×</button>
      </div>
      <div class="history-list">
        <div 
          v-for="session in historySessions" 
          :key="session.session_id"
          class="history-item"
          @click="loadSession(session.session_id)"
        >
          <div class="history-title">{{ session.title || '新会话' }}</div>
          <div class="history-meta">{{ Number(session.message_count || 0) }} 条消息</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue';
import chatApi from '../api/chat';

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
const currentTask = ref(null);
const currentSessionId = ref(localStorage.getItem('ai_session_id') || generateSessionId());
const showHistory = ref(false);
const historySessions = ref([]);
const chatMessagesRef = ref(null);

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

const sendMessage = async () => {
  const message = messageInput.value.trim();
  if (!message || isLoading.value) return;

  addMessage(message, 'user');
  saveMessage('user', message);
  messageInput.value = '';
  isLoading.value = true;

  try {
    const data = await chatApi.sendUnifiedChat({ message: message });
    
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

const confirmTask = () => {
  alert('任务已确认执行');
  currentTask.value = null;
};

const cancelTask = () => {
  currentTask.value = null;
};

const newConversation = () => {
  currentSessionId.value = generateSessionId();
  localStorage.setItem('ai_session_id', currentSessionId.value);
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
  console.log('自动操作:', action);
  const event = new CustomEvent('auto-action', { detail: { action, userMessage } });
  window.dispatchEvent(event);
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
  loadConversationHistory();
});
</script>
