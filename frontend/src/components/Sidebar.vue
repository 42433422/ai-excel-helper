<template>
  <div class="sidebar">
    <div class="sidebar-header">
      <div class="sidebar-brand" aria-label="品牌与标题">
        <img
          class="sidebar-brand-logo"
          src="/brand-xc-logo.jpg"
          width="40"
          height="40"
          alt=""
          decoding="async"
        />
        <div class="sidebar-brand-text">
          <h4>AI 智能助手</h4>
          <small style="opacity: 0.7">出货单管理系统</small>
        </div>
      </div>
    </div>
    <div class="sidebar-menu" :class="{ 'reorder-enabled': sidebarLayoutStore.reorderEnabled }">
      <button
        v-for="item in menuItems"
        :key="item.key"
        class="menu-item"
        type="button"
        style="width:100%; text-align:left; border:none; background:transparent;"
        :class="{
          active: activeView === item.key,
          'drag-armed': armedDragKey === item.key,
          'dragging': draggingKey === item.key,
          'drop-target': dragOverKey === item.key && draggingKey !== item.key
        }"
        :data-view="item.key"
        :aria-label="item.name"
        :title="item.name"
        :draggable="sidebarLayoutStore.reorderEnabled"
        @mousedown="onPressStart(item.key)"
        @mouseup="onPressEnd"
        @mouseleave="onPressEnd"
        @dragstart="onDragStart($event, item.key)"
        @dragover="onDragOver($event, item.key)"
        @drop="onDrop($event, item.key)"
        @dragend="onDragEnd"
        @click="selectView(item.key)"
      >
        <span class="menu-item-icon" aria-hidden="true">
          <i class="fa" :class="item.iconClass"></i>
        </span>
        <span>{{ item.name }}</span>
      </button>
    </div>
    <div class="sidebar-footer">
      <div class="sidebar-status-mods-row">
        <div class="status-indicator">
          <span class="status-dot online"></span>
          <span>系统正常</span>
        </div>
        <div
          v-if="primaryModChip"
          class="sidebar-mods-badges"
          :title="primaryModChip.fullName"
          aria-label="已加载扩展模块"
        >
          <span class="sidebar-mod-chip">{{ primaryModChip.shortLabel }}</span>
        </div>
      </div>
      <button
        class="mode-switch"
        id="modeSwitch"
        type="button"
        aria-label="切换专业模式"
        @click="toggleProMode"
        style="width:100%; border:none; background:transparent; padding:0; cursor:pointer;"
      >
        <span class="mode-label">
          {{ isProMode ? '切换到普通版' : '切换到专业版' }}
        </span>
        <div 
          class="toggle-switch" 
          id="proModeToggle"
          :class="{ active: isProMode }"
        >
          <div class="toggle-slider"></div>
        </div>
      </button>
      <div class="current-mode-text">
        当前：{{ currentModeText }}
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { storeToRefs } from 'pinia'
import { useIndustryStore } from '@/stores/industry'
import { useSidebarLayoutStore } from '@/stores/sidebarLayout'
import { useModsStore } from '@/stores/mods'
import { useModRoutes } from '@/composables/useModRoutes'

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

const industryStore = useIndustryStore()
const sidebarLayoutStore = useSidebarLayoutStore()
const modsStore = useModsStore()
const { mods: modsFromStore } = storeToRefs(modsStore)
const { modMenuItems, initializeMods } = useModRoutes()

function shortModLabel(name) {
  const s = String(name || '').trim()
  if (!s) return 'Mod'
  return s.length > 8 ? `${s.slice(0, 7)}…` : s
}

const loadedModChips = computed(() =>
  (modsFromStore.value || []).map((m) => ({
    id: m.id,
    shortLabel: shortModLabel((m.name && String(m.name).trim()) || m.id),
    fullName: (m.name && String(m.name).trim()) || m.id,
  }))
)

const primaryModChip = computed(() => {
  const chips = loadedModChips.value
  return chips.length > 0 ? chips[0] : null
})

const modsSummaryTitle = computed(() =>
  loadedModChips.value.map((m) => m.fullName).join('、')
)
const PRO_INTENT_EXPERIENCE_KEY = 'xcagi_pro_intent_experience'
const proIntentExperienceEnabled = ref(localStorage.getItem(PRO_INTENT_EXPERIENCE_KEY) === '1')
const LONG_PRESS_MS = 320
const armedDragKey = ref('')
const draggingKey = ref('')
const dragOverKey = ref('')
let pressTimer = null

const menuItemsBase = [
  { key: 'chat', name: '智能对话', iconClass: 'fa-comments-o' },
  { key: 'ai-ecosystem', name: 'AI生态', iconClass: 'fa-sitemap' },
  { key: 'products', name: '产品管理', iconClass: 'fa-cubes' },
  { key: 'materials', name: '原材料仓库', iconClass: 'fa-archive' },
  { key: 'business-docking', name: '业务对接', iconClass: 'fa-exchange' },
  { key: 'shipment-records', name: '出货记录', iconClass: 'fa-industry' },
  { key: 'customers', name: '客户管理', iconClass: 'fa-users' },
  { key: 'wechat-contacts', name: '微信联系人列表', iconClass: 'fa-weixin' },
  { key: 'print', name: '标签打印', iconClass: 'fa-print' },
  { key: 'printer-list', name: '打印机列表', iconClass: 'fa-print' },
  { key: 'template-preview', name: '模板库', iconClass: 'fa-file-o' },
  { key: 'settings', name: '系统设置', iconClass: 'fa-cog' },
  { key: 'tools', name: '工具表', iconClass: 'fa-wrench' },
  { key: 'other-tools', name: '员工工作流管理', iconClass: 'fa-sitemap' }
]

