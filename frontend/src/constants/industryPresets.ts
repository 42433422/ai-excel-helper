/**
 * 跨行业 UI 预设：宿主与 Mod 制作端共用同一套 id（与 manifest.industry.id、/api/system/industry 一致）。
 * 运行时优先 GET /api/system/industry-presets（config/industry_presets.json），本文件为离线 fallback。
 */

import { industryPresetIds, industryPresets } from '@/stores/hostConfig'

export type IndustryQuickButton = { text: string; label: string }

export type IndustryPreset = {
  id: string
  name: string
  scenario: string
  welcomeIntro: string
  welcomeBullets: string[]
  quickButtons: IndustryQuickButton[]
  placeholderNormal: string
  placeholderPro: string
  menuLabels: Record<string, string>
  uiLabels: Record<string, string>
}

export const INDUSTRY_PRESET_IDS = [
  '通用',
  '涂料',
  '考勤',
  '烤禽',
  '批发',
  '电商',
  '餐饮',
  '物流',
] as const

export const INDUSTRY_PRESETS: Record<string, IndustryPreset> = {
  通用: {
    id: '通用',
    name: '通用',
    scenario: '多行业本地工作台。',
    welcomeIntro: '你好，我是业务助手。',
    welcomeBullets: ['查数据与单据', '导出打印'],
    quickButtons: [
      { text: '帮我查一下常用数据', label: '查数据' },
      { text: '打开客户或单位列表', label: '列表' },
      { text: '今天的业务单据', label: '今日单据' },
      { text: '有哪些需要处理的事项', label: '待办' },
      { text: '测试预览', label: '测试预览' },
    ],
    placeholderNormal: '输入需求',
    placeholderPro: '复合任务',
    menuLabels: {},
    uiLabels: { entity: '条目', model_label: '编号', shipment_order: '业务单', records: '业务记录' },
  },
  涂料: {
    id: '涂料',
    name: '涂料/油漆',
    scenario: '涂料化工批发。',
    welcomeIntro: '你好，涂料助手。',
    welcomeBullets: ['查价与客户', '开单打印'],
    quickButtons: [
      { text: '查一下A001的价格', label: '查产品' },
      { text: '有哪些客户？', label: '客户列表' },
      { text: '今天的出货单', label: '出货单' },
      { text: '库存不足的材料', label: '库存预警' },
      { text: '帮我打印A001标签', label: '打印标签' },
      { text: '测试预览', label: '测试预览' },
    ],
    placeholderNormal: '查产品',
    placeholderPro: '开单打印',
    menuLabels: {
      materials: '原材料仓库',
      products: '产品管理',
      'materials-list': '原材料列表',
      orders: '出货单管理',
      'shipment-records': '出货记录',
      customers: '客户管理',
      print: '标签打印',
    },
    uiLabels: { entity: '产品', model_label: '型号', shipment_order: '出货单', records: '出货记录' },
  },
  考勤: {
    id: '考勤',
    name: '考勤/排班',
    scenario: '考勤排班。',
    welcomeIntro: '你好，考勤助手。',
    welcomeBullets: ['查员工出勤', '考勤单'],
    quickButtons: [
      { text: '查询工号1001的员工信息', label: '查员工' },
      { text: '研发部今天谁出勤', label: '今日出勤' },
      { text: '生成本月考勤单', label: '考勤单' },
      { text: '登记李四请假半天', label: '请假登记' },
      { text: '打印考勤表', label: '打印考勤' },
      { text: '测试预览', label: '测试预览' },
    ],
    placeholderNormal: '查员工',
    placeholderPro: '汇总考勤',
    menuLabels: {
      materials: '排班资源',
      products: '人员管理',
      'materials-list': '班次列表',
      orders: '考勤单管理',
      'shipment-records': '考勤记录',
      customers: '部门管理',
      print: '考勤表打印',
    },
    uiLabels: { entity: '员工', model_label: '工号', shipment_order: '考勤单', records: '考勤记录' },
  },
  烤禽: {
    id: '烤禽',
    name: '烤禽/熟食',
    scenario: '烤禽冷链配送。',
    welcomeIntro: '你好，烤禽助手。',
    welcomeBullets: ['查货品', '配送单'],
    quickButtons: [
      { text: '查一下今日烤鸡批发价', label: '查货品' },
      { text: '有哪些门店客户', label: '客户列表' },
      { text: '今天的配送单', label: '配送单' },
      { text: '哪些货品库存偏低', label: '库存预警' },
      { text: '打印货品标签', label: '打印标签' },
      { text: '测试预览', label: '测试预览' },
    ],
    placeholderNormal: '查货品',
    placeholderPro: '汇总配送',
    menuLabels: {
      materials: '原料/半成品',
      products: '货品管理',
      'materials-list': '原料清单',
      orders: '配送/出货单',
      'shipment-records': '出货记录',
      customers: '门店/客户',
      print: '货品标签',
    },
    uiLabels: { entity: '货品', model_label: '货号', shipment_order: '配送单', records: '出货记录' },
  },
  批发: {
    id: '批发',
    name: '批发/分销',
    scenario: '批发分销。',
    welcomeIntro: '你好，批发助手。',
    welcomeBullets: ['查价开单', '库存'],
    quickButtons: [
      { text: '查一下畅销品库存', label: '查库存' },
      { text: '批发客户列表', label: '客户' },
      { text: '今天的批发单', label: '批发单' },
      { text: '低于安全库存的SKU', label: '库存预警' },
      { text: '测试预览', label: '测试预览' },
    ],
    placeholderNormal: '查库存',
    placeholderPro: '批量开单',
    menuLabels: {
      products: '商品管理',
      orders: '批发单',
      'shipment-records': '出货记录',
      customers: '客户管理',
      print: '单据打印',
    },
    uiLabels: { entity: '商品', shipment_order: '批发单' },
  },
  电商: {
    id: '电商',
    name: '电商/零售',
    scenario: '电商零售。',
    welcomeIntro: '你好，电商助手。',
    welcomeBullets: ['查 SKU', '待发货'],
    quickButtons: [
      { text: '查 SKU 10001 库存', label: '查商品' },
      { text: '今日待发货订单', label: '待发货' },
      { text: '测试预览', label: '测试预览' },
    ],
    placeholderNormal: '查商品',
    placeholderPro: '汇总订单',
    menuLabels: {
      products: '商品管理',
      orders: '订单管理',
      'shipment-records': '出货记录',
      customers: '买家管理',
      print: '面单打印',
    },
    uiLabels: { entity: '商品', shipment_order: '订单' },
  },
  餐饮: {
    id: '餐饮',
    name: '餐饮',
    scenario: '餐饮门店。',
    welcomeIntro: '你好，餐饮助手。',
    welcomeBullets: ['查食材', '订货'],
    quickButtons: [
      { text: '查今日食材库存', label: '查食材' },
      { text: '门店订货列表', label: '订货' },
      { text: '测试预览', label: '测试预览' },
    ],
    placeholderNormal: '查食材',
    placeholderPro: '汇总订货',
    menuLabels: {
      materials: '食材仓库',
      products: '菜品/食材',
      orders: '订货单',
      customers: '供应商',
      print: '食材标签',
    },
    uiLabels: { entity: '食材', shipment_order: '订货单' },
  },
  物流: {
    id: '物流',
    name: '物流',
    scenario: '物流运单。',
    welcomeIntro: '你好，物流助手。',
    welcomeBullets: ['查运单', '发运'],
    quickButtons: [
      { text: '查在途运单', label: '在途' },
      { text: '今日新建运单', label: '运单' },
      { text: '测试预览', label: '测试预览' },
    ],
    placeholderNormal: '查运单',
    placeholderPro: '批量运单',
    menuLabels: {
      products: '货物管理',
      orders: '运单管理',
      customers: '收发方',
      print: '运单打印',
    },
    uiLabels: { entity: '货物', shipment_order: '运单' },
  },
}

