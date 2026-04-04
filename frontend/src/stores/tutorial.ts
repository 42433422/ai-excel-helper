import { computed, nextTick, ref } from 'vue'
import { defineStore } from 'pinia'
import router from '@/router'

export type TutorialActionType = 'click' | 'observe'

/** 新手教程路线：基础为现有全流程；进阶为深化能力（可逐步扩充） */
export type TutorialTrackId = 'basic' | 'advanced'

const PRO_INTENT_EXPERIENCE_STORAGE_KEY = 'xcagi_pro_intent_experience'
type ProIntentLocalSnapshot = false | string | null

export interface TutorialStep {
  id: string
  title: string
  description: string
  targetSelector: string
  /** 高亮区域（默认同 targetSelector；多匹配时可用更外层容器） */
  highlightSelector?: string
  actionType: TutorialActionType
  routeName?: string
  assistantTab?: string
  excludeInPro?: boolean
  /** 为 true 时 click 步骤仍允许点卡片「下一步」（避免副窗未展开等情况下卡死；核心操作步骤勿开） */
  allowCardNext?: boolean
  /** 为 true 时找不到目标不自动跳步，占位并轮询 DOM（路由切换后异步页面未挂载，如进阶「页内功能」步） */
  noAutoSkipWhenMissing?: boolean
}

type TutorialTestStatus = 'pending' | 'passed' | 'skipped'
type TutorialReturnContext = {
  routeName?: string
  assistantOpen?: boolean
  assistantTab?: string
  assistantState?: Record<string, unknown> | null
}

const createStep = (step: TutorialStep): TutorialStep => ({
  ...step,
  // 教程默认只覆盖普通版核心能力，避免暴露专业版入口。
  excludeInPro: step.excludeInPro ?? true
})

