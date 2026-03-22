<template>
  <div class="main-container">
    <Sidebar
      :active-view="currentRouteName"
      :is-pro-mode="isProMode"
      @change-view="handleViewChange"
      @toggle-pro-mode="$emit('toggle-pro-mode')"
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
import { useRoute, useRouter } from 'vue-router'
import Sidebar from './Sidebar.vue'

const props = defineProps({
  isProMode: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['toggle-pro-mode'])

const route = useRoute()
const router = useRouter()

const viewTitles = {
  'chat': '智能对话',
  'products': '产品管理',
  'materials': '原材料仓库',
  'orders': '出货单',
  'orders-create': '新建订单',
  'shipment-records': '出货记录管理',
  'customers': '客户管理',
  'wechat-contacts': '微信联系人列表',
  'print': '标签打印',
  'printer-list': '打印机列表',
  'template-preview': '模板预览',
  'settings': '系统设置',
  'tools': '工具表'
}

const routeNameMap = {
  '/': 'chat',
  '/products': 'products',
  '/materials': 'materials',
  '/orders': 'orders',
  '/orders/create': 'orders-create',
  '/shipment-records': 'shipment-records',
  '/customers': 'customers',
  '/wechat-contacts': 'wechat-contacts',
  '/print': 'print',
  '/printer-list': 'printer-list',
  '/template-preview': 'template-preview',
  '/settings': 'settings',
  '/tools': 'tools'
}

const currentRouteName = computed(() => {
  return routeNameMap[route.path] || route.name || 'chat'
})

const currentViewTitle = computed(() => {
  return viewTitles[currentRouteName.value] || '未知页面'
})

const handleViewChange = (viewKey) => {
  const routePath = Object.entries(routeNameMap).find(
    ([, name]) => name === viewKey
  )?.[0]
  if (routePath) {
    router.push(routePath)
  }
}
</script>
