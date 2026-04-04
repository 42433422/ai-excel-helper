import type { WorkflowEmployeeDocsV1, WorkflowEmployeeKind } from '@/types/workflowEmployeeDocs'
import bundledDocs from '@/data/workflow-employee-docs.json'
import {
  isWorkflowDocCoreEmployeeId,
  isWorkflowDocFixedModServiceId,
} from '@/constants/workflowEmployeeDocIds'
import {
  countManifestWorkflowEmployeeRows,
  type ModWithWorkflowEmployees,
} from '@/utils/modWorkflowEmployees'

let cached: Promise<WorkflowEmployeeDocsV1> | null = null

function isRecord(x: unknown): x is Record<string, unknown> {
  return typeof x === 'object' && x !== null
}

function isValidV1(data: unknown): data is WorkflowEmployeeDocsV1 {
  if (!isRecord(data)) return false
  if (data.schemaVersion !== 1) return false
  if (typeof data.pageTitle !== 'string' || typeof data.pageSubtitle !== 'string') return false
  if (typeof data.pipelineBranchLabel !== 'string' || typeof data.overviewNote !== 'string') return false
  if (typeof data.floatPanelHint !== 'string') return false
  if (!Array.isArray(data.branches) || !Array.isArray(data.flows)) return false
  return true
}

/** 按员工 id 解析展示分类（远程 JSON 可省略 kind，避免旧文件误标成内置） */
function resolveKindForId(id: string, fromJson?: WorkflowEmployeeKind): WorkflowEmployeeKind {
  if (isWorkflowDocFixedModServiceId(id)) return 'fixed_extension'
  if (isWorkflowDocCoreEmployeeId(id)) return 'core'
  if (fromJson === 'core' || fromJson === 'fixed_extension') return fromJson
  return 'core'
}

/** 合并 JSON 与代码内 id 表，保证 wechat_phone / real_phone 不会变成 core */
export function normalizeWorkflowEmployeeDocs(d: WorkflowEmployeeDocsV1): WorkflowEmployeeDocsV1 {
  return {
    ...d,
    branches: d.branches.map((b) => ({
      ...b,
      kind: resolveKindForId(b.id, b.kind),
    })),
    flows: d.flows.map((f) => ({
      ...f,
      kind: resolveKindForId(f.id, f.kind),
    })),
  }
}

/**
 * 加载工作流员工说明（流程全景文案、副窗提示等）。
 *
 * 优先级：
 * 1. 环境变量 VITE_WORKFLOW_EMPLOYEE_DOCS_URL（可指向 CDN / 内网静态文件，便于不改前端包即可更新）
 * 2. 同源 `/workflow-employee-docs.json`（部署时替换 public 下文件即可）
 * 3. 打包内置 `src/data/workflow-employee-docs.json`（离线 / 请求失败回退）
 *
 * 推荐：**路径 1 — 结构化 JSON 文本**，与代码分仓维护；不要用「静态分析代码」生成说明（叙述质量差、易碎、难审阅）。
 */
export async function loadWorkflowEmployeeDocs(): Promise<WorkflowEmployeeDocsV1> {
  const envUrl = (import.meta.env.VITE_WORKFLOW_EMPLOYEE_DOCS_URL as string | undefined)?.trim()
  const urls: string[] = []
  if (envUrl) urls.push(envUrl)
  urls.push('/workflow-employee-docs.json')

  for (const url of urls) {
    try {
      const r = await fetch(url, { cache: 'no-store' })
      if (!r.ok) continue
      const json: unknown = await r.json()
      if (isValidV1(json)) return normalizeWorkflowEmployeeDocs(json)
      console.warn('[workflowEmployeeDocs] invalid payload from', url)
    } catch (e) {
      console.warn('[workflowEmployeeDocs] fetch failed', url, e)
    }
  }

  if (isValidV1(bundledDocs)) return normalizeWorkflowEmployeeDocs(bundledDocs as WorkflowEmployeeDocsV1)
  throw new Error('[workflowEmployeeDocs] bundled fallback invalid')
}

/** 全应用共享一次解析结果（流程全景与副窗复用） */
export function getWorkflowEmployeeDocs(): Promise<WorkflowEmployeeDocsV1> {
  if (!cached) cached = loadWorkflowEmployeeDocs()
  return cached
}

/** 与副窗固定行数量一致（四名内置 AI + 两行固定扩展） */
const WORKFLOW_FIXED_ROW_COUNT = 6

export type WorkflowDocsRuntimeContext = {
  clientModsUiOff: boolean
  /** 与侧栏/副窗一致：原版模式为空数组 */
  modsForUi: ModWithWorkflowEmployees[]
  /** mods store isLoaded：扩展列表是否已结束首轮拉取（原版模式下恒为 true） */
  isModsListLoaded: boolean
  /** fetchMods 返回 mods_disabled 时的提示文案特征 */
  modsDisabledByServer: boolean
}