const tutorialStepsBasic: TutorialStep[] = [
  createStep({
    id: 'chat-entry',
    title: '智能对话入口',
    description: '请点击左侧「智能对话」，从这里进入日常业务主流程。',
    targetSelector: '.sidebar .menu-item[data-view="chat"]',
    actionType: 'click',
    routeName: 'chat'
  }),
  createStep({
    id: 'starter-pack-open-tab',
    title: '打开「新手对话包」',
    description:
      '请先点击副窗顶部的「新手对话包」标签，切换到对话包列表后，再按后面步骤逐条点选示例话术。若副窗已展开或暂时点不到，也可点本卡片「下一步」继续。',
    targetSelector:
      '[data-tutorial-spotlight="assistant-panel"] .assistant-tab[data-tutorial-id="tab-starterPack"]',
    actionType: 'click',
    routeName: 'chat',
    // 只打开副窗并停在「推送」等默认区，避免预先切到对话包导致用户看不到「先点标签」；标签栏始终可见。
    assistantTab: 'push',
    allowCardNext: true
  }),
  createStep({
    id: 'starter-pack-demo-1-pick',
    title: '示例一 · 点选话术',
    description: '请点击第一条「查产品价格」示例。系统会跳到智能对话并把话术填入输入框。',
    targetSelector: '.assistant-body-starter .starter-pack-list > .starter-pack-item:nth-child(1)',
    actionType: 'click',
    routeName: 'chat',
    assistantTab: 'starterPack'
  }),
  createStep({
    id: 'starter-pack-demo-1-send',
    title: '示例一 · 发送',
    description: '请确认输入框内容无误后，点击下方「发送」按钮，把话术发给助手。',
    targetSelector: '#sendMessageBtn',
    actionType: 'click',
    routeName: 'chat'
  }),
  createStep({
    id: 'starter-pack-demo-1-view',
    title: '示例一 · 查看产品副窗',
    description:
      '本条是查价示例：发送后助手会打开「协助副窗」并带入查询结果。请在右侧副窗中查看命中产品、价格与「保存修改」等入口，而不是只看左侧聊天列表。确认后点击「下一步」。',
    targetSelector: '[data-tutorial-assistant-body]',
    highlightSelector: '[data-tutorial-assistant-body]',
    actionType: 'observe',
    routeName: 'chat',
    assistantTab: 'assistant'
  }),
  createStep({
    id: 'starter-pack-demo-2-pick',
    title: '示例二 · 点选话术',
    description: '请回到副窗「新手对话包」，点击第二条「生成发货单单产品」示例。',
    targetSelector: '.assistant-body-starter .starter-pack-list > .starter-pack-item:nth-child(2)',
    actionType: 'click',
    routeName: 'chat',
    assistantTab: 'starterPack'
  }),
  createStep({
    id: 'starter-pack-demo-2-send',
    title: '示例二 · 发送',
    description: '点击下方「发送」，观察单产品发货单类话术如何被处理。',
    targetSelector: '#sendMessageBtn',
    actionType: 'click',
    routeName: 'chat'
  }),
  createStep({
    id: 'starter-pack-demo-3-pick',
    title: '示例三 · 点选话术',
    description:
      '进入本步后，教程会自动打开副窗并切到「新手对话包」。请点击第三条「增加发货单」示例（若未展开请稍候半秒待界面就绪）。',
    targetSelector: '.assistant-body-starter .starter-pack-list > .starter-pack-item:nth-child(3)',
    actionType: 'click',
    routeName: 'chat',
    assistantTab: 'starterPack'
  }),
  createStep({
    id: 'starter-pack-demo-3-send',
    title: '示例三 · 发送',
    description:
      '点选示例后副窗会自动收起。请点击「发送」，助手会在右侧「当前任务」生成发货单预览（与左侧对话摘要配合查看）。',
    targetSelector: '#sendMessageBtn',
    actionType: 'click',
    routeName: 'chat'
  }),
  createStep({
    id: 'starter-pack-demo-3-confirm-task',
    title: '示例三 · 确认任务',
    description:
      '「增加发货单」与生成类示例相同：主操作在右侧任务面板。请浏览预览与订单编号后，点击任务卡片上的绿色「确认执行」完成本步（勿以左侧聊天区为主）。',
    targetSelector: '#taskPanel button[data-action="confirm-task"]',
    highlightSelector: '#taskPanel button[data-action="confirm-task"]',
    actionType: 'click',
    routeName: 'chat'
  }),
  createStep({
    id: 'starter-pack-demo-3-start-print',
    title: '示例三 · 开始打印',
    description:
      '执行成功后，任务卡片会出现「下载发货单」与绿色「开始打印」。请点击「开始打印」走一遍打印流程（与对话中发送「开始打印」效果相同）。',
    targetSelector: '#taskPanel button[data-action="start-print"]',
    highlightSelector: '#taskPanel button[data-action="start-print"]',
    actionType: 'click',
    routeName: 'chat'
  }),
  createStep({
    id: 'tab-push',
    title: '推送与微信消息',
    description:
      '请点击副窗顶部的「推送」标签。开启「星标聊天自动刷新」后，星标联系人的新微信消息会在此列表显示，便于快速查看提醒与待办。',
    targetSelector:
      '[data-tutorial-spotlight="assistant-panel"] .assistant-tab[data-tutorial-id="tab-push"]',
    actionType: 'click',
    routeName: 'chat',
    assistantTab: 'push'
  }),
  createStep({
    id: 'wechat-contacts-stars',
    title: '微信与星标联系人',
    description:
      '请点击左侧「微信联系人列表」进入联系人页。在列表中把常用客户设为星标；再在智能对话开启「星标聊天自动刷新」后，星标联系人的新微信消息会出现在副窗「推送」里。',
    targetSelector: '.sidebar .menu-item[data-view="wechat-contacts"]',
    actionType: 'click',
    routeName: 'chat',
    assistantTab: 'push'
  }),
  createStep({
    id: 'wechat-starred-list-intro',
    title: '星标联系人列表',
    description:
      '下方卡片为「星标联系人列表」：可筛选类型（全部/联系人/群聊）、在列表中搜索，或对每条记录使用「查看聊天记录」「刷新聊天记录」「编辑」「删除」。教程中无需改数据，浏览后点「下一步」回到后续副窗介绍。',
    targetSelector: '#view-wechat-contacts .card[data-tutorial-id="wechat-starred-list"]',
    highlightSelector: '#view-wechat-contacts .card[data-tutorial-id="wechat-starred-list"]',
    actionType: 'observe',
    routeName: 'wechat-contacts'
  }),
  createStep({
    id: 'chat-star-auto-refresh',
    title: '星标聊天自动刷新',
    description:
      '请先点击左侧「智能对话」回到本页（若已在对话页可忽略）。然后勾选输入区上方「星标聊天自动刷新（1分钟）」：开启后系统会按间隔拉取星标联系人的新消息，副窗「推送」中才会出现对应提醒。',
    targetSelector: '#view-chat label[data-tutorial-id="star-auto-refresh-toggle"]',
    highlightSelector: '#view-chat label[data-tutorial-id="star-auto-refresh-toggle"]',
    actionType: 'click',
    routeName: 'chat'
  }),
  createStep({
    id: 'chat-excel-analyze-toolbar',
    title: '分析 Excel',
    description:
      '微信与星标相关流程后，可在智能对话输入区上方使用「分析Excel」：上传工作表以分析词条与数据。教程中无需真的选文件；可点按钮了解入口，或直接点本卡片「下一步」继续。',
    targetSelector: '#view-chat button[data-tutorial-id="toolbar-excel-analyze"]',
    highlightSelector: '#view-chat button[data-tutorial-id="toolbar-excel-analyze"]',
    actionType: 'click',
    allowCardNext: true,
    routeName: 'chat'
  }),
  createStep({
    id: 'chat-intent-pro-experience',
    title: 'AI意图体验（对话开关）',
    description:
      '工具栏上的「专业模式AI意图体验」用于增强对话里 AI 意图识别与回复方式（名称指对话侧体验，与付费「专业版」业务模块不同）。本步仅作介绍：请点卡片「下一步」继续；若您想试用，可自行勾选开关，教程结束或退出后会恢复进入教程前的开关状态。',
    targetSelector: '#view-chat label[data-tutorial-id="intent-pro-experience-toggle"]',
    highlightSelector: '#view-chat label[data-tutorial-id="intent-pro-experience-toggle"]',
    actionType: 'observe',
    routeName: 'chat'
  }),
  createStep({
    id: 'tab-assistant',
    title: '产品协助',
    description: '请点击「协助副窗」，用于产品查询与资料修正。',
    targetSelector:
      '[data-tutorial-spotlight="assistant-panel"] .assistant-tab[data-tutorial-id="tab-assistant"]',
    actionType: 'click',
    routeName: 'chat',
    assistantTab: 'assistant'
  }),
  createStep({
    id: 'tab-one-click',
    title: '一键托管',
    description: '请点击「一键托管」，在「工作流员工选择」中用开关启用需要的 AI 员工。',
    targetSelector:
      '[data-tutorial-spotlight="assistant-panel"] .assistant-tab[data-tutorial-id="tab-one-click"]',
    actionType: 'click',
    routeName: 'chat',
    assistantTab: 'oneClick'
  }),
  createStep({
    id: 'tab-lobster',
    title: '龙虾托管',
    description: '请点击「龙虾托管」，同样可通过开关选择参与托管的 AI 员工。',
    targetSelector:
      '[data-tutorial-spotlight="assistant-panel"] .assistant-tab[data-tutorial-id="tab-lobster"]',
    actionType: 'click',
    routeName: 'chat',
    assistantTab: 'lobster'
  }),
  createStep({
    id: 'settings-entry',
    title: '系统设置',
    description: '请点击左侧「系统设置」，确认配置入口可正常访问。',
    targetSelector: '.sidebar .menu-item[data-view="settings"]',
    actionType: 'click',
    routeName: 'settings'
  }),
  createStep({
    id: 'sidebar-nav',
    title: '菜单总览',
    description: '最后浏览左侧菜单分区，确认常用入口可见且布局正常。',
    targetSelector: '.sidebar .sidebar-menu',
    actionType: 'observe'
  })
]

