/**
 * 核心侧栏菜单键的展示名：与 Sidebar 一致。
 * 优先级：Mod manifest `menu_overrides[].label` → 行业名 → 默认名。
 */

import { DEFAULT_INDUSTRY_ID } from '@/constants/industryDefaults'
import { INDUSTRY_PRESETS } from '@/constants/industryPresets'

export type MenuOverrideRow = {
  key?: string
  label?: string
  icon?: string
  iconClass?: string
  hidden?: boolean
}

export type ModForNavLabel = {
  menu_overrides?: MenuOverrideRow[]
}

/** 与 MainLayout.viewTitlesBase 对齐；默认文案保持通用宿主语境，行业词汇由 preset / Mod 覆盖 */
export const MENU_DEFAULT_NAMES: Record<string, string> = {
  chat: '智能对话',
  'ai-ecosystem': '智能生态',
  brain: '智脑集成',
  'model-payment': '模型服务',
  'kitten-finance': '财务分析',
  'mod-store': '能力库',
  products: '业务对象',
  'materials-list': '资源列表',
  materials: '资源库',
  'traditional-mode': '表格模式',
  'business-docking': '业务对接',
  orders: '业务单据',
  'orders-create': '新建业务单据',
  'shipment-records': '业务记录',
  customers: '组织管理',
  'data-sources': '数据来源',
  'wechat-contacts': '企业微信联系人',
  print: '模板与打印',
  'printer-list': '打印机列表',
  'template-preview': '模板库',
  console: '模板库',
  settings: '系统设置',
  tools: '工具表',
  'approval-hub': '审批中心',
  'enterprise-customer-service': '外部客服',
  'other-tools': '员工工作流',
  'workflow-employee-space': '员工空间',
  'workflow-visualization': '流程可视化',
  purchase: '耗材申领',
  'label-editor': '模板编辑器',
  'batch-analyze': '批量分析',
  'chat-debug': '对话调试',
}

/**
 * 行业层名称：与 MainLayout.viewTitles、shellMenuLabels 等多处共用。
 */
export const INDUSTRY_MENU_LABELS: Record<string, Record<string, string>> = {
  涂料: {
    materials: '原材料仓库',
    products: '产品管理',
    'materials-list': '原材料列表',
    orders: '出货单管理',
    'shipment-records': '出货记录',
    customers: '客户管理',
    print: '标签打印',
  },
  考勤: {
    materials: '排班资源',
    products: '人员管理',
    'materials-list': '班次列表',
    orders: '考勤单管理',
    'shipment-records': '考勤记录',
    customers: '部门管理',
    print: '考勤表打印',
  },
  电商: {
    materials: '商品仓库',
    products: '商品管理',
    'materials-list': '商品列表',
    orders: '订单管理',
    'shipment-records': '出货记录',
    customers: '买家管理',
    print: '面单打印',
  },
  餐饮: {
    materials: '食材仓库',
    products: '食材管理',
    'materials-list': '食材列表',
    orders: '订单管理',
    'shipment-records': '出货记录',
    customers: '供应商管理',
    print: '食材标签',
  },
  物流: {
    materials: '货物仓库',
    products: '货物管理',
    'materials-list': '货物列表',
    orders: '运单管理',
    'shipment-records': '出货记录',
    customers: '收发方管理',
    print: '运单打印',
  },
}

// 与 industryPresets.menuLabels 对齐，避免仅改一处导致菜单文案不一致
for (const preset of Object.values(INDUSTRY_PRESETS)) {
  if (!INDUSTRY_MENU_LABELS[preset.id]) {
    INDUSTRY_MENU_LABELS[preset.id] = { ...preset.menuLabels }
  } else {
    Object.assign(INDUSTRY_MENU_LABELS[preset.id], preset.menuLabels)
  }
}

function modLabelOverride(menuKey: string, modsForUi: ModForNavLabel[] | null | undefined): string {
  if (!menuKey || !Array.isArray(modsForUi) || !modsForUi.length) return ''
  for (const mod of modsForUi) {
    const rows = mod?.menu_overrides
    if (!Array.isArray(rows)) continue
    for (const row of rows) {
      if (!row || typeof row !== 'object') continue
      if (row.hidden === true) continue
      const k = String(row.key || '').trim()
      if (k !== menuKey) continue
      const label = String(row.label || '').trim()
      if (label) return label
    }
  }
  return ''
}

export function resolveCoreNavLabel(
  menuKey: string,
  industryId: string,
  modsForUi: ModForNavLabel[] | null | undefined,
): string {
  const key = String(menuKey || '').trim()
  if (!key) return ''
  const fromMod = modLabelOverride(key, modsForUi)
  if (fromMod) return fromMod
  const byInd =
    INDUSTRY_MENU_LABELS[industryId] || INDUSTRY_MENU_LABELS[DEFAULT_INDUSTRY_ID]
  if (byInd[key]) return byInd[key]
  return MENU_DEFAULT_NAMES[key] || ''
}