/** 已加载的预设 id 列表（API 优先，否则内置 8 项） */
export function listIndustryPresetIdList(): string[] {
  const apiIds = industryPresetIds.value
  if (apiIds.length > 0) return [...apiIds]
  return [...INDUSTRY_PRESET_IDS]
}

export function getIndustryPreset(industryId: string): IndustryPreset {
  const id = String(industryId || '').trim() || '通用'
  const apiMap = industryPresets.value
  if (apiMap[id]) return apiMap[id]
  return INDUSTRY_PRESETS[id] || INDUSTRY_PRESETS['通用']
}

/** 从 Mod manifest.industry 构造可展示的预设（非 8 内置行业也可完整 UI） */
export function industryPresetFromManifest(
  ind: Record<string, unknown> | null | undefined,
): IndustryPreset | null {
  if (!ind || typeof ind !== 'object') return null
  const id = String(ind.id || '').trim()
  if (!id) return null
  const existing = getIndustryPreset(id)
  if (existing.id === id && (INDUSTRY_PRESETS[id] || industryPresets.value[id])) {
    return existing
  }
  const name = String(ind.name || id).trim() || id
  const scenario = String(ind.scenario || ind.description || '').trim()
  const uiLabels =
    ind.ui_labels && typeof ind.ui_labels === 'object'
      ? (ind.ui_labels as Record<string, string>)
      : { entity: '条目', shipment_order: '业务单' }
  const menuLabels: Record<string, string> = {}
  const overrides = ind.menu_overrides
  if (Array.isArray(overrides)) {
    for (const row of overrides) {
      if (row && typeof row === 'object') {
        const key = String((row as Record<string, unknown>).key || '').trim()
        const label = String((row as Record<string, unknown>).label || '').trim()
        if (key && label) menuLabels[key] = label
      }
    }
  }
  return {
    id,
    name,
    scenario: scenario || `${name}业务。`,
    welcomeIntro: String(ind.welcome_intro || ind.welcomeIntro || `你好，${name}助手。`),
    welcomeBullets: Array.isArray(ind.welcome_bullets)
      ? (ind.welcome_bullets as string[]).map(String).slice(0, 2)
      : ['查数据', '处理单据'],
    quickButtons: Array.isArray(ind.quick_buttons)
      ? (ind.quick_buttons as IndustryQuickButton[])
      : [{ text: '帮我查一下常用数据', label: '查数据' }],
    placeholderNormal: String(ind.placeholder_normal || '输入需求'),
    placeholderPro: String(ind.placeholder_pro || '复合任务'),
    menuLabels,
    uiLabels,
  }
}