/** 进阶侧栏入口：不强制 routeName，避免从上一菜单页被拉回 chat；高亮仍指向 .sidebar .menu-item[data-view] */
const advancedSidebarNavStep = (
  view: string,
  title: string,
  description: string
): TutorialStep =>
  createStep({
    id: `advanced-nav-${view.replace(/[^a-z0-9-]/gi, '-')}`,
    title,
    description,
    targetSelector: `.sidebar .menu-item[data-view="${view}"]`,
    actionType: 'click',
    allowCardNext: true,
    excludeInPro: false
  })

/** 进入对应路由后，高亮该页主内容区并介绍页内按钮/表格等（先由 routeName 切页再量 DOM） */
const advancedPageFeaturesStep = (
  idSuffix: string,
  routeName: string,
  title: string,
  description: string,
  targetSelector: string
): TutorialStep =>
  createStep({
    id: `advanced-page-${idSuffix}`,
    title,
    description,
    targetSelector,
    highlightSelector: targetSelector,
    actionType: 'observe',
    routeName,
    excludeInPro: false,
    allowCardNext: true,
    noAutoSkipWhenMissing: true
  })

/** 进阶教程：每个菜单先认入口，再进页介绍页内功能（与基础教程互补） */
const tutorialStepsAdvanced: TutorialStep[] = [
  createStep({
    id: 'advanced-sidebar-scan',
    title: '侧栏菜单 · 怎么用这条路线',
    description:
      '先点侧栏进入模块，再在同一页用多个高亮分区依次介绍顶栏、筛选、表格等（洞口落在对应区域，避免整块主区看起来像「还在讲侧栏」）。任一步可点卡片「下一步」略过。',
    targetSelector: '.sidebar .sidebar-menu',
    actionType: 'observe',
    routeName: 'chat',
    excludeInPro: false
  }),
  advancedSidebarNavStep(
    'chat',
    '智能对话',
    '【入口】主工作台：查价、发货单、任务与打印等多从这里开始；右侧常有「当前任务」，顶栏可开副窗。请点击「智能对话」进入（或点卡片「下一步」）。'
  ),
  advancedPageFeaturesStep(
    'chat-quick',
    'chat',
    '智能对话 · 快捷话术区',
    '顶部横排按钮：一键填入并发送常见指令（如查价、开单相关话术），减少重复输入。点选后内容会进下方输入框，可再改再发。',
    '#view-chat .quick-actions'
  ),
  advancedPageFeaturesStep(
    'chat-thread',
    'chat',
    '智能对话 · 对话与任务区',
    '左侧为消息流：用户与助手气泡；AI 长回复可收起/展开，带发货单下载等按钮。右侧为「当前任务」：展示助手识别的任务卡片、确认执行、开始打印等主操作。',
    '#view-chat .chat-container'
  ),
  advancedPageFeaturesStep(
    'chat-input',
    'chat',
    '智能对话 · 输入与副窗',
    '底部工具栏：新对话、历史、分析 Excel、专业模式意图体验、星标微信自动刷新；中间输入框与发送。顶栏右侧「副窗」打开推送、产品查询、对话包与教程。',
    '#view-chat .input-area'
  ),
  advancedSidebarNavStep(
    'products',
    '产品管理',
    '【入口】维护产品档案，供对话查价、开单、打标签引用。请点击「产品管理」。'
  ),
  advancedPageFeaturesStep(
    'products-header',
    'products',
    '产品管理 · 顶栏按钮',
    '标题右侧：导出价格表（按当前所选单位）、勾选表格后批量删除、添加产品（打开录入弹窗）。这是本页增删导出的主入口。',
    '#view-products .page-header'
  ),
  advancedPageFeaturesStep(
    'products-filters',
    'products',
    '产品管理 · 筛选与搜索',
    '先选「产品单位」再加载该单位产品；可选导出用模板；搜索框按型号/名称过滤列表。与顶栏导出配合使用。',
    '#view-products .search-box'
  ),
  advancedPageFeaturesStep(
    'products-table',
    'products',
    '产品管理 · 表格与弹窗',
    '表格左侧多选；行尾编辑/删除；列表过长时向下滚动自动加载更多。添加/编辑在弹窗中填写型号、名称、规格、价格等。',
    '#view-products .card'
  ),
  advancedSidebarNavStep(
    'materials-list',
    '原材料列表',
    '【入口】列表视角浏览原材料条目。请点击「原材料列表」。'
  ),
  advancedPageFeaturesStep(
    'materials-list-header',
    'materials-list',
    '原材料列表 · 顶栏',
    '标题右侧：导出 Excel、批量删除（需先勾选表格）、添加原材料。列表模式与仓库模式共用此顶栏逻辑。',
    '#view-materials .page-header'
  ),
  advancedPageFeaturesStep(
    'materials-list-search',
    'materials-list',
    '原材料列表 · 搜索与分类',
    '搜索框过滤名称等；分类下拉筛选；选择导出模板。若出现黄色「库存预警」条，会列出低于安全库存的物料摘要。',
    '#view-materials .search-box'
  ),
  advancedPageFeaturesStep(
    'materials-list-table',
    'materials-list',
    '原材料列表 · 表格',
    '表格含编码、名称、分类、库存（低于安全库存会标红）、价格、供应商等；多选后批量删除，行内编辑/删除，触底加载更多。',
    '#view-materials .card'
  ),
  advancedSidebarNavStep(
    'materials',
    '原材料仓库',
    '【入口】仓储维度管理库存与原材料。请点击「原材料仓库」。'
  ),
  advancedPageFeaturesStep(
    'materials-header',
    'materials',
    '原材料仓库 · 顶栏',
    '仓库视角下同页：导出、批量删除、添加。此处维护入库视角的原材料主数据与库存字段。',
    '#view-materials .page-header'
  ),
  advancedPageFeaturesStep(
    'materials-search',
    'materials',
    '原材料仓库 · 筛选',
    '搜索与分类、导出模板；关注预警条中的低库存提示，及时补货或改最小库存。',
    '#view-materials .search-box'
  ),
  advancedPageFeaturesStep(
    'materials-table',
    'materials',
    '原材料仓库 · 表格与表单',
    '在表格中改库存、单价等；弹窗内维护编码、名称、分类、规格、单位、数量、供应商等完整字段。',
    '#view-materials .card'
  ),
  advancedSidebarNavStep(
    'business-docking',
    '业务对接',
    '【入口】上传旧业务 Excel，做网格映射与模板保留。请点击「业务对接」。'
  ),
  advancedPageFeaturesStep(
    'business-dock-upload',
    'business-docking',
    '业务对接 · 上传与提取',
    '在此选择 Excel、点「上传并提取」，再选 Sheet。提取成功后会显示文件名、字段数等摘要。',
    '#view-business-docking .dock-card'
  ),
  advancedPageFeaturesStep(
    'business-dock-results',
    'business-docking',
    '业务对接 · 字段、网格与保留模板',
    '提取后：左侧字段列表、右侧网格预览核对映射；其下「保留模板」可新增或替换同业务范围模板。未提取时本区为占位说明，可先点「下一步」。',
    '#view-business-docking [data-tutorial-anchor="business-dock-results"]'
  ),
  advancedSidebarNavStep(
    'shipment-records',
    '出货记录',
    '【入口】按单位与模板查历史出货。请点击「出货记录」。'
  ),
  advancedPageFeaturesStep(
    'shipment-header',
    'shipment-records',
    '出货记录 · 查询条件',
    '选择购买单位、打印状态筛选、出货记录模板，点「查看记录」拉数据；条件齐后可「导出 Excel」。',
    '#view-shipment-records .page-header'
  ),
  advancedPageFeaturesStep(
    'shipment-table',
    'shipment-records',
    '出货记录 · 结果表',
    '表格按所选模板列展示；行内可有打印、查看等操作（以当前模板列为准）。未加载前会提示先选单位。',
    '#view-shipment-records .card'
  ),
  advancedSidebarNavStep(
    'customers',
    '客户管理',
    '【入口】客户主数据与导入导出。请点击「客户管理」。'
  ),
  advancedPageFeaturesStep(
    'customers-header',
    'customers',
    '客户管理 · 顶栏与导入导出',
    '选导出模板、上传 Excel 更新购买单位、导出按钮、批量删除（需先勾选）。图标按钮为导入/导出快捷入口。',
    '#view-customers .page-header'
  ),
  advancedPageFeaturesStep(
    'customers-stats',
    'customers',
    '客户管理 · 统计',
    '数字卡片展示客户总数等汇总指标（以当前页统计为准）。',
    '#view-customers .stat-cards'
  ),
  advancedPageFeaturesStep(
    'customers-table',
    'customers',
    '客户管理 · 客户表',
    '表格多选、触底加载更多；行内维护客户资料列。与微信联系人数据互补使用。',
    '#view-customers .card'
  ),
  advancedSidebarNavStep(
    'wechat-contacts',
    '微信联系人列表',
    '【入口】微信缓存、搜索、星标与列表维护。请点击「微信联系人列表」。'
  ),
  advancedPageFeaturesStep(
    'wechat-search-card',
    'wechat-contacts',
    '微信联系人 · 搜索与星标',
    '本卡：刷新联系人/聊天记录缓存 → 搜索昵称备注微信号 → 对结果「添加星标」。依赖本地解密缓存，先刷新再搜更准。',
    '#view-wechat-contacts .page-content .card:first-of-type'
  ),
  advancedPageFeaturesStep(
    'wechat-starred-card',
    'wechat-contacts',
    '微信联系人 · 星标列表',
    '星标列表：类型筛选、关键词过滤、一键解除星标；每行可查看/刷新聊天记录、编辑、删除。聊天记录在弹窗中只读展示。',
    '#view-wechat-contacts .card[data-tutorial-id="wechat-starred-list"]'
  ),
  advancedSidebarNavStep(
    'print',
    '标签打印',
    '【入口】选产品与数量打标签。请点击「标签打印」。'
  ),
  advancedPageFeaturesStep(
    'print-header',
    'print',
    '标签打印 · 页面说明',
    '本页用于按产品型号与数量生成标签打印任务；具体走纸与驱动依赖本机已绑定的标签打印机。',
    '#view-print .page-header'
  ),
  advancedPageFeaturesStep(
    'print-form',
    'print',
    '标签打印 · 生成标签',
    '在卡片中选产品型号、填写数量，点「打印标签」。下方灰字为打印机检测状态；异常时请到「打印机列表」检查绑定。',
    '#view-print .card'
  ),
  advancedSidebarNavStep(
    'printer-list',
    '打印机列表',
    '【入口】发货单打印机与标签打印机绑定。请点击「打印机列表」。'
  ),
  advancedPageFeaturesStep(
    'printer-header',
    'printer-list',
    '打印机列表 · 顶栏',
    '标题旁「刷新」重新检测本机打印机列表；绑定或列表变更后建议先刷新再选。',
    '#view-printer-list .page-header'
  ),
  advancedPageFeaturesStep(
    'printer-bind',
    'printer-list',
    '打印机列表 · 分类绑定',
    '上方两格分别绑定「发货单打印机」与「标签打印机」；下拉选设备并查看连接状态，再点保存（下方还有「全部打印机」表可批量操作）。',
    '#view-printer-list .page-content > .card:nth-child(2)'
  ),
  advancedPageFeaturesStep(
    'printer-table',
    'printer-list',
    '打印机列表 · 全部设备表',
    '表格列出检测到的打印机，可多选后一键设为发货单或标签默认机；与上方分类绑定配合使用。',
    '#view-printer-list .page-content > .card:nth-child(3)'
  ),
  advancedSidebarNavStep(
    'template-preview',
    '模板库',
    '【入口】按业务范围管理 Excel 导出模板。请点击「模板库」。'
  ),
  advancedPageFeaturesStep(
    'template-header',
    'template-preview',
    '模板库 · 说明与规则',
    '按业务范围管理 Excel/标签导出模板；替换模板时会校验必备词条完整性（见下方黄色提示）。',
    '#view-template-preview .page-header'
  ),
  advancedPageFeaturesStep(
    'template-toolbar',
    'template-preview',
    '模板库 · 范围与操作',
    '横排按钮切换业务范围、刷新列表、创建模板；与下方网格工具、模板卡片列表联动。',
    '#view-template-preview .template-preview-toolbar'
  ),
  advancedPageFeaturesStep(
    'template-grid-tool',
    'template-preview',
    '模板库 · 网格映射工具',
    '上传 Excel 可提取字段并查看结果，用于对照或辅助配置模板结构。',
    '#view-template-preview .grid-tool-card'
  ),
  advancedPageFeaturesStep(
    'template-cards',
    'template-preview',
    '模板库 · 模板卡片',
    '各卡片展示预览、词条与操作按钮（预览/编辑/删除等，以当前模板类型为准）。若当前范围暂无模板，列表区可能为空，可点「下一步」。',
    '#view-template-preview .template-preview-section'
  ),
  advancedSidebarNavStep(
    'settings',
    '系统设置',
    '【入口】行业、意图包与其它系统项。请点击「系统设置」。'
  ),
  advancedPageFeaturesStep(
    'settings-header',
    'settings',
    '系统设置 · 总览',
    '多卡片分区配置行业、意图包、基本项与导航等；不熟时建议只浏览，避免在生产环境误改关键项。',
    '#view-settings .page-header'
  ),
  advancedPageFeaturesStep(
    'settings-industry',
    'settings',
    '系统设置 · 行业配置',
    '切换当前行业会影响 AI 意图识别与业务字段文案；下方显示该行业主单位等摘要。',
    '#view-settings .page-content > .card:nth-child(2)'
  ),
  advancedPageFeaturesStep(
    'settings-intent',
    'settings',
    '系统设置 · AI 意图包',
    '按包开关增强对特定行业用语的理解；需先选好行业后再逐项评估是否开启。',
    '#view-settings .page-content > .card:nth-child(3)'
  ),
  advancedPageFeaturesStep(
    'settings-basic',
    'settings',
    '系统设置 · 基本与其它卡片',
    '「基本设置」含助手名、AI 模式等；其下还有导航自定义、蒸馏版本、关于等卡片，可向下滚动浏览。',
    '#view-settings .page-content > .card:nth-child(4)'
  ),
  advancedSidebarNavStep(
    'tools',
    '工具表',
    '【入口】内置工具目录。请点击「工具表」。'
  ),
  advancedPageFeaturesStep(
    'tools-header',
    'tools',
    '工具表 · 筛选',
    '顶栏关键词搜索 + 业务分类下拉，用于在大量内置工具中快速定位。',
    '#view-tools .page-header'
  ),
  advancedPageFeaturesStep(
    'tools-grid',
    'tools',
    '工具表 · 工具卡片',
    '每张卡展示分类、名称、说明；点「查看」打开详情或执行（能力因工具而异：Excel、OCR、数据库等）。',
    '#view-tools .tools-container'
  ),
  advancedSidebarNavStep(
    'other-tools',
    '员工工作流管理',
    '【入口】原版与各 Mod 工作流相关能力。请点击「员工工作流管理」。'
  ),
  advancedPageFeaturesStep(
    'other-tools-workflow',
    'other-tools',
    '员工工作流管理 · 流程与员工',
    '本卡说明原版与 Mod 扩展的统一管理入口，并可进入「流程全景」查看执行逻辑与过程。',
    '#view-other-tools .page-content > .card:nth-child(2)'
  ),
  advancedSidebarNavStep(
    'ai-ecosystem',
    'AI生态',
    '【入口】独立 AI 子应用入口。请点击「AI生态」。'
  ),
  advancedPageFeaturesStep(
    'ai-eco-title',
    'ai-ecosystem',
    'AI生态 · 应用入口',
    '此处为独立子应用启动区；点下方卡片进入对应生态（如小猫分析、龙虾生态等）。',
    '#view-ai-ecosystem .ecosystem-home-title'
  ),
  advancedPageFeaturesStep(
    'ai-eco-launcher',
    'ai-ecosystem',
    'AI生态 · 启动器',
    '进入子应用后，顶栏一般可返回本列表；子应用内常见上传、工作流、对话与侧栏数据区，以具体应用为准。',
    '#view-ai-ecosystem .launcher-grid'
  )
]

