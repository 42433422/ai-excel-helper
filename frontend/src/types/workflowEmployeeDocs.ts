/** 工作流员工说明文档（JSON / 远程加载），与实现逻辑解耦，便于单独更新文案 */

/** 与副窗列表分类一致：四名 AI 为内置；微信电话/真实电话为固定扩展行；Mod 员工由 manifest 追加 */
export type WorkflowEmployeeKind = 'core' | 'fixed_extension'

export type WorkflowBranchDoc = {
  id: string
  title: string
  trigger: string
  /** 总览卡片角标；缺省视为 core */
  kind?: WorkflowEmployeeKind
}

export type WorkflowStepDoc = {
  label: string
  detail?: string
}

export type WorkflowFlowDoc = {
  id: string
  title: string
  lead: string
  steps: WorkflowStepDoc[]
  notes?: string[]
  /** 过程标题旁角标；缺省视为 core */
  kind?: WorkflowEmployeeKind
}

export type WorkflowEmployeeDocsV1 = {
  schemaVersion: 1
  /** 页面主标题 */
  pageTitle: string
  /** 页头说明（纯文本，勿写 HTML） */
  pageSubtitle: string
  /** 总览管道末端节点文案（流程全景页由运行时按 Mod 状态覆盖） */
  pipelineBranchLabel: string
  /** 总览底部说明（流程全景页由运行时覆盖） */
  overviewNote: string
  branches: WorkflowBranchDoc[]
  flows: WorkflowFlowDoc[]
  /**
   * 历史字段：核心包不再使用。Mod/扩展的蓝图与 manifest 说明由各扩展包自带文档提供；
   * 远程 JSON 若仍带此段，流程全景页也会忽略。
   */
  modManifestExplainer?: {
    title: string
    lead: string
    bullets?: string[]
  }
  /** 副窗「一键托管 / 龙虾」里工作流员工区提示 */
  floatPanelHint: string
  /** 流程全景链接 title 属性 */
  workflowVisualLinkTitle?: string
  /** 覆盖一键托管顶栏介绍；缺省或空串则用代码内置逻辑 */
  recommendIntroOneClick?: string
  /** 覆盖龙虾托管顶栏介绍 */
  recommendIntroLobster?: string
}
