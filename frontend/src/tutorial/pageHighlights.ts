import type { TutorialPageHighlight } from './types'

/** 宿主页内高亮注册表（按 vue-router name）；侧栏不可见的路由（如 print）不收录 */
export const HOST_PAGE_HIGHLIGHTS: Record<string, TutorialPageHighlight[]> = {
  chat: [
    {
      idSuffix: 'quick',
      title: '智能对话 · 快捷话术区',
      description: '顶部横排按钮：一键填入并发送常见指令（如查价、开单相关话术），减少重复输入',
      targetSelector: '#view-chat .quick-actions',
    },
    {
      idSuffix: 'thread',
      title: '智能对话 · 对话与任务区',
      description: '左侧为消息流：用户与助手气泡',
      targetSelector: '#view-chat .chat-container',
    },
    {
      idSuffix: 'input',
      title: '智能对话 · 输入与副窗',
      description: '底部工具栏：新对话、历史、分析 Excel、专业模式意图体验、星标微信自动刷…',
      targetSelector: '#view-chat .input-area',
    },
  ],
  products: [
    {
      idSuffix: 'header',
      title: '产品管理 · 顶栏按钮',
      description: '标题右侧：导出价格表（按当前所选单位）、勾选表格后批量删除、添加产品（打开录…',
      targetSelector: '#view-products .page-header',
    },
    {
      idSuffix: 'filters',
      title: '产品管理 · 筛选与搜索',
      description: '先选「产品单位」再加载该单位产品',
      targetSelector: '#view-products .search-box',
    },
    {
      idSuffix: 'table',
      title: '产品管理 · 表格与弹窗',
      description: '表格左侧多选',
      targetSelector: '#view-products .card',
    },
  ],
  'materials-list': [
    {
      idSuffix: 'header',
      title: '原材料列表 · 顶栏',
      description: '标题右侧：导出 Excel、批量删除（需先勾选表格）、添加原材料',
      targetSelector: '#view-materials .page-header',
    },
    {
      idSuffix: 'search',
      title: '原材料列表 · 搜索与分类',
      description: '搜索框过滤名称等',
      targetSelector: '#view-materials .search-box',
    },
    {
      idSuffix: 'table',
      title: '原材料列表 · 表格',
      description: '表格含编码、名称、分类、库存（低于安全库存会标红）、价格、供应商等',
      targetSelector: '#view-materials .card',
    },
  ],
  materials: [
    {
      idSuffix: 'header',
      title: '原材料仓库 · 顶栏',
      description: '仓库视角下同页：导出、批量删除、添加',
      targetSelector: '#view-materials .page-header',
    },
    {
      idSuffix: 'search',
      title: '原材料仓库 · 筛选',
      description: '搜索与分类、导出模板',
      targetSelector: '#view-materials .search-box',
    },
    {
      idSuffix: 'table',
      title: '原材料仓库 · 表格与表单',
      description: '在表格中改库存、单价等',
      targetSelector: '#view-materials .card',
    },
  ],
  'traditional-mode': [
    {
      idSuffix: 'main',
      title: '表格模式 · 主工作区',
      description: '以表格方式浏览与编辑业务数据',
      targetSelector: '#view-traditional-mode .page-content',
    },
  ],
  'business-docking': [
    {
      idSuffix: 'upload',
      title: '业务对接 · 上传与提取',
      description: '在此选择 Excel、点「上传并提取」，再选 Sheet',
      targetSelector: '#view-business-docking .dock-card',
    },
    {
      idSuffix: 'results',
      title: '业务对接 · 字段、网格与保留模板',
      description: '提取后：左侧字段列表、右侧网格预览核对映射',
      targetSelector: '#view-business-docking [data-tutorial-anchor="business-dock-results"]',
    },
  ],
  orders: [
    {
      idSuffix: 'header',
      title: '订单管理 · 顶栏',
      description: '新建、导出、筛选等主操作通常在顶栏',
      targetSelector: '#view-orders .page-header',
    },
    {
      idSuffix: 'table',
      title: '订单管理 · 列表',
      description: '表格展示历史单据',
      targetSelector: '#view-orders .card',
    },
  ],
  'shipment-records': [
    {
      idSuffix: 'header',
      title: '出货记录 · 查询条件',
      description: '选择购买单位、打印状态筛选、出货记录模板，点「查看记录」拉数据',
      targetSelector: '#view-shipment-records .page-header',
    },
    {
      idSuffix: 'table',
      title: '出货记录 · 结果表',
      description: '表格按所选模板列展示',
      targetSelector: '#view-shipment-records .card',
    },
  ],
  customers: [
    {
      idSuffix: 'header',
      title: '客户管理 · 顶栏与导入导出',
      description: '选导出模板、上传 Excel 更新购买单位、导出按钮、批量删除（需先勾选）',
      targetSelector: '#view-customers .page-header',
    },
    {
      idSuffix: 'stats',
      title: '客户管理 · 统计',
      description: '数字卡片展示客户总数等汇总指标（以当前页统计为准）',
      targetSelector: '#view-customers .stat-cards',
    },
    {
      idSuffix: 'table',
      title: '客户管理 · 客户表',
      description: '表格多选、触底加载更多',
      targetSelector: '#view-customers .card',
    },
  ],
  'data-sources': [
    {
      idSuffix: 'wechat-search',
      title: '微信联系人 · 搜索与星标',
      description: '本卡：刷新联系人/聊天记录缓存 → 搜索昵称备注微信号 → 对结果「添加星标…',
      targetSelector: '#view-data-sources [data-tutorial-id="wechat-search-star"]',
    },
    {
      idSuffix: 'wechat-starred',
      title: '微信联系人 · 星标列表',
      description: '星标列表：类型筛选、关键词过滤、一键解除星标',
      targetSelector: '#view-data-sources [data-tutorial-id="wechat-starred-list"]',
    },
  ],
  'printer-list': [
    {
      idSuffix: 'header',
      title: '打印机列表 · 顶栏',
      description: '标题旁「刷新」重新检测本机打印机列表',
      targetSelector: '#view-printer-list .page-header',
    },
    {
      idSuffix: 'bind',
      title: '打印机列表 · 分类绑定',
      description: '上方两格分别绑定「发货单打印机」与「标签打印机」',
      targetSelector: '#view-printer-list .page-content > .card:nth-child(2)',
    },
    {
      idSuffix: 'table',
      title: '打印机列表 · 全部设备表',
      description: '表格列出检测到的打印机，可多选后一键设为发货单或标签默认机',
      targetSelector: '#view-printer-list .page-content > .card:nth-child(3)',
    },
  ],
  'template-preview': [
    {
      idSuffix: 'header',
      title: '模板库 · 说明与规则',
      description: '按业务范围管理 Excel/标签导出模板',
      targetSelector: '#view-template-preview .page-header',
    },
    {
      idSuffix: 'toolbar',
      title: '模板库 · 范围与操作',
      description: '横排按钮切换业务范围、刷新列表、创建模板',
      targetSelector: '#view-template-preview .template-preview-toolbar',
    },
    {
      idSuffix: 'grid-tool',
      title: '模板库 · 网格映射工具',
      description: '上传 Excel 可提取字段并查看结果，用于对照或辅助配置模板结构',
      targetSelector: '#view-template-preview .grid-tool-card',
    },
    {
      idSuffix: 'cards',
      title: '模板库 · 模板卡片',
      description: '各卡片展示预览、词条与操作按钮（预览/编辑/删除等，以当前模板类型为准）',
      targetSelector: '#view-template-preview .template-preview-section',
    },
  ],
  settings: [
    {
      idSuffix: 'header',
      title: '系统设置 · 总览',
      description: '多卡片分区配置意图包、基本项与导航等',
      targetSelector: '#view-settings .settings-page__hero',
    },
    {
      idSuffix: 'intent',
      title: '系统设置 · AI 意图能力',
      description: '只读展示当前行业下各意图领域与示例词',
      targetSelector: '[data-tutorial-id="settings-intent"]',
    },
    {
      idSuffix: 'basic',
      title: '系统设置 · 基本与其它卡片',
      description: '「基本设置」含助手名、AI 模式等',
      targetSelector: '[data-tutorial-id="settings-basic"]',
    },
  ],
  tools: [
    {
      idSuffix: 'header',
      title: '工具表 · 筛选',
      description: '顶栏关键词搜索 + 业务分类下拉，用于在大量内置工具中快速定位',
      targetSelector: '#view-tools .page-header',
    },
    {
      idSuffix: 'grid',
      title: '工具表 · 工具卡片',
      description: '每张卡展示分类、名称、说明',
      targetSelector: '#view-tools .tools-container',
    },
  ],
  'approval-workspace': [
    {
      idSuffix: 'main',
      title: '审批中心 · 工作区',
      description: '在此处理待办审批、查看流程状态',
      targetSelector: '#view-approval-workspace .page-content, #view-approval-hub .page-content',
    },
  ],
  'approval-hub': [
    {
      idSuffix: 'main',
      title: '审批中心 · 工作区',
      description: '在此处理待办审批、查看流程状态',
      targetSelector: '#view-approval-hub .page-content',
    },
  ],
  'other-tools': [
    {
      idSuffix: 'workflow',
      title: '员工工作流管理 · 流程与员工',
      description: '本卡说明原版与 Mod 扩展的统一管理入口，并可进入「流程全景」查看执行逻辑…',
      targetSelector: '#view-other-tools .page-content > .card:nth-child(2)',
    },
  ],
  'workflow-employee-space': [
    {
      idSuffix: 'main',
      title: '员工空间 · 概览',
      description: '查看与管理工作流员工相关入口',
      targetSelector: '#view-workflow-employee-space .page-content',
    },
  ],
  'ai-ecosystem': [
    {
      idSuffix: 'title',
      title: 'AI生态 · 应用入口',
      description: '此处为独立子应用启动区',
      targetSelector: '#view-ai-ecosystem .ecosystem-home-title',
    },
    {
      idSuffix: 'launcher',
      title: 'AI生态 · 启动器',
      description: '进入子应用后，顶栏一般可返回本列表',
      targetSelector: '#view-ai-ecosystem .launcher-grid',
    },
  ],
}

export function mergePageHighlights(
  base: Record<string, TutorialPageHighlight[]>,
  extra: Record<string, TutorialPageHighlight[]>,
): Record<string, TutorialPageHighlight[]> {
  const out: Record<string, TutorialPageHighlight[]> = { ...base }
  for (const [route, rows] of Object.entries(extra || {})) {
    const prev = out[route] ? [...out[route]] : []
    const byId = new Map(prev.map((r) => [r.idSuffix, r]))
    for (const row of rows || []) {
      byId.set(row.idSuffix, row)
    }
    out[route] = Array.from(byId.values())
  }
  return out
}