const resolveElementRect = (selector: string) => {
  const el = document.querySelector(selector)
  if (!el) return null
  try {
    el.scrollIntoView({ block: 'nearest', inline: 'nearest' })
  } catch (_e) {
    // ignore
  }
  const rect = el.getBoundingClientRect()
  if (!rect || rect.width <= 0 || rect.height <= 0) return null
  return {
    top: rect.top,
    left: rect.left,
    width: rect.width,
    height: rect.height
  }
}

/** 上一步后若目标尚未挂载，不能用 skipMissingTargets（会向前跳步抵消后退）；用占位矩形保持教程层可见 */
const getTutorialFallbackHighlightRect = () => ({
  top: Math.max(24, window.innerHeight * 0.22),
  left: Math.max(24, window.innerWidth * 0.5 - 160),
  width: 320,
  height: 160
})

/** 确认执行后「开始打印」按钮晚于教程切步才挂载，若按缺节点自动跳过会误跳到「产品协助」 */
const NEVER_AUTO_SKIP_STEP_IDS = new Set(['starter-pack-demo-3-start-print'])

const shouldNeverAutoSkipStep = (step: TutorialStep | null) =>
  !!step && NEVER_AUTO_SKIP_STEP_IDS.has(step.id)

const resolveStepHighlightRect = (step: TutorialStep | null) => {
  if (!step) return null
  const sel = (step.highlightSelector || step.targetSelector).trim()
  const base = resolveElementRect(sel)
  if (!base) return null
  // 大块固定侧栏（副窗、任务面板）再外扩一点，抵消阴影/圆角与亚像素误差
  if (
    sel.includes('assistant-panel') ||
    sel.includes('tutorial-assistant-body') ||
    sel === '#taskPanel'
  ) {
    const pad = 6
    return {
      top: base.top - pad,
      left: base.left - pad,
      width: base.width + pad * 2,
      height: base.height + pad * 2
    }
  }
  // 业务页主内容区略外扩，洞口更易看清表格与工具栏
  if (sel.includes('.page-content') || sel.match(/#view-[a-z0-9-]+\s*$/)) {
    const pad = 4
    return {
      top: base.top - pad,
      left: base.left - pad,
      width: base.width + pad * 2,
      height: base.height + pad * 2
    }
  }
  return base
}

const TUTORIAL_SET_ASSISTANT_TAB = 'xcagi:tutorial:set-assistant-tab'

const dispatchAssistantTab = (tab: string) => {
  const t = String(tab || '').trim()
  if (!t) return
  window.dispatchEvent(
    new CustomEvent(TUTORIAL_SET_ASSISTANT_TAB, {
      detail: { tab: t, open: true }
    })
  )
}

/** 副窗切换 tab 后再量 DOM，否则高亮选择器找不到节点会被整步跳过 */
const afterAssistantTabLayout = (fn: () => void) => {
  nextTick(() => {
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        fn()
      })
    })
  })
}

