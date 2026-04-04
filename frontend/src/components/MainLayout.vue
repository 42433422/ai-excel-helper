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
        <div
          class="mode-badge"
          :class="[props.isProMode ? 'pro' : 'normal', { 'with-mod': hasModsForUi }]"
        >
          {{ modeBadgeText }}
        </div>
        <TopAssistantFloat />
      </div>
      <slot></slot>
    </div>
    <TutorialOverlay />
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { storeToRefs } from 'pinia'
import { useRoute, useRouter } from 'vue-router'
import { useIndustryStore } from '@/stores/industry'
import { useModsStore } from '@/stores/mods'
import { useModRoutes } from '@/composables/useModRoutes'
import Sidebar from './Sidebar.vue'
import TopAssistantFloat from './TopAssistantFloat.vue'
import TutorialOverlay from './TutorialOverlay.vue'

const props = defineProps({
  isProMode: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['toggle-pro-mode'])

const route = useRoute()
const router = useRouter()
const industryStore = useIndustryStore()
const modsStore = useModsStore()
const { modsForUi } = storeToRefs(modsStore)
const { modMenuItems } = useModRoutes()

/** 原版模式或未加载扩展时为空，与侧栏 Mod 菜单一致 */
const hasModsForUi = computed(() => modsForUi.value.length > 0)

/** 顶栏角标：普通/专业 + 已加载 Mod 时追加简写（如 ·Pro） */
function resolveModBadgeSuffix() {
  const list = modsForUi.value
  if (!list.length) return ''
  const lead = list.find((m) => m.primary) || list[0]
  const raw = `${lead?.name || ''} ${lead?.id || ''}`.trim()
  if (/pro|奇士美|qsm|sz-qsm/i.test(raw)) return 'Pro'
  const name = String(lead?.name || lead?.id || 'Mod').trim()
  if (name.length <= 8) return name
  return `${name.slice(0, 6)}…`
}

const modeBadgeText = computed(() => {
  const base = props.isProMode ? '专业版' : '普通版'
  if (!hasModsForUi.value) return base
  return `${base}·${resolveModBadgeSuffix()}`
})

const modPathToSidebarKey = computed(() => {
  const m = {}
  for (const item of modMenuItems.value) {
    if (item.path) m[item.path] = item.key
  }
  return m
})

const viewTitlesBase = {
  chat: '智能对话',
  'ai-ecosystem': 'AI生态',
  products: '产品管理',
  'materials-list': '原材料列表',
  materials: '原材料仓库',
  'business-docking': '业务对接',
  'orders-create': '新建订单',
  'shipment-records': '出货记录',
  customers: '客户管理',
  'wechat-contacts': '微信联系人列表',
  print: '标签打印',
  'printer-list': '打印机列表',
  'template-preview': '模板库',
  console: '模板库',
  settings: '系统设置',
  tools: '工具表',
  'other-tools': '员工工作流管理',
  'workflow-visualization': '工作流可视化'
}

const industryTitleMap = {
  涂料: {
    products: '产品管理',
    'materials-list': '原材料列表',
    'shipment-records': '出货记录',
    customers: '客户管理',
    print: '标签打印'
  },
  电商: {
    products: '商品管理',
    'materials-list': '商品列表',
    'shipment-records': '出货记录',
    customers: '买家管理',
    print: '面单打印'
  },
  餐饮: {
    products: '食材管理',
    'materials-list': '食材列表',
    'shipment-records': '出货记录',
    customers: '供应商管理',
    print: '食材标签'
  },
  物流: {
    products: '货物管理',
    'materials-list': '货物列表',
    'shipment-records': '出货记录',
    customers: '收发方管理',
    print: '运单打印'
  }
}

const routeNameMap = {
  '/': 'chat',
  '/ai-ecosystem': 'ai-ecosystem',
  '/products': 'products',
  '/materials-list': 'materials-list',
  '/materials': 'materials',
  '/business-docking': 'business-docking',
  '/orders/create': 'orders-create',
  '/shipment-records': 'shipment-records',
  '/customers': 'customers',
  '/wechat-contacts': 'wechat-contacts',
  '/print': 'print',
  '/printer-list': 'printer-list',
  '/template-preview': 'template-preview',
  '/console': 'console',
  '/settings': 'settings',
  '/tools': 'tools',
  '/other-tools': 'other-tools',
  '/workflow-visualization': 'workflow-visualization'
}

const currentRouteName = computed(() => {
  const modKey = modPathToSidebarKey.value[route.path]
  if (modKey) return modKey
  return routeNameMap[route.path] || String(route.name || '') || 'chat'
})

const viewTitles = computed(() => {
  const industryId = String(industryStore.currentIndustryId || '涂料')
  const byIndustry = industryTitleMap[industryId] || industryTitleMap['涂料']
  return {
    ...viewTitlesBase,
    ...byIndustry
  }
})

const currentViewTitle = computed(() => {
  const metaTitle = route.meta?.title
  if (typeof metaTitle === 'string' && metaTitle.trim()) return metaTitle
  return viewTitles.value[currentRouteName.value] || '未知页面'
})

const handleViewChange = (viewKey) => {
  const modItem = modMenuItems.value.find((m) => m.key === viewKey)
  if (modItem?.path) {
    router.push(modItem.path)
    return
  }
  const routePath = Object.entries(routeNameMap).find(
    ([, name]) => name === viewKey
  )?.[0]
  if (routePath) {
    router.push(routePath)
  }
}

onMounted(async () => {
  if (!industryStore.isLoaded) {
    try {
      await industryStore.initialize()
    } catch (_e) {
      // 行业信息加载失败时，顶部标题保持默认文案
    }
  }
})
</script>

<style scoped>
.mode-badge {
  margin-left: auto;
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 12px;
  line-height: 1;
  font-weight: 600;
}

.mode-badge.normal {
  color: #1f2937;
  background: #e5e7eb;
  border: 1px solid #d1d5db;
}

.mode-badge.pro {
  color: #7dd3fc;
  background: rgba(14, 116, 144, 0.2);
  border: 1px solid rgba(125, 211, 252, 0.35);
}

/* 已加载 Mod：在普通/专业底子上略强调「扩展环境」 */
.mode-badge.with-mod.normal {
  background: linear-gradient(135deg, #eef2ff 0%, #e0e7ff 100%);
  border-color: #a5b4fc;
  color: #3730a3;
}

.mode-badge.with-mod.pro {
  box-shadow: 0 0 0 1px rgba(125, 211, 252, 0.2);
}
</style>
