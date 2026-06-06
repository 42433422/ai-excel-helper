/**
 * 每个工作流员工对应的「单位数据库 / 主工作台」入口。
 *
 * 用于工位特写卡片的「查看 [对应数据库]」快捷链接：员工头顶显示工时与已处理数，
 * 卡片底部跳到该员工实际操作的核心表格 / 工作台页面。
 *
 * Mod manifest 声明的扩展员工没有静态映射（运行时不知道扩展往哪里跳），
 * 默认回退到 `chat`（智能对话），由扩展自身负责在副窗里提供更专属的入口。
 */

export type WorkflowEmployeeDatabaseLink = {
  empId: string
  /** vue-router name */
  routeName: string
  /** 可选 query，如数据来源页预选微信本地库 */
  query?: Record<string, string>
  /** 按钮文案（动作语气，如「查看出货记录」） */
  label: string
  /** 简短说明，作为按钮 title / aria 描述 */
  description: string
}

const CORE_LINKS: Record<string, WorkflowEmployeeDatabaseLink> = {
  label_print: {
    empId: 'label_print',
    routeName: 'print',
    label: '查看标签打印工作台',
    description: '与标签打印 AI 员工对应的打印模板与打印任务工作台',
  },
  shipment_mgmt: {
    empId: 'shipment_mgmt',
    routeName: 'shipment-records',
    label: '查看出货记录数据库',
    description: '出货管理 AI 员工写入的出货记录与审计数据',
  },
  receipt_confirm: {
    empId: 'receipt_confirm',
    routeName: 'customers',
    label: '查看客户管理数据库',
    description: '收货确认 AI 员工跟进的客户业务进程与历史反馈',
  },
  wechat_msg: {
    empId: 'wechat_msg',
    routeName: 'data-sources',
    query: { source: 'wechat_local_db' },
    label: '查看微信联系人',
    description: '微信消息处理 AI 员工监控的星标联系人与会话（数据来源 · 微信本地库）',
  },
  wechat_phone: {
    empId: 'wechat_phone',
    routeName: 'chat',
    label: '回到智能对话查看通话进度',
    description: '微信电话对接业务员的状态轮询与任务面板均在对话页',
  },
  real_phone: {
    empId: 'real_phone',
    routeName: 'chat',
    label: '回到智能对话查看通话进度',
    description: '真实电话业务员的 ADB 链路状态与任务面板均在对话页',
  },
}

const FALLBACK_LINK: WorkflowEmployeeDatabaseLink = {
  empId: '',
  routeName: 'chat',
  label: '回到智能对话',
  description: '此员工由扩展提供，专属数据由所在扩展副窗维护',
}

export function databaseLinkForEmployee(empId: string): WorkflowEmployeeDatabaseLink {
  const core = CORE_LINKS[empId]
  if (core) return core
  return { ...FALLBACK_LINK, empId }
}