const currentRouteName = () => String(router.currentRoute.value.name || '')

/**
 * 带 routeName 的步骤必须先切路由再 querySelector。否则从「微信联系人」等页点「下一步」时
 * nextStep 里同步 refreshHighlight 会在 #view-chat 未挂载时量到空节点，误触发自动跳过整步。
 */
const ensureRouteForStepThen = (step: TutorialStep, fn: () => void) => {
  const name = step.routeName?.trim()
  if (!name || currentRouteName() === name) {
    fn()
    return
  }
  router
    .push({ name })
    .then(() => {
      nextTick(fn)
    })
    .catch(() => {
      fn()
    })
}

/** 基础+进阶教程全部讲解文案（去重），用于副窗「选择教程」阶段预热 TTS（不依赖教程已启动） */
export function getTutorialTtsWarmupTexts(isProMode: boolean): string[] {
  const keep = (step: TutorialStep) => (step.excludeInPro ? !isProMode : true)
  const merged = [...tutorialStepsBasic, ...tutorialStepsAdvanced].filter(keep)
  const seen = new Set<string>()
  const out: string[] = []
  for (const step of merged) {
    const d = String(step.description || '').trim()
    if (!d || seen.has(d)) continue
    seen.add(d)
    out.push(d)
  }
  return out
}

