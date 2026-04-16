<template>
  <div class="main-container">
    <Sidebar
      :active-view="activeView"
      :is-pro-mode="isProMode"
      @change-view="handleViewChange"
      @toggle-pro-mode="handleToggleProMode"
    />
    <div class="main-content">
      <div class="top-bar">
        <div class="page-title">{{ currentViewTitle }}</div>
      </div>
      <slot></slot>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import Sidebar from './Sidebar.vue'

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

const viewTitles = {
  'chat': '智能对话',
  'products': '产品管理',
  'materials': '原材料仓库',
  'orders': '出货单',
  'shipment-records': '出货记录管理',
  'customers': '客户管理',
  'wechat-contacts': '微信联系人列表',
  'print': '标签打印',
  'template-preview': '模板预览',
  'settings': '系统设置',
  'tools': '工具表'
}

const currentViewTitle = computed(() => {
  return viewTitles[props.activeView] || '未知页面'
})

const handleViewChange = (viewKey) => {
  emit('change-view', viewKey)
}

const handleToggleProMode = () => {
  emit('toggle-pro-mode')
}
</script>