/**
 * 仅当扩展已加载且 manifest 中确实存在 workflow_employees 行时，才视为「扩展工作流已启用」（与副窗列表一致）。
 * 原版模式 / 后端关 Mod / 仍在拉列表 / 0 包 / 有包但无员工 → 均为 false，核心 UI 不展示 Mod 向说明。
 */
export function isModWorkflowEmployeesActive(ctx: WorkflowDocsRuntimeContext): boolean {
  if (ctx.clientModsUiOff || ctx.modsDisabledByServer) return false
  if (!ctx.isModsListLoaded) return false
  return countManifestWorkflowEmployeeRows(ctx.modsForUi) > 0
}

/**
 * 流程全景：页头 / 管道 / 紫条随运行时变化。核心包不承载 Mod 专段与蓝图说明（由各扩展包文档自行提供）。
 */
export function applyWorkflowEmployeeDocsRuntime(
  d: WorkflowEmployeeDocsV1,
  ctx: WorkflowDocsRuntimeContext
): WorkflowEmployeeDocsV1 {
  const nFix = WORKFLOW_FIXED_ROW_COUNT
  const modPkgs = ctx.modsForUi.length
  const modRows = countManifestWorkflowEmployeeRows(ctx.modsForUi)
  const modActive = isModWorkflowEmployeesActive(ctx)

  let pageSubtitle: string
  let pipelineBranchLabel: string
  let overviewNote: string

  if (ctx.clientModsUiOff) {
    pipelineBranchLabel = `内置 ${nFix} 类（固定 · 原版模式）`
    pageSubtitle = `副窗「工作流员工」为原版模式：仅 ${nFix} 条固定行（四名内置 AI + 两行固定扩展），浏览器不请求扩展列表。下表与当前副窗一致。`
    overviewNote = `共 ${nFix} 条固定行；角标区分「内置 AI」与「固定扩展」。开关写入 xcagi_workflow_ai_employees。扩展侧蓝图与专有流程不在此页展示。`
  } else if (ctx.modsDisabledByServer) {
    pipelineBranchLabel = `内置 ${nFix} 类（后端已关闭扩展）`
    pageSubtitle = `后端已禁用扩展（XCAGI_DISABLE_MODS）；副窗与本文仅 ${nFix} 条固定行。`
    overviewNote = `共 ${nFix} 条固定行；后端未加载扩展包。`
  } else if (!ctx.isModsListLoaded) {
    pipelineBranchLabel = `内置 ${nFix} 类（固定）`
    pageSubtitle = `正在与后端同步可用扩展列表。当前仅展示固定 ${nFix} 类工作流；若环境中存在在 manifest 声明了工作流员工的扩展，同步完成后本页与副窗将自动一致更新。`
    overviewNote = `共 ${nFix} 条固定行。扩展蓝图、注册失败原因等以各扩展包及后端日志为准，不在此页展开。`
  } else if (!modActive) {
    pipelineBranchLabel = `内置 ${nFix} 类（固定）`
    if (modPkgs === 0) {
      pageSubtitle = `扩展列表已就绪：当前未加载任何扩展包，副窗与本文仅 ${nFix} 条固定行。若安装扩展，其 manifest 与工作流说明由该扩展提供。`
      overviewNote = `共 ${nFix} 条固定行；无已加载扩展包，副窗无 manifest 追加行。`
    } else {
      pageSubtitle = `已加载 ${modPkgs} 个扩展包，均未声明 workflow_employees；副窗与本文仅 ${nFix} 条固定行。扩展蓝图与对接说明由各扩展包维护。`
      overviewNote = `共 ${nFix} 条固定行；当前扩展包未提供工作流员工条目。`
    }
  } else {
    pipelineBranchLabel = `内置 ${nFix} 类 + ${modRows} 条扩展工作流`
    pageSubtitle = `副窗为 ${nFix} 条固定行 + 当前 manifest 中的 ${modRows} 条扩展工作流员工（${modPkgs} 个扩展包）。下图固定六类为内核说明；各扩展的蓝图、API 与专有步骤请以扩展包文档为准。`
    overviewNote = `先 ${nFix} 条固定行，再 ${modRows} 条来自各包 workflow_employees（id 去重）。固定扩展 wechat_phone / real_phone 与 manifest 行由前端区分。开关写入 xcagi_workflow_ai_employees。`
  }

  return {
    ...d,
    pageSubtitle,
    pipelineBranchLabel,
    overviewNote,
    modManifestExplainer: undefined,
  }
}
