<template>
  <div class="work-mode-monitor" :class="{ 'work-mode': isWorkMode }">
    <div class="monitor-header">
      <h3 class="monitor-title">工作模式监控</h3>
      <button class="close-btn" @click="handleClose">×</button>
    </div>
    
    <div class="monitor-body">
      <div v-if="isTaskAcquisition" class="task-acquisition-panel">
        <div class="acquisition-header">
          <span class="acquisition-icon">📦</span>
          <span class="acquisition-text">检测到新订单</span>
        </div>
        
        <div v-if="currentOrder" class="order-info">
          <div class="order-detail">
            <span class="detail-label">订单号：</span>
            <span class="detail-value">{{ currentOrder.id }}</span>
          </div>
          <div class="order-detail">
            <span class="detail-label">客户：</span>
            <span class="detail-value">{{ currentOrder.customer }}</span>
          </div>
          <div class="order-detail">
            <span class="detail-label">金额：</span>
            <span class="detail-value">¥{{ currentOrder.amount }}</span>
          </div>
        </div>
        
        <div class="acquisition-actions">
          <button class="action-btn download" @click="handleDownload">
            下载订单
          </button>
          <button class="action-btn reset" @click="handleReset">
            重置
          </button>
        </div>
      </div>
      
      <div class="contacts-list">
        <div class="list-header">
          <span class="list-title">星标联系人</span>
          <span class="contact-count">{{ contacts.length }}</span>
        </div>
        
        <div class="contacts-scroll">
          <div 
            v-for="contact in contacts" 
            :key="contact.id"
            class="contact-item"
            @click="handleContactClick(contact)"
          >
            <div class="contact-avatar">
              {{ contact.name?.charAt(0) || '?' }}
            </div>
            <div class="contact-info">
              <div class="contact-name">{{ contact.name }}</div>
              <div class="contact-last-message">{{ contact.lastMessage }}</div>
            </div>
            <div v-if="contact.unreadCount > 0" class="unread-badge">
              {{ contact.unreadCount }}
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
const props = defineProps({
  contacts: {
    type: Array,
    default: () => []
  },
  isTaskAcquisition: {
    type: Boolean,
    default: false
  },
  currentOrder: {
    type: Object,
    default: null
  },
  isWorkMode: {
    type: Boolean,
    default: true
  }
})

const emit = defineEmits(['contactClick', 'messageSend', 'downloadOrder', 'resetTask'])

function handleClose() {
  emit('resetTask')
}

function handleContactClick(contact) {
  emit('contactClick', contact)
}

function handleDownload() {
  if (props.currentOrder) {
    emit('downloadOrder', props.currentOrder.id)
  }
}

function handleReset() {
  emit('resetTask')
}
</script>

<style scoped>
.work-mode-monitor {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 400px;
  max-height: 500px;
  background: rgba(10, 14, 39, 0.95);
  border: 1px solid rgba(255, 0, 0, 0.5);
  border-radius: 12px;
  box-shadow: 0 0 20px rgba(255, 0, 0, 0.3);
  backdrop-filter: blur(10px);
  overflow: hidden;
  z-index: 100;
}

.monitor-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  background: rgba(255, 0, 0, 0.1);
  border-bottom: 1px solid rgba(255, 0, 0, 0.3);
}

.monitor-title {
  margin: 0;
  font-size: 16px;
  font-weight: bold;
  color: rgba(255, 0, 0, 0.9);
}

.close-btn {
  background: transparent;
  border: none;
  color: rgba(255, 0, 0, 0.7);
  font-size: 24px;
  cursor: pointer;
  padding: 0;
  line-height: 1;
}

.close-btn:hover {
  color: rgba(255, 0, 0, 0.9);
}

.monitor-body {
  padding: 16px;
  max-height: 400px;
  overflow-y: auto;
}

.task-acquisition-panel {
  background: rgba(255, 0, 0, 0.1);
  border: 1px solid rgba(255, 0, 0, 0.3);
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 16px;
}

.acquisition-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}

.acquisition-icon {
  font-size: 24px;
}

.acquisition-text {
  font-size: 16px;
  font-weight: bold;
  color: rgba(255, 0, 0, 0.9);
}

.order-info {
  background: rgba(0, 0, 0, 0.2);
  border-radius: 6px;
  padding: 12px;
  margin-bottom: 12px;
}

.order-detail {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
}

.order-detail:last-child {
  margin-bottom: 0;
}

.detail-label {
  color: rgba(255, 0, 0, 0.7);
  font-size: 14px;
}

.detail-value {
  color: rgba(255, 255, 255, 0.9);
  font-size: 14px;
}

.acquisition-actions {
  display: flex;
  gap: 12px;
}

.action-btn {
  flex: 1;
  padding: 10px 16px;
  border: none;
  border-radius: 6px;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.action-btn.download {
  background: rgba(255, 0, 0, 0.2);
  color: rgba(255, 255, 255, 0.9);
  border: 1px solid rgba(255, 0, 0, 0.4);
}

.action-btn.download:hover {
  background: rgba(255, 0, 0, 0.3);
  transform: scale(1.05);
}

.action-btn.reset {
  background: transparent;
  color: rgba(255, 0, 0, 0.7);
  border: 1px solid rgba(255, 0, 0, 0.3);
}

.action-btn.reset:hover {
  background: rgba(255, 0, 0, 0.1);
}

.contacts-list {
  background: rgba(0, 0, 0, 0.2);
  border-radius: 8px;
  overflow: hidden;
}

.list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: rgba(255, 0, 0, 0.1);
  border-bottom: 1px solid rgba(255, 0, 0, 0.2);
}

.list-title {
  font-size: 14px;
  font-weight: bold;
  color: rgba(255, 0, 0, 0.9);
}

.contact-count {
  font-size: 12px;
  padding: 2px 8px;
  background: rgba(255, 0, 0, 0.2);
  border-radius: 10px;
  color: rgba(255, 255, 255, 0.8);
}

.contacts-scroll {
  max-height: 250px;
  overflow-y: auto;
}

.contact-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  cursor: pointer;
  transition: background 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.contact-item:hover {
  background: rgba(255, 0, 0, 0.1);
}

.contact-avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: rgba(255, 0, 0, 0.2);
  border: 1px solid rgba(255, 0, 0, 0.3);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  font-weight: bold;
  color: rgba(255, 255, 255, 0.9);
}

.contact-info {
  flex: 1;
  min-width: 0;
}

.contact-name {
  font-size: 14px;
  font-weight: bold;
  color: rgba(255, 255, 255, 0.9);
  margin-bottom: 4px;
}

.contact-last-message {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.6);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.unread-badge {
  min-width: 20px;
  height: 20px;
  padding: 0 6px;
  background: rgba(255, 0, 0, 0.5);
  border-radius: 10px;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.9);
  display: flex;
  align-items: center;
  justify-content: center;
}
</style>
