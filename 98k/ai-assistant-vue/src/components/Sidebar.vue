<template>
  <div class="sidebar">
    <div class="sidebar-header">
      <h4>AI 智能助手</h4>
      <small style="opacity: 0.7">出货单管理系统</small>
    </div>
    <div class="sidebar-menu">
      <div
        v-for="item in menuItems"
        :key="item.key"
        class="menu-item"
        :class="{ active: activeView === item.key }"
        @click="selectView(item.key)"
      >
        <span>{{ item.icon }}</span>
        <span>{{ item.name }}</span>
      </div>
    </div>
    <div style="padding: 15px; border-top: 1px solid rgba(255,255,255,0.1);">
      <div class="status-indicator" style="margin-bottom: 10px;">
        <span class="status-dot online"></span>
        <span>系统正常</span>
      </div>
      <div class="mode-switch" id="modeSwitch">
        <span class="mode-label">专业模式</span>
        <div 
          class="toggle-switch" 
          :class="{ active: isProMode }"
          @click="toggleProMode"
        >
          <div class="toggle-slider"></div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { defineProps, defineEmits, ref } from 'vue'

const props = defineProps({
  activeView: {
    type: String,
    required: true
  },
  isProMode: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['change-view', 'toggle-pro-mode'])

const menuItems = [
  { key: 'chat', name: '智能对话', icon: '💬' },
  { key: 'products', name: '产品管理', icon: '📦' },
  { key: 'materials', name: '原材料仓库', icon: '🏭' },
  { key: 'orders', name: '出货单', icon: '📋' },
  { key: 'shipment-records', name: '出货记录管理', icon: '📊' },
  { key: 'customers', name: '客户管理', icon: '👥' },
  { key: 'wechat-contacts', name: '微信联系人列表', icon: '📱' },
  { key: 'print', name: '标签打印', icon: '🖨️' },
  { key: 'template-preview', name: '模板预览', icon: '📄' },
  { key: 'settings', name: '系统设置', icon: '⚙️' },
  { key: 'tools', name: '工具表', icon: '🔧' }
]

const selectView = (key) => {
  emit('change-view', key)
}

const toggleProMode = () => {
  emit('toggle-pro-mode')
}
</script>
