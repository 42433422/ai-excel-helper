/**
 * 可交付宿主标准用户流程（与 docs/guides/PRODUCT_USER_FLOW.md 对齐）
 */

export const LS_PRODUCT_FLOW_COMPLETED = 'xcagi_product_flow_completed'
export const LS_PRODUCT_FLOW_HOST_ACK = 'xcagi_product_flow_host_ack'

export type ProductFlowStepId = 'welcome' | 'host-pack' | 'industry' | 'done'

export interface ProductFlowStepMeta {
  id: ProductFlowStepId
  index: number
  title: string
  subtitle: string
}

export const PRODUCT_FLOW_STEPS: ProductFlowStepMeta[] = [
  {
    id: 'welcome',
    index: 1,
    title: '认识宿主',
    subtitle: '这一份软件是独立宿主，装 MOD 后才变成你的业务系统',
  },
  {
    id: 'host-pack',
    index: 2,
    title: '宿主就绪',
    subtitle: '装齐通用能力包（对话、扩展市场、工作流桥接）',
  },
  {
    id: 'industry',
    index: 3,
    title: '行业定型',
    subtitle: '从平台安装行业 MOD，侧栏与功能变为你的垂直系统（可稍后）',
  },
  {
    id: 'done',
    index: 4,
    title: '开始使用',
    subtitle: '进入智能对话与日常操作',
  },
]

export function readProductFlowCompleted(): boolean {
  if (typeof localStorage === 'undefined') return true
  try {
    return localStorage.getItem(LS_PRODUCT_FLOW_COMPLETED) === '1'
  } catch {
    return true
  }
}

export function markProductFlowCompleted(): void {
  if (typeof localStorage === 'undefined') return
  try {
    localStorage.setItem(LS_PRODUCT_FLOW_COMPLETED, '1')
  } catch {
    /* ignore */
  }
}

export function readHostPackAcknowledged(): boolean {
  if (typeof localStorage === 'undefined') return true
  try {
    return localStorage.getItem(LS_PRODUCT_FLOW_HOST_ACK) === '1'
  } catch {
    return true
  }
}

export function markHostPackAcknowledged(): void {
  if (typeof localStorage === 'undefined') return
  try {
    localStorage.setItem(LS_PRODUCT_FLOW_HOST_ACK, '1')
  } catch {
    /* ignore */
  }
}

export function parseFlowStepQuery(raw: unknown): ProductFlowStepId {
  const s = String(raw || '').trim().toLowerCase()
  if (s === 'host-pack' || s === 'host') return 'host-pack'
  if (s === 'industry' || s === 'mod') return 'industry'
  if (s === 'done' || s === 'finish') return 'done'
  return 'welcome'
}