const industryMenuNameMap = {
  涂料: {
    products: '产品管理',
    materials: '原材料仓库',
    'shipment-records': '出货记录',
    customers: '客户管理',
    print: '标签打印'
  },
  电商: {
    products: '商品管理',
    materials: '商品仓库',
    'shipment-records': '出货记录',
    customers: '买家管理',
    print: '面单打印'
  },
  餐饮: {
    products: '食材管理',
    materials: '食材仓库',
    'shipment-records': '出货记录',
    customers: '供应商管理',
    print: '食材标签'
  },
  物流: {
    products: '货物管理',
    materials: '货物仓库',
    'shipment-records': '出货记录',
    customers: '收发方管理',
    print: '运单打印'
  }
}

const menuItems = computed(() => {
  const industryId = String(industryStore.currentIndustryId || '涂料')
  const byIndustry = industryMenuNameMap[industryId] || industryMenuNameMap['涂料']
  const localized = menuItemsBase.map((item) => ({
    ...item,
    name: byIndustry[item.key] || item.name
  }))
  const allItems = [...localized, ...modMenuItems.value]
  return sidebarLayoutStore.applyOrder(allItems)
})

const currentModeText = computed(() => {
  if (props.isProMode) {
    return '专业版（增强执行）'
  }
  if (proIntentExperienceEnabled.value) {
    return '普通版（专业意图体验）'
  }
  return '普通版（标准对话）'
})

const syncProIntentExperience = () => {
  proIntentExperienceEnabled.value = localStorage.getItem(PRO_INTENT_EXPERIENCE_KEY) === '1'
}

const selectView = (key) => {
  if (draggingKey.value) return
  emit('change-view', key)
}

const toggleProMode = () => {
  emit('toggle-pro-mode')
}

const clearPressTimer = () => {
  if (pressTimer) {
    window.clearTimeout(pressTimer)
    pressTimer = null
  }
}

const onPressStart = (key) => {
  if (!sidebarLayoutStore.reorderEnabled) return
  clearPressTimer()
  pressTimer = window.setTimeout(() => {
    armedDragKey.value = key
  }, LONG_PRESS_MS)
}

const onPressEnd = () => {
  clearPressTimer()
  if (!draggingKey.value) {
    armedDragKey.value = ''
    dragOverKey.value = ''
  }
}

const onDragStart = (event, key) => {
  if (!sidebarLayoutStore.reorderEnabled || armedDragKey.value !== key) {
    event.preventDefault()
    return
  }
  draggingKey.value = key
  dragOverKey.value = ''
  event.dataTransfer.effectAllowed = 'move'
  event.dataTransfer.setData('text/plain', key)
}

const onDragOver = (event, key) => {
  if (!draggingKey.value || draggingKey.value === key) return
  event.preventDefault()
  dragOverKey.value = key
}

const onDrop = (event, key) => {
  if (!draggingKey.value) return
  event.preventDefault()
  sidebarLayoutStore.moveItem(draggingKey.value, key, menuItemsBase.map((m) => m.key))
  dragOverKey.value = ''
}

const onDragEnd = () => {
  clearPressTimer()
  armedDragKey.value = ''
  draggingKey.value = ''
  dragOverKey.value = ''
}

onMounted(async () => {
  window.addEventListener('storage', syncProIntentExperience)
  window.addEventListener('xcagi:pro-intent-experience-changed', syncProIntentExperience)
  sidebarLayoutStore.initialize(menuItemsBase.map((m) => m.key))
  if (!industryStore.isLoaded) {
    try {
      await industryStore.initialize()
    } catch (_e) {
    }
  }
  if (!modsStore.isLoaded) {
    await modsStore.initialize()
  }
})

onBeforeUnmount(() => {
  window.removeEventListener('storage', syncProIntentExperience)
  window.removeEventListener('xcagi:pro-intent-experience-changed', syncProIntentExperience)
})
</script>

<style scoped>
.sidebar-status-mods-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 6px 8px;
  margin-bottom: 10px;
}

.sidebar-status-mods-row .status-indicator {
  margin-bottom: 0;
  flex-shrink: 0;
  min-width: 0;
}

.sidebar-mods-badges {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  justify-content: flex-end;
  flex: 1 1 auto;
  min-width: 0;
  max-width: 70%;
}

.sidebar-mod-chip {
  display: inline-block;
  max-width: 100%;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 10px;
  line-height: 1.35;
  font-weight: 600;
  color: #3730a3;
  background: #e0e7ff;
  border: 1px solid #c7d2fe;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.sidebar-menu.reorder-enabled .menu-item {
  cursor: grab;
}

.sidebar-menu.reorder-enabled .menu-item.drag-armed {
  outline: 1px dashed rgba(125, 211, 252, 0.7);
}

.sidebar-menu.reorder-enabled .menu-item.dragging {
  opacity: 0.5;
}

.sidebar-menu.reorder-enabled .menu-item.drop-target {
  box-shadow: inset 0 0 0 1px rgba(125, 211, 252, 0.7);
  border-radius: 8px;
}
</style>
