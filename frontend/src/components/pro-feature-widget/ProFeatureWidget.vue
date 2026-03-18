<template>
  <div 
    class="pro-feature-widget"
    :class="{ 'visible': visible, 'work-mode': isWorkMode }"
  >
    <div class="widget-header">
      <div class="widget-tabs">
        <button 
          v-for="tab in tabs" 
          :key="tab.id"
          class="tab-btn"
          :class="{ 'active': activePanel === tab.id }"
          @click="activePanel = tab.id"
        >
          {{ tab.name }}
        </button>
      </div>
      <button class="close-btn" @click="handleClose">×</button>
    </div>
    
    <div class="widget-body">
      <WeChatLoginPanel 
        v-if="activePanel === 'wechat'" 
        @close="handleClose"
      />
      <UserListPanel 
        v-if="activePanel === 'users'"
        @close="handleClose"
      />
      <ProductQueryPanel 
        v-if="activePanel === 'products'"
        @close="handleClose"
      />
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import WeChatLoginPanel from './WeChatLoginPanel.vue'
import UserListPanel from './UserListPanel.vue'
import ProductQueryPanel from './ProductQueryPanel.vue'

const props = defineProps({
  visible: {
    type: Boolean,
    default: false
  },
  activePanel: {
    type: String,
    default: 'wechat'
  },
  isWorkMode: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['close', 'panelChange'])

const tabs = [
  { id: 'wechat', name: '微信登录' },
  { id: 'users', name: '客户管理' },
  { id: 'products', name: '产品查询' }
]

const activePanel = ref(props.activePanel)

function handleClose() {
  emit('close')
}
</script>

<style scoped>
.pro-feature-widget {
  position: fixed;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%) scale(0.9);
  width: 600px;
  max-height: 80vh;
  background: rgba(10, 14, 39, 0.98);
  border: 1px solid rgba(0, 255, 255, 0.5);
  border-radius: 16px;
  box-shadow: 0 0 40px rgba(0, 255, 255, 0.3);
  backdrop-filter: blur(20px);
  opacity: 0;
  pointer-events: none;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  z-index: 1100;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.pro-feature-widget.visible {
  opacity: 1;
  pointer-events: auto;
  transform: translate(-50%, -50%) scale(1);
}

.work-mode .pro-feature-widget {
  border-color: rgba(255, 0, 0, 0.5);
  box-shadow: 0 0 40px rgba(255, 0, 0, 0.3);
}

.widget-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  background: rgba(0, 255, 255, 0.05);
  border-bottom: 1px solid rgba(0, 255, 255, 0.2);
}

.work-mode .widget-header {
  background: rgba(255, 0, 0, 0.05);
  border-bottom-color: rgba(255, 0, 0, 0.2);
}

.widget-tabs {
  display: flex;
  gap: 8px;
}

.tab-btn {
  padding: 8px 16px;
  background: transparent;
  border: 1px solid rgba(0, 255, 255, 0.3);
  border-radius: 6px;
  color: rgba(0, 255, 255, 0.7);
  font-size: 14px;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.tab-btn:hover {
  background: rgba(0, 255, 255, 0.1);
  border-color: rgba(0, 255, 255, 0.5);
}

.tab-btn.active {
  background: rgba(0, 255, 255, 0.2);
  border-color: rgba(0, 255, 255, 0.8);
  color: rgba(0, 255, 255, 0.9);
}

.work-mode .tab-btn {
  border-color: rgba(255, 0, 0, 0.3);
  color: rgba(255, 0, 0, 0.7);
}

.work-mode .tab-btn:hover {
  background: rgba(255, 0, 0, 0.1);
  border-color: rgba(255, 0, 0, 0.5);
}

.work-mode .tab-btn.active {
  background: rgba(255, 0, 0, 0.2);
  border-color: rgba(255, 0, 0, 0.8);
  color: rgba(255, 0, 0, 0.9);
}

.close-btn {
  background: transparent;
  border: none;
  color: rgba(0, 255, 255, 0.7);
  font-size: 28px;
  cursor: pointer;
  padding: 0;
  line-height: 1;
  transition: color 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.close-btn:hover {
  color: rgba(0, 255, 255, 0.9);
}

.work-mode .close-btn {
  color: rgba(255, 0, 0, 0.7);
}

.work-mode .close-btn:hover {
  color: rgba(255, 0, 0, 0.9);
}

.widget-body {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
}
</style>
