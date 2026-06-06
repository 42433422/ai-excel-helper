export type ModPrimaryWorkflowStep = {
  id: string
  label: string
  route?: string
}

export type ModPrimaryWorkflow = {
  title: string
  steps: ModPrimaryWorkflowStep[]
}

function normalizeSteps(raw: unknown): ModPrimaryWorkflowStep[] {
  if (!Array.isArray(raw)) return []
  return raw
    .map((row, idx) => {
      if (typeof row === 'string') {
        const label = row.trim()
        return label ? { id: `step-${idx + 1}`, label } : null
      }
      if (!row || typeof row !== 'object') return null
      const r = row as Record<string, unknown>
      const label = String(r.label || r.title || r.name || '').trim()
      if (!label) return null
      return {
        id: String(r.id || `step-${idx + 1}`).trim(),
        label,
        route: String(r.route || r.path || '').trim() || undefined,
      }
    })
    .filter((row): row is ModPrimaryWorkflowStep => Boolean(row))
}

export function resolveModPrimaryWorkflow(mod: unknown): ModPrimaryWorkflow | null {
  if (!mod || typeof mod !== 'object') return null
  const m = mod as Record<string, unknown>
  const direct = m.primary_workflow || m.primaryWorkflow
  const frontend = m.frontend && typeof m.frontend === 'object' ? (m.frontend as Record<string, unknown>) : {}
  const source = direct || frontend.primary_workflow || frontend.primaryWorkflow
  if (source && typeof source === 'object') {
    const row = source as Record<string, unknown>
    const steps = normalizeSteps(row.steps)
    if (steps.length) {
      return {
        title: String(row.title || '推荐流程').trim() || '推荐流程',
        steps,
      }
    }
  }

  if (String(m.id || '').trim() === 'taiyangniao-pro') {
    return {
      title: '考勤 Mod 推荐流程',
      steps: [
        { id: 'upload', label: '上传考勤表', route: '/taiyangniao-pro' },
        { id: 'match', label: '匹配员工', route: '/products' },
        { id: 'stats', label: '生成统计', route: '/shipment-records' },
        { id: 'export-print', label: '导出/打印', route: '/print' },
      ],
    }
  }
  return null
}
