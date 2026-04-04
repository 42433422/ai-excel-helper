<template>
  <div 
    class="pro-order-float-panel"
    :class="{ 
      'task-acquiring': isTaskAcquiring,
      'work-mode': isWorkMode 
    }"
  >
    <div class="panel-header">
      <h3 class="panel-title">订单信息</h3>
      <button class="close-btn" @click="handleClose">×</button>
    </div>
    
    <div v-if="order" class="panel-body">
      <div class="order-info">
        <div class="info-row">
          <span class="info-label">订单号</span>
          <span class="info-value">{{ order.id }}</span>
        </div>
        <div class="info-row">
          <span class="info-label">客户</span>
          <span class="info-value">{{ order.customer }}</span>
        </div>
        <div class="info-row">
          <span class="info-label">金额</span>
          <span class="info-value price">¥{{ order.amount }}</span>
        </div>
        <div class="info-row">
          <span class="info-label">日期</span>
          <span class="info-value">{{ order.date }}</span>
        </div>
        <div class="info-row">
          <span class="info-label">状态</span>
          <span class="info-value status" :class="order.status">{{ order.statusText }}</span>
        </div>
      </div>
      
      <div class="panel-actions">
        <button class="action-btn download" @click="handleDownload">
          <span class="btn-icon"><i class="fa fa-download" aria-hidden="true"></i></span>
          下载订单
        </button>
        <button class="action-btn view" @click="handleView">
          <span class="btn-icon"><i class="fa fa-eye" aria-hidden="true"></i></span>
          查看详情
        </button>
      </div>
    </div>
    
    <div v-else class="empty-state">
      <div class="empty-icon"><i class="fa fa-cubes" aria-hidden="true"></i></div>
      <div class="empty-text">暂无订单信息</div>
    </div>
  </div>
</template>

<script setup>
const props = defineProps({
  order: {
    type: Object,
    default: null
  },
  isTaskAcquiring: {
    type: Boolean,
    default: false
  },
  isWorkMode: {
    type: Boolean,
    default: true
  }
})

const emit = defineEmits(['download', 'view', 'close'])

function handleDownload() {
  emit('download', props.order?.id)
}

function handleView() {
  emit('view', props.order)
}

function handleClose() {
  emit('close')
}
</script>

<style scoped>
.pro-order-float-panel {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 320px;
  background: rgba(10, 14, 39, 0.95);
  border: 1px solid rgba(255, 0, 0, 0.5);
  border-radius: 12px;
  box-shadow: 0 0 20px rgba(255, 0, 0, 0.3);
  backdrop-filter: blur(10px);
  overflow: hidden;
  transition: all 0.5s cubic-bezier(0.4, 0, 0.2, 1);
  z-index: 100;
}

.pro-order-float-panel.task-acquiring {
  transform: translate(-50%, -50%) translateX(180px);
  animation: proOrderFloatPulse 2s ease-in-out infinite;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  background: rgba(255, 0, 0, 0.1);
  border-bottom: 1px solid rgba(255, 0, 0, 0.3);
}

.panel-title {
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
  transition: color 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.close-btn:hover {
  color: rgba(255, 0, 0, 0.9);
}

.panel-body {
  padding: 16px;
}

.order-info {
  background: rgba(0, 0, 0, 0.2);
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 16px;
}

.info-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  padding-bottom: 12px;
  border-bottom: 1px solid rgba(255, 0, 0, 0.1);
}

.info-row:last-child {
  margin-bottom: 0;
  padding-bottom: 0;
  border-bottom: none;
}

.info-label {
  font-size: 13px;
  color: rgba(255, 0, 0, 0.7);
}

.info-value {
  font-size: 14px;
  color: rgba(255, 255, 255, 0.9);
  font-weight: 500;
}

.info-value.price {
  font-size: 18px;
  font-weight: bold;
  color: rgba(255, 0, 0, 0.9);
}

.info-value.status {
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
}

.info-value.status.pending {
  background: rgba(255, 204, 0, 0.2);
  color: rgba(255, 204, 0, 0.9);
}

.info-value.status.processing {
  background: rgba(0, 191, 255, 0.2);
  color: rgba(0, 191, 255, 0.9);
}

.info-value.status.completed {
  background: rgba(0, 255, 0, 0.2);
  color: rgba(0, 255, 0, 0.9);
}

.panel-actions {
  display: flex;
  gap: 12px;
}

.action-btn {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 12px 16px;
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

.action-btn.view {
  background: transparent;
  color: rgba(255, 0, 0, 0.8);
  border: 1px solid rgba(255, 0, 0, 0.3);
}

.action-btn.view:hover {
  background: rgba(255, 0, 0, 0.1);
  border-color: rgba(255, 0, 0, 0.5);
}

.btn-icon {
  font-size: 16px;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
}

.empty-icon {
  font-size: 48px;
  margin-bottom: 12px;
  opacity: 0.5;
}

.empty-text {
  font-size: 14px;
  color: rgba(255, 255, 255, 0.6);
}

@keyframes proOrderFloatPulse {
  0%, 100% {
    transform: translate(-50%, -50%) translateX(180px) scale(1);
    box-shadow: 0 0 20px rgba(255, 0, 0, 0.3);
  }
  50% {
    transform: translate(-50%, -50%) translateX(180px) scale(1.02);
    box-shadow: 0 0 30px rgba(255, 0, 0, 0.5);
  }
}
</style>
