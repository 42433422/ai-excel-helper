/** 宿主侧栏菜单结构（与 router / MainLayout 对齐） */

export type CoreMenuCatalogItem = {
  key: string
  name: string
  iconClass: string
  children?: CoreMenuCatalogItem[]
}

/** 侧栏默认置顶项（行业 Mod 场景下仍保持在业务菜单之上） */
export const PRIMARY_CHAT_MENU_KEY = 'chat'

export function pinMenuKeyFirst<T extends { key: string }>(
  items: T[],
  key: string = PRIMARY_CHAT_MENU_KEY,
): T[] {
  const hit = items.find((i) => String(i.key) === key)
  if (!hit) return items
  return [hit, ...items.filter((i) => String(i.key) !== key)]
}

export const CORE_MENU_ITEMS_BASE: CoreMenuCatalogItem[] = [
  { key: PRIMARY_CHAT_MENU_KEY, name: '智能对话', iconClass: 'fa-comments-o' },
  { key: 'ai-ecosystem', name: '智能生态', iconClass: 'fa-sitemap' },
  { key: 'mod-store', name: '能力库', iconClass: 'fa-puzzle-piece' },
  { key: 'products', name: '业务对象', iconClass: 'fa-cubes' },
  { key: 'materials', name: '资源库', iconClass: 'fa-archive' },
  { key: 'traditional-mode', name: '表格模式', iconClass: 'fa-table' },
  { key: 'orders', name: '业务单据', iconClass: 'fa-file-text-o' },
  { key: 'shipment-records', name: '业务记录', iconClass: 'fa-industry' },
  { key: 'customers', name: '组织管理', iconClass: 'fa-users' },
  { key: 'data-sources', name: '数据来源', iconClass: 'fa-database' },
  { key: 'printer-list', name: '打印机列表', iconClass: 'fa-print' },
  { key: 'template-preview', name: '模板库', iconClass: 'fa-file-o' },
  { key: 'tools', name: '工具表', iconClass: 'fa-wrench' },
  { key: 'approval-hub', name: '审批中心', iconClass: 'fa-check-square-o' },
  {
    key: 'other-tools',
    name: '员工工作流',
    iconClass: 'fa-sitemap',
    children: [{ key: 'workflow-employee-space', name: '员工空间', iconClass: 'fa-user-circle' }],
  },
]

export const SETTINGS_MENU_ITEM: CoreMenuCatalogItem = {
  key: 'settings',
  name: '系统设置',
  iconClass: 'fa-cog',
}

export const CORE_MENU_ITEMS_TRAILING: CoreMenuCatalogItem[] = [
  { key: 'enterprise-customer-service', name: '外部客服', iconClass: 'fa-building-o' },
  { key: 'internal-customer-service', name: '内部客服', iconClass: 'fa-headphones' },
]

export const ADMIN_MENU_ITEM: CoreMenuCatalogItem = {
  key: 'admin-entitlements',
  name: '用户 Mod 管理',
  iconClass: 'fa-shield',
}

export const CORE_NAV_KEYS = [
  ...CORE_MENU_ITEMS_BASE.map((m) => m.key),
  ...CORE_MENU_ITEMS_TRAILING.map((m) => m.key),
  SETTINGS_MENU_ITEM.key,
]

export const SANDBOX_MENU_KEYS = new Set([
  'chat',
  'workflow-visualization',
  'chat-debug',
  'tools',
  'other-tools',
])

export function flattenNavKeys(items: Array<{ key: string; children?: Array<{ key: string }> }>): string[] {
  const out: string[] = []
  for (const item of items) {
    out.push(item.key)
    if (item.children?.length) {
      for (const child of item.children) {
        out.push(child.key)
      }
    }
  }
  return out
}

export function sidebarLayoutSeedKeys(): string[] {
  const keys = [
    ...CORE_MENU_ITEMS_BASE.map((m) => m.key),
    ...CORE_MENU_ITEMS_TRAILING.map((m) => m.key),
  ]
  return pinMenuKeyFirst(
    keys.map((key) => ({ key })),
    PRIMARY_CHAT_MENU_KEY,
  ).map((row) => row.key)
}