export const useTutorialStore = defineStore('tutorial', () => {
  const isActive = ref(false)
  const isExited = ref(false)
  const currentStepIndex = ref(0)
  const currentTrack = ref<TutorialTrackId | null>(null)
  const steps = ref<TutorialStep[]>([])
  const highlightRect = ref<{ top: number; left: number; width: number; height: number } | null>(null)
  const canNext = ref(false)
  const blockedTip = ref('')
  const testResults = ref<Record<string, TutorialTestStatus>>({})
  const lastTestReport = ref<{ total: number; passed: number; skipped: number } | null>(null)
  const returnContext = ref<TutorialReturnContext | null>(null)
  /** 专业版下基础教程无可用步骤时自动改走进阶路线，在遮罩上提示用户原因 */
  const proBasicFallbackNotice = ref('')
  /** false = 未进入教程或未采集；null = 当时 localStorage 无此项 */
  const tutorialProIntentSnapshot = ref<ProIntentLocalSnapshot>(false)

  const captureTutorialProIntentSnapshot = () => {
    tutorialProIntentSnapshot.value = localStorage.getItem(PRO_INTENT_EXPERIENCE_STORAGE_KEY)
  }

  const restoreTutorialProIntentSnapshot = () => {
    if (tutorialProIntentSnapshot.value === false) return
    const snap = tutorialProIntentSnapshot.value
    tutorialProIntentSnapshot.value = false
    if (snap === null || snap === '') {
      localStorage.removeItem(PRO_INTENT_EXPERIENCE_STORAGE_KEY)
    } else {
      localStorage.setItem(PRO_INTENT_EXPERIENCE_STORAGE_KEY, snap)
    }
    const enabled = snap === '1'
    window.dispatchEvent(
      new CustomEvent('xcagi:pro-intent-experience-changed', { detail: { enabled } })
    )
  }

  const currentStep = computed(() => steps.value[currentStepIndex.value] || null)
  const hasPrev = computed(() => currentStepIndex.value > 0)
  const isLastStep = computed(() => currentStepIndex.value >= steps.value.length - 1)
  const testSummary = computed(() => {
    const total = steps.value.length
    const values = Object.values(testResults.value)
    const passed = values.filter((x) => x === 'passed').length
    const skipped = values.filter((x) => x === 'skipped').length
    const pending = Math.max(0, total - passed - skipped)
    return { total, passed, skipped, pending }
  })

  const clearBlockedTip = () => {
    blockedTip.value = ''
  }

  let stepTargetPollTimer: ReturnType<typeof setTimeout> | null = null
  const clearStepTargetPoll = () => {
    if (stepTargetPollTimer !== null) {
      clearTimeout(stepTargetPollTimer)
      stepTargetPollTimer = null
    }
  }

  const resetRuntime = () => {
    clearStepTargetPoll()
    currentStepIndex.value = 0
    highlightRect.value = null
    canNext.value = false
    blockedTip.value = ''
    testResults.value = {}
    currentTrack.value = null
  }

  const markStepStatus = (stepId: string, status: TutorialTestStatus) => {
    if (!stepId) return
    testResults.value = {
      ...testResults.value,
      [stepId]: status
    }
  }

  /** 进阶「页内功能」步：侧栏点菜单后路由已变但页面异步挂载，首帧量不到会误跳过；轮询直到 #view-* 出现 */
  const pollUntilStepTargetReady = (stepId: string) => {
    clearStepTargetPoll()
    highlightRect.value = getTutorialFallbackHighlightRect()
    blockedTip.value = '正在加载本页…'
    let attempts = 0
    const poll = () => {
      stepTargetPollTimer = null
      if (!isActive.value || currentStep.value?.id !== stepId) return
      const rect = resolveStepHighlightRect(currentStep.value)
      if (rect) {
        highlightRect.value = rect
        clearBlockedTip()
        if (currentStep.value.actionType === 'observe') {
          canNext.value = true
          markStepStatus(currentStep.value.id, 'passed')
        }
        return
      }
      attempts += 1
      if (attempts >= 50) {
        blockedTip.value = '若仍未出现本页高亮，请再点侧栏进入该菜单，或点「下一步」。'
        canNext.value = true
        markStepStatus(currentStep.value.id, 'passed')
        return
      }
      stepTargetPollTimer = window.setTimeout(poll, 100)
    }
    stepTargetPollTimer = window.setTimeout(poll, 80)
  }

  const skipMissingTargets = () => {
    const tryResolveCurrent = () => {
      if (!currentStep.value) {
        finishTutorial()
        return
      }
      if (window.__XCAGI_IS_PRO_MODE && currentStep.value.excludeInPro) {
        if (import.meta.env.DEV) {
          console.info('[tutorial] skip pro-only guarded step:', currentStep.value.id)
        }
        markStepStatus(currentStep.value.id, 'skipped')
        currentStepIndex.value += 1
        canNext.value = false
        skipMissingTargets()
        return
      }
      const step = currentStep.value
      const applyRect = () => {
        if (!currentStep.value) {
          finishTutorial()
          return
        }
        const rect = resolveStepHighlightRect(currentStep.value)
        if (rect) {
          highlightRect.value = rect
          if (currentStep.value.actionType === 'observe') {
            canNext.value = true
            markStepStatus(currentStep.value.id, 'passed')
          }
          return
        }
        if (shouldNeverAutoSkipStep(currentStep.value)) {
          highlightRect.value = getTutorialFallbackHighlightRect()
          blockedTip.value = '请稍候，待任务执行完成出现「开始打印」后再点击该按钮。'
          return
        }
        if (currentStep.value.noAutoSkipWhenMissing) {
          pollUntilStepTargetReady(currentStep.value.id)
          return
        }
        blockedTip.value = '当前功能在此页面不可用，已自动跳过。'
        markStepStatus(currentStep.value.id, 'skipped')
        currentStepIndex.value += 1
        canNext.value = false
        skipMissingTargets()
      }
      const runAfterRoute = () => {
        if (step.assistantTab) {
          dispatchAssistantTab(step.assistantTab)
          afterAssistantTabLayout(applyRect)
        } else {
          afterAssistantTabLayout(applyRect)
        }
      }
      if (step.routeName?.trim()) {
        ensureRouteForStepThen(step, runAfterRoute)
        return
      }
      if (step.assistantTab) {
        dispatchAssistantTab(step.assistantTab)
        afterAssistantTabLayout(applyRect)
        return
      }
      applyRect()
    }
    tryResolveCurrent()
  }

  const filterStepsForPro = (list: TutorialStep[], pro: boolean) =>
    list.filter((step) => (step.excludeInPro ? !pro : true))

  const startTutorial = (
    options: {
      isProMode?: boolean
      returnContext?: TutorialReturnContext
      track?: TutorialTrackId
    } = {}
  ) => {
    const isProMode = !!options.isProMode
    proBasicFallbackNotice.value = ''
    let effectiveTrack: TutorialTrackId = options.track ?? 'basic'
    returnContext.value = options.returnContext || null
    let source =
      effectiveTrack === 'advanced' ? tutorialStepsAdvanced : tutorialStepsBasic
    steps.value = filterStepsForPro(source, isProMode)
    // 基础教程步骤默认可在普通版外隐藏；专业版下会全部被过滤掉，表现为「点了没反应」。
    if (!steps.value.length && effectiveTrack === 'basic' && isProMode) {
      proBasicFallbackNotice.value =
        '当前为专业版界面：基础教程面向普通版布局，已自动切换为「进阶教程」路线（仍可分步熟悉菜单与页面）。'
      effectiveTrack = 'advanced'
      source = tutorialStepsAdvanced
      steps.value = filterStepsForPro(source, isProMode)
    }
    if (!steps.value.length) {
      finishTutorial()
      return
    }
    captureTutorialProIntentSnapshot()
    isActive.value = true
    isExited.value = false
    lastTestReport.value = null
    resetRuntime()
    // 须在 resetRuntime 之后赋值：reset 会清空 currentTrack
    currentTrack.value = effectiveTrack
    for (const step of steps.value) {
      markStepStatus(step.id, 'pending')
    }
    skipMissingTargets()
  }

  const refreshHighlight = (opts?: { skipMissingOnFail?: boolean }) => {
    const skipMissingOnFail = opts?.skipMissingOnFail !== false
    if (!isActive.value || !currentStep.value) return
    const step = currentStep.value
    const apply = () => {
      if (!isActive.value || !currentStep.value) return
      const rect = resolveStepHighlightRect(currentStep.value)
      if (rect) {
        highlightRect.value = rect
        clearBlockedTip()
        clearStepTargetPoll()
        if (currentStep.value.actionType === 'observe') {
          canNext.value = true
          markStepStatus(currentStep.value.id, 'passed')
        }
        return
      }
      if (shouldNeverAutoSkipStep(currentStep.value)) {
        highlightRect.value = getTutorialFallbackHighlightRect()
        blockedTip.value = '请稍候，待任务执行完成出现「开始打印」后再点击该按钮。'
        return
      }
      if (currentStep.value.noAutoSkipWhenMissing) {
        pollUntilStepTargetReady(currentStep.value.id)
        return
      }
      if (skipMissingOnFail) {
        skipMissingTargets()
      } else {
        highlightRect.value = getTutorialFallbackHighlightRect()
      }
    }
    const runAfterRoute = () => {
      if (step.assistantTab) {
        dispatchAssistantTab(step.assistantTab)
        afterAssistantTabLayout(apply)
      } else {
        afterAssistantTabLayout(apply)
      }
    }
    if (step.routeName?.trim()) {
      ensureRouteForStepThen(step, runAfterRoute)
      return
    }
    if (step.assistantTab) {
      dispatchAssistantTab(step.assistantTab)
      afterAssistantTabLayout(apply)
      return
    }
    apply()
  }

  const prevStep = () => {
    if (!hasPrev.value) return
    currentStepIndex.value -= 1
    canNext.value = false
    clearBlockedTip()
    // 不在此处 refreshHighlight：须先由 TutorialOverlay 完成 ensureStepRoute / ensureAssistantTab，
    // 否则路由与副窗仍为「下一步」状态，量到的 DOM 与步骤不一致。
  }

  const nextStep = () => {
    if (!currentStep.value) {
      exitTutorial()
      return
    }
    if (isLastStep.value) {
      finishTutorial()
      return
    }
    currentStepIndex.value += 1
    canNext.value = false
    clearBlockedTip()
    refreshHighlight()
    if (currentStep.value?.actionType === 'observe') {
      canNext.value = true
    }
  }

  const markCurrentStepClicked = () => {
    if (!currentStep.value || currentStep.value.actionType !== 'click') return
    canNext.value = true
    blockedTip.value = ''
    markStepStatus(currentStep.value.id, 'passed')
  }

  const blockOutsideClick = () => {
    if (!currentStep.value || currentStep.value.actionType !== 'click') return
    blockedTip.value = '请先点击高亮区域完成当前步骤。'
  }

  const finishTutorial = () => {
    restoreTutorialProIntentSnapshot()
    proBasicFallbackNotice.value = ''
    lastTestReport.value = {
      total: testSummary.value.total,
      passed: testSummary.value.passed,
      skipped: testSummary.value.skipped
    }
    isActive.value = false
    isExited.value = false
    resetRuntime()
  }

  const exitTutorial = () => {
    restoreTutorialProIntentSnapshot()
    proBasicFallbackNotice.value = ''
    lastTestReport.value = {
      total: testSummary.value.total,
      passed: testSummary.value.passed,
      skipped: testSummary.value.skipped
    }
    isActive.value = false
    isExited.value = true
    resetRuntime()
  }

    return {
    isActive,
    isExited,
    currentStepIndex,
    currentTrack,
    steps,
    currentStep,
    highlightRect,
    canNext,
    blockedTip,
    proBasicFallbackNotice,
    testResults,
    testSummary,
    lastTestReport,
    returnContext,
    hasPrev,
    isLastStep,
    startTutorial,
    refreshHighlight,
    prevStep,
    nextStep,
    markCurrentStepClicked,
    blockOutsideClick,
    clearBlockedTip,
    finishTutorial,
    exitTutorial
  }
})