export function listIndustryPresets(): IndustryPreset[] {
  return listIndustryPresetIdList().map((id) => getIndustryPreset(id))
}

export function getIndustryQuickButtons(industryId: string): IndustryQuickButton[] {
  return [...getIndustryPreset(industryId).quickButtons]
}

/** 识别历史会话中的欢迎语（兼容旧版考勤文案） */
export function isIndustryWelcomePlainText(plain: string): boolean {
  const t = String(plain || '').trim()
  if (!t) return false
  if (t.startsWith('您好！我是您的智能考勤助手')) return true
  for (const id of listIndustryPresetIdList()) {
    if (t.startsWith(getIndustryPreset(id).welcomeIntro)) return true
  }
  return false
}

export function getIndustryWelcomeMarkdown(industryId: string): string {
  const p = getIndustryPreset(industryId)
  const bullets = p.welcomeBullets.slice(0, 2).map((b) => `- ${b}`).join('\n')
  return `${p.welcomeIntro}\n${bullets}\n请说出需求。`
}

export function manifestIndustryFromPreset(presetId: string): Record<string, unknown> {
  const p = getIndustryPreset(presetId)
  return {
    id: p.id,
    name: p.name,
    scenario: p.scenario,
    description: p.scenario,
    units: { primary: '件', primary_label: '数量' },
    product_fields: {
      name: p.uiLabels.entity || '名称',
      model: p.uiLabels.model_label || '编号',
    },
    ui_labels: p.uiLabels,
    menu_overrides: Object.entries(p.menuLabels).map(([key, label]) => ({ key, label })),
  }
}
