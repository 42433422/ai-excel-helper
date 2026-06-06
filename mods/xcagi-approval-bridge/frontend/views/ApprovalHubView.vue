<template>
  <div class="approval-hub">
    <nav class="approval-hub-tabs" aria-label="审批功能分区">
      <RouterLink
        v-for="tab in tabs"
        :key="tab.name"
        :to="`${hubBase}/${routePathMap[tab.name]}`"
        class="approval-hub-tab"
        :class="{ active: isActiveTab(tab.name) }"
      >
        <i class="fa" :class="tab.icon" aria-hidden="true" />
        {{ tab.label }}
      </RouterLink>
    </nav>
    <div class="approval-hub-content">
      <RouterView />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { APPROVAL_BRIDGE_MOD_ID } from '@/constants/approvalMod'

const route = useRoute()

const hubBase = computed(() =>
  route.meta?.mod === APPROVAL_BRIDGE_MOD_ID ||
  String(route.path).includes(`/mod/${APPROVAL_BRIDGE_MOD_ID}/`)
    ? `/mod/${APPROVAL_BRIDGE_MOD_ID}/approval-hub`
    : '/approval-hub',
)

const modRouteNames: Record<string, string> = {
  'approval-workspace': 'mod-approval-workspace',
  'approval-flow-management': 'mod-approval-flow-management',
  'approval-rules': 'mod-approval-rules',
}

const tabs = [
  { name: 'approval-workspace', label: '工作台', icon: 'fa-tasks' },
  { name: 'approval-flow-management', label: '流程管理', icon: 'fa-sitemap' },
  { name: 'approval-rules', label: '流程规则', icon: 'fa-check-square-o' }
] as const

// 嵌套路由的相对路径映射
const routePathMap: Record<string, string> = {
  'approval-workspace': 'workspace',
  'approval-flow-management': 'flow-management',
  'approval-rules': 'rules'
}

function isActiveTab(name: string) {
  const n = route.name
  return n === name || n === modRouteNames[name]
}
</script>

<style scoped>
.approval-hub {
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.approval-hub-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  padding: 0 0 12px;
  margin-bottom: 4px;
  border-bottom: 1px solid rgba(148, 163, 184, 0.35);
  flex-shrink: 0;
}

.approval-hub-tab {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 14px;
  border-radius: 8px;
  text-decoration: none;
  color: #64748b;
  font-size: 14px;
  font-weight: 500;
  transition: background 0.15s ease, color 0.15s ease;
}

.approval-hub-tab:hover {
  background: rgba(148, 163, 184, 0.12);
  color: #334155;
}

.approval-hub-tab.active {
  background: rgba(14, 165, 233, 0.12);
  color: #0369a1;
}

.approval-hub-tab .fa {
  opacity: 0.85;
}

.approval-hub-content {
  min-height: 0;
  flex: 1;
  padding-top: 8px;
}
</style>
