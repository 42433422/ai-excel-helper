import { describe, expect, it, vi } from 'vitest'
import { LS_PLANNER_MOD_FACADE_ENABLED } from '@/constants/plannerMod'
import { XCAGI_ACTIVE_EXTENSION_MOD_ID_KEY } from '@/utils/xcagiStorageKeys'
import { resolvePlannerPagePath } from './plannerPagePaths'

describe('plannerPagePaths', () => {
  it('maps planner pages when facade on', () => {
    const store: Record<string, string> = {
      [LS_PLANNER_MOD_FACADE_ENABLED]: '1',
    }
    vi.stubGlobal('localStorage', {
      getItem: (k: string) => store[k] ?? null,
    })
    expect(resolvePlannerPagePath('/')).toBe('/mod/xcagi-planner-bridge/chat')
    expect(resolvePlannerPagePath('/brain')).toBe('/mod/xcagi-planner-bridge/brain')
    vi.unstubAllGlobals()
  })

  it('keeps host chat when taiyangniao-pro is active extension', () => {
    const store: Record<string, string> = {
      [LS_PLANNER_MOD_FACADE_ENABLED]: '1',
      [XCAGI_ACTIVE_EXTENSION_MOD_ID_KEY]: 'taiyangniao-pro',
    }
    vi.stubGlobal('localStorage', {
      getItem: (k: string) => store[k] ?? null,
    })
    expect(resolvePlannerPagePath('/')).toBe('/')
    vi.unstubAllGlobals()
  })
})
