import type {
  WorkflowBranchDoc,
  WorkflowEmployeeDocsV1,
  WorkflowEmployeeKind,
  WorkflowFlowDoc,
} from '@/types/workflowEmployeeDocs'
import bundledDocs from '@/data/workflow-employee-docs.json'
import {
  isWorkflowDocCoreEmployeeId,
  isWorkflowDocFixedModServiceId,
} from '@/constants/workflowEmployeeDocIds'
import {
  countManifestWorkflowEmployeeRows,
  resolvePhoneAgentApiBase,
  type ModWithWorkflowEmployees,
  type WorkflowEmployeeManifestEntry,
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
  if (
    fromJson === 'core' ||
    fromJson === 'fixed_extension' ||
    fromJson === 'mod_extension'
  ) {
    return fromJson
  }
  return 'core'
}

function isPlaceholderManifestEntry(e: WorkflowEmployeeManifestEntry): boolean {
  if (e.workflow_ui_kind === 'placeholder') return true
  return !!e.workflow_placeholder
}

function oneLineSummary(text: string, maxLen = 220): string {
  const s = String(text || '')
    .replace(/\s+/g, ' ')
    .trim()
  if (!s) return ''
  if (s.length <= maxLen) return s
  return `${s.slice(0, maxLen - 1)}…`
}

/** 由 manifest 条目生成流程全景过程段（与副窗 panel_summary 一致） */
export function buildSyntheticManifestWorkflowFlow(
  e: WorkflowEmployeeManifestEntry,
  modId: string,
  modName: string,
): WorkflowFlowDoc {
  const id = String(e.id || '').trim()
  const label = String(e.label || id).trim() || id
  const summary =
    e.panel_summary?.trim() ||
    `由扩展「${modName}」在 manifest 中声明的工作流员工「${label}」。`
  const phoneBase = resolvePhoneAgentApiBase(e, modId)
  const placeholder = isPlaceholderManifestEntry(e)

  const steps: WorkflowFlowDoc['steps'] = [
    { label: '启用员工', detail: '在副窗打开对应工作流员工开关（xcagi_workflow_ai_employees）。' },
  ]

  if (phoneBase) {
    steps.push(
      {
        label: '启动电话业务员链路',
        detail: `开启时 POST ${phoneBase}/start；关闭时 POST ${phoneBase}/stop（与副窗一致）。`,
      },
      {
        label: '轮询运行状态',
        detail: `启用后定期 GET ${phoneBase}/status，将状态合并进任务面板条目。`,
      },
    )
  } else if (placeholder) {
    steps.push({
      label: '使用宿主业务页',
      detail:
        '本条为触点/占位型扩展：执行业务在宿主页或侧栏入口完成，与智能对话、星标刷新等配合；无独立 phone-agent 自动化。',
    })
  } else {
    steps.push({
      label: '按扩展包文档对接',
      detail: `专有 API、蓝图与步骤见扩展包「${modName}」文档；本页仅展示 manifest 摘要。`,
    })
  }

  const notes = [`扩展包：${modName}（${modId}）`]
  if (phoneBase) {
    notes.push(`电话 API 根：${phoneBase}`)
  } else if (e.phone_agent_base_path?.trim()) {
    notes.push(
      `相对 API 前缀：/api/mod/${modId}/${e.phone_agent_base_path.replace(/^\/+|\/+$/g, '')}`,
    )
  }

  return {
    id,
    kind: 'mod_extension',
    title: `${label} · 过程`,
    lead: summary,
    steps,
    notes,
  }
}

function buildSyntheticManifestBranch(
  e: WorkflowEmployeeManifestEntry,
  modName: string,
): WorkflowBranchDoc {
  const id = String(e.id || '').trim()
  const label = String(e.label || id).trim() || id
  const summary =
    e.panel_summary?.trim() ||
    `由扩展「${modName}」声明的工作流员工「${label}」。`
  return {
    id,
    kind: 'mod_extension',
    title: label,
    trigger: oneLineSummary(summary),
  }
}

