import type { TutorialBuildContext, TutorialStep, TutorialTrackId } from './types'
import { buildAdvancedNavSteps } from './buildNavTour'
import { collectModStepsForTrack, injectModSteps } from './buildModSteps'
import { buildBasicSteps } from './tracks/basic'

export function filterStepsForPro(list: TutorialStep[], pro: boolean): TutorialStep[] {
  return list.filter((step) => (step.excludeInPro ? !pro : true))
}

export function resolveTrackSteps(trackId: TutorialTrackId, ctx: TutorialBuildContext): TutorialStep[] {
  const id = String(trackId || 'basic').trim() || 'basic'
  let steps: TutorialStep[]
  if (id === 'advanced') {
    steps = buildAdvancedNavSteps(ctx.visibleNav, ctx)
  } else if (id === 'basic') {
    steps = buildBasicSteps(ctx)
  } else {
    steps = injectModSteps([], collectModStepsForTrack(id, ctx.mods as never[]))
    if (!steps.length) {
      steps = buildAdvancedNavSteps(ctx.visibleNav, ctx)
    }
  }
  const modInjected =
    id === 'basic' || id === 'advanced'
      ? injectModSteps(steps, collectModStepsForTrack(id, ctx.mods as never[]))
      : steps
  return filterStepsForPro(modInjected, ctx.isProMode)
}

export function resolveAllWarmupSteps(ctx: TutorialBuildContext): TutorialStep[] {
  const basic = resolveTrackSteps('basic', ctx)
  const advanced = resolveTrackSteps('advanced', ctx)
  return dedupeById([...basic, ...advanced])
}

function dedupeById(steps: TutorialStep[]): TutorialStep[] {
  const seen = new Set<string>()
  const out: TutorialStep[] = []
  for (const s of steps) {
    if (seen.has(s.id)) continue
    seen.add(s.id)
    out.push(s)
  }
  return out
}
