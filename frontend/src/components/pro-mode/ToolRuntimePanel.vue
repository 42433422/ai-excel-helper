<template>
  <div 
    class="tool-runtime-panel"
    :class="{ 'work-mode': isWorkMode }"
  >
    <div class="panel-header">
      <h3 class="panel-title">{{ tool?.name || '工具运行中' }}</h3>
      <span class="panel-status" :class="status.toLowerCase()">{{ statusText }}</span>
    </div>
    
    <div class="panel-body">
      <div v-if="status === 'RUNNING'" class="progress-container">
        <div class="progress-bar">
          <div 
            class="progress-fill"
            :style="{ width: progress + '%' }"
          ></div>
        </div>
        <div class="progress-text">{{ progress }}%</div>
      </div>
      
      <div v-if="status === 'MATCHED'" class="matched-info">
        <div class="matched-icon"><i class="fa fa-check" aria-hidden="true"></i></div>
        <div class="matched-text">工具已匹配</div>
      </div>
      
      <div v-if="status === 'WAITING'" class="waiting-info">
        <div class="waiting-spinner"></div>
        <div class="waiting-text">等待执行...</div>
      </div>
      
      <div v-if="status === 'DONE'" class="done-info">
        <div class="done-icon"><i class="fa fa-check" aria-hidden="true"></i></div>
        <div class="done-text">执行完成</div>
      </div>
    </div>
    
    <div class="panel-footer">
      <button 
        v-if="status === 'RUNNING'"
        class="cancel-button"
        @click="handleCancel"
      >
        取消
      </button>
      <button 
        v-if="status === 'DONE'"
        class="close-button"
        @click="handleClose"
      >
        关闭
      </button>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  tool: {
    type: Object,
    default: null
  },
  progress: {
    type: Number,
    default: 0
  },
  status: {
    type: String,
    default: 'idle'
  },
  isWorkMode: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['cancel', 'close'])

const statusText = computed(() => {
  switch (props.status) {
    case 'RUNNING':
      return '运行中'
    case 'MATCHED':
      return '已匹配'
    case 'WAITING':
      return '等待中'
    case 'DONE':
      return '已完成'
    default:
      return '空闲'
  }
})

function handleCancel() {
  emit('cancel')
}

function handleClose() {
  emit('close')
}
</script>

<style scoped>
.tool-runtime-panel {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 300px;
  background: rgba(10, 14, 39, 0.95);
  border: 1px solid rgba(0, 255, 255, 0.5);
  border-radius: 12px;
  box-shadow: 0 0 20px rgba(0, 255, 255, 0.3);
  backdrop-filter: blur(10px);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  z-index: 100;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  border-bottom: 1px solid rgba(0, 255, 255, 0.2);
}

.panel-title {
  margin: 0;
  font-size: 16px;
  font-weight: bold;
  color: rgba(0, 255, 255, 0.9);
}

.panel-status {
  font-size: 12px;
  padding: 4px 8px;
  border-radius: 4px;
  background: rgba(0, 255, 255, 0.1);
  color: rgba(0, 255, 255, 0.8);
}

.panel-status.running {
  background: rgba(0, 255, 0, 0.1);
  color: rgba(0, 255, 0, 0.8);
}

.panel-status.matched {
  background: rgba(255, 204, 0, 0.1);
  color: rgba(255, 204, 0, 0.8);
}

.panel-status.waiting {
  background: rgba(0, 191, 255, 0.1);
  color: rgba(0, 191, 255, 0.8);
}

.panel-status.done {
  background: rgba(0, 255, 0, 0.1);
  color: rgba(0, 255, 0, 0.8);
}

.panel-body {
  padding: 20px;
}

.progress-container {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.progress-bar {
  width: 100%;
  height: 8px;
  background: rgba(0, 255, 255, 0.1);
  border-radius: 4px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, rgba(0, 255, 255, 0.8), rgba(0, 191, 255, 0.8));
  border-radius: 4px;
  transition: width 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 0 10px rgba(0, 255, 255, 0.5);
}

.progress-text {
  text-align: center;
  font-size: 14px;
  color: rgba(0, 255, 255, 0.9);
}

.matched-info,
.waiting-info,
.done-info {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}

.matched-icon,
.done-icon {
  font-size: 32px;
  color: rgba(0, 255, 0, 0.8);
}

.matched-text,
.done-text {
  font-size: 14px;
  color: rgba(0, 255, 255, 0.9);
}

.waiting-spinner {
  width: 40px;
  height: 40px;
  border: 3px solid rgba(0, 255, 255, 0.2);
  border-top-color: rgba(0, 255, 255, 0.8);
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

.waiting-text {
  font-size: 14px;
  color: rgba(0, 255, 255, 0.9);
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

.panel-footer {
  display: flex;
  justify-content: center;
  padding: 16px;
  border-top: 1px solid rgba(0, 255, 255, 0.2);
}

.cancel-button,
.close-button {
  padding: 10px 30px;
  border: 1px solid rgba(255, 0, 0, 0.5);
  border-radius: 6px;
  background: rgba(255, 0, 0, 0.1);
  color: rgba(255, 0, 0, 0.8);
  font-size: 14px;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.cancel-button:hover,
.close-button:hover {
  background: rgba(255, 0, 0, 0.2);
  transform: scale(1.05);
}

.work-mode .tool-runtime-panel {
  border-color: rgba(255, 0, 0, 0.5);
  box-shadow: 0 0 20px rgba(255, 0, 0, 0.3);
}

.work-mode .panel-title {
  color: rgba(255, 0, 0, 0.9);
}

.work-mode .progress-fill {
  background: linear-gradient(90deg, rgba(255, 0, 0, 0.8), rgba(255, 51, 51, 0.8));
  box-shadow: 0 0 10px rgba(255, 0, 0, 0.5);
}
</style>