/** 将 manifest workflow_employees 并入 branches/flows（id 去重，跳过 JSON 已有 id） */
export function mergeManifestWorkflowEmployeesIntoDocs(
  d: WorkflowEmployeeDocsV1,
  ctx: WorkflowDocsRuntimeContext,
): WorkflowEmployeeDocsV1 {
  if (!isModWorkflowEmployeesActive(ctx)) {
    return d
  }

  const existingIds = new Set<string>([
    ...d.branches.map((b) => b.id),
    ...d.flows.map((f) => f.id),
  ])
  const extraBranches: WorkflowBranchDoc[] = []
  const extraFlows: WorkflowFlowDoc[] = []
  const seen = new Set<string>()

  for (const m of ctx.modsForUi || []) {
    const modId = String(m.id || '').trim()
    const modName = String(m.name || modId || '扩展').trim() || '扩展'
    for (const e of m.workflow_employees || []) {
      const id = String(e?.id || '').trim()
      if (!id || seen.has(id) || existingIds.has(id)) continue
      seen.add(id)
      extraBranches.push(buildSyntheticManifestBranch(e, modName))
      extraFlows.push(buildSyntheticManifestWorkflowFlow(e, modId, modName))
    }
  }

  if (!extraBranches.length) return d

  return {
    ...d,
    branches: [...d.branches, ...extraBranches],
    flows: [...d.flows, ...extraFlows],
  }
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
  const modPkgs = ctx.modsForUi.length
  const modRows = countManifestWorkflowEmployeeRows(ctx.modsForUi)
  const modActive = isModWorkflowEmployeesActive(ctx)

  let pageSubtitle: string
  let pipelineBranchLabel: string
  let overviewNote: string

  if (ctx.clientModsUiOff) {
    pipelineBranchLabel = '未安装工作流员工（原版模式）'
    pageSubtitle =
      '副窗「工作流员工」为原版模式：浏览器不请求扩展列表，无 manifest 工作流员工。请从 MOD 商店「AI 员工」安装工作流员工 Mod 后刷新。'
    overviewNote = '共 0 条；开关写入 xcagi_workflow_ai_employees。'
  } else if (ctx.modsDisabledByServer) {
    pipelineBranchLabel = '未安装工作流员工（后端已关闭扩展）'
    pageSubtitle = '后端已禁用扩展（XCAGI_DISABLE_MODS）；副窗与本文不展示工作流员工。'
    overviewNote = '共 0 条；后端未加载扩展包。'
  } else if (!ctx.isModsListLoaded) {
    pipelineBranchLabel = '同步扩展列表中'
    pageSubtitle =
      '正在与后端同步可用扩展列表。若环境中已安装带 workflow_employees 的工作流员工 Mod，同步完成后本页与副窗将自动更新。'
    overviewNote = '当前共 0 条；扩展蓝图与注册失败原因以各扩展包及后端日志为准。'
  } else if (!modActive) {
    pipelineBranchLabel = '未安装工作流员工'
    if (modPkgs === 0) {
      pageSubtitle =
        '扩展列表已就绪：当前未加载任何扩展包。请从 MOD 商店「AI 员工 → 工作流员工」安装 6 类工作流员工 Mod。'
      overviewNote = '共 0 条；无已加载扩展包。'
    } else {
      pageSubtitle = `已加载 ${modPkgs} 个扩展包，均未声明 workflow_employees。请安装工作流员工 Mod（manifest 含 workflow_employees）。`
      overviewNote = '共 0 条；当前扩展包未提供工作流员工条目。'
    }
  } else {
    pipelineBranchLabel = `已安装 ${modRows} 名工作流员工`
    pageSubtitle = `副窗与本文展示当前 manifest 中的 ${modRows} 条工作流员工（来自 ${modPkgs} 个扩展包）。各 Mod 的蓝图、API 与专有步骤以扩展包文档为准。`
    overviewNote = `${modRows} 条来自各包 workflow_employees（id 去重）。开关写入 xcagi_workflow_ai_employees。`
  }

  const withCopy: WorkflowEmployeeDocsV1 = {
    ...d,
    pageSubtitle,
    pipelineBranchLabel,
    overviewNote,
    modManifestExplainer: undefined,
  }
  return mergeManifestWorkflowEmployeesIntoDocs(withCopy, ctx)
}
