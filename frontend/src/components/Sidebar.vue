<template>
  <div class="sidebar">
    <div class="sidebar-header">
      <h4>AI 智能助手</h4>
      <small style="opacity: 0.7">出货单管理系统</small>
    </div>
    <div class="sidebar-menu">
      <button
        v-for="item in menuItems"
        :key="item.key"
        class="menu-item"
        type="button"
        style="width:100%; text-align:left; border:none; background:transparent;"
        :class="{ active: activeView === item.key }"
        :data-view="item.key"
        :aria-label="item.name"
        :title="item.name"
        @click="selectView(item.key)"
      >
        <span>{{ item.icon }}</span>
        <span>{{ item.name }}</span>
      </button>
    </div>
    <div style="padding: 15px; border-top: 1px solid rgba(255,255,255,0.1);">
      <div class="status-indicator" style="margin-bottom: 10px;">
        <span class="status-dot online"></span>
        <span>系统正常</span>
      </div>
      <button
        class="mode-switch"
        id="modeSwitch"
        type="button"
        aria-label="切换专业模式"
        @click="toggleProMode"
        style="width:100%; border:none; background:transparent; padding:0; cursor:pointer;"
      >
        <span class="mode-label">专业模式</span>
        <div 
          class="toggle-switch" 
          id="proModeToggle"
          :class="{ active: isProMode }"
        >
          <div class="toggle-slider"></div>
        </div>
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

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
  { key: 'printer-list', name: '打印机列表', icon: '🖨️' },
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
