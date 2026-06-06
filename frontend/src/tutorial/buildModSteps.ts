import type { ModInfo } from '@/stores/mods'
import type {
  ModTutorialContribution,
  TutorialBuildContext,
  TutorialPageHighlight,
  TutorialStep,
  TutorialTrackMeta,
} from './types'

function readModTutorial(mod: ModInfo): ModTutorialContribution | null {
  const raw = mod?.tutorial
  if (!raw || typeof raw !== 'object') return null
  return raw as ModTutorialContribution
}

export function collectModTutorialTracks(
  mods: ModInfo[],
  modMenuKeys: Set<string>,
): TutorialTrackMeta[] {
  const out: TutorialTrackMeta[] = []
  for (const mod of mods || []) {
    const t = readModTutorial(mod)
    if (!t?.tracks?.length) continue
    for (const row of t.tracks) {
      const id = String(row.id || '').trim()
      if (!id) continue
      if (row.requires_mod_menu) {
        const hasMenu = (mod.menu || []).some((m) => modMenuKeys.has(`mod-${m.id}`))
        if (!hasMenu) continue
      }
      out.push({
        id,
        title: String(row.title || id),
        summary: String(row.summary || row.description || '').slice(0, 120),
        description: String(row.description || row.summary || ''),
        kind: 'mod',
        recommended: row.recommended === true,
        modId: mod.id,
      })
    }
  }
  return out
}

export function collectModPageHighlights(ctx: TutorialBuildContext): Record<string, TutorialPageHighlight[]> {
  const out: Record<string, TutorialPageHighlight[]> = {}
  for (const mod of ctx.mods || []) {
    const t = readModTutorial(mod as ModInfo)
    if (!t?.page_highlights) continue
    for (const [route, rows] of Object.entries(t.page_highlights)) {
      if (!out[route]) out[route] = []
      out[route].push(...(rows || []))
    }
  }
  return out
}

export function collectModStepsForTrack(
  trackId: string,
  mods: ModInfo[],
): TutorialStep[] {
  const steps: TutorialStep[] = []
  for (const mod of mods || []) {
    const t = readModTutorial(mod)
    if (!t?.steps?.length) continue
    const prefix = `${mod.id}:`
    for (const row of t.steps) {
      const rowTrack = String(row.track || 'advanced').trim()
      if (rowTrack !== trackId) continue
      const afterNavKey = String(row.after_nav_key || row.afterNavKey || '').trim()
      steps.push({
        ...row,
        id: String(row.id || '').startsWith(prefix) ? String(row.id) : `${prefix}${row.id}`,
        afterNavKey: afterNavKey || undefined,
      })
    }
  }
  return steps
}

export function injectModSteps(base: TutorialStep[], modSteps: TutorialStep[]): TutorialStep[] {
  if (!modSteps.length) return base
  const out = [...base]
  for (const step of modSteps) {
    const after = step.afterNavKey
    if (after) {
      let idx = -1
      for (let i = out.length - 1; i >= 0; i -= 1) {
        const s = out[i]
        if (s.id === `nav-${after}` || s.targetSelector?.includes(`data-view="${after}"`)) {
          idx = i
          break
        }
      }
      if (idx >= 0) {
        out.splice(idx + 1, 0, step)
        continue
      }
    }
    out.push(step)
  }
  return dedupeStepIds(out)
}

function dedupeStepIds(steps: TutorialStep[]): TutorialStep[] {
  const seen = new Set<string>()
  const out: TutorialStep[] = []
  for (const s of steps) {
    if (seen.has(s.id)) continue
    seen.add(s.id)
    out.push(s)
  }
  return out
}
