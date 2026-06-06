import { describe, expect, it } from 'vitest'
import { collectModPageHighlights, collectModTutorialTracks, injectModSteps } from './buildModSteps'
import { createTutorialBuildContext } from './buildContext'
import type { ModInfo } from '@/stores/mods'

describe('buildModSteps', () => {
  it('merges mod page highlights by route', () => {
    const mods = [
      {
        id: 'demo-mod',
        tutorial: {
          page_highlights: {
            chat: [{ idSuffix: 'x', title: 'T', description: 'D', targetSelector: '#x' }],
          },
        },
      },
    ] as unknown as ModInfo[]
    const ctx = createTutorialBuildContext({
      industryId: '考勤',
      mods,
      visibleNav: [],
      isProMode: false,
    })
    const merged = collectModPageHighlights(ctx)
    expect(merged.chat?.[0]?.idSuffix).toBe('x')
  })

  it('filters tracks that require mod menu', () => {
    const mods = [
      {
        id: 'm1',
        menu: [{ id: 'erp-products', label: '产品', icon: 'fa', path: '/x' }],
        tutorial: {
          tracks: [{ id: 'erp-tour', title: 'ERP 导览', requires_mod_menu: true }],
        },
      },
    ] as unknown as ModInfo[]
    const keys = new Set(['mod-erp-products'])
    const tracks = collectModTutorialTracks(mods, keys)
    expect(tracks).toHaveLength(1)
    const tracksHidden = collectModTutorialTracks(mods, new Set())
    expect(tracksHidden).toHaveLength(0)
  })

  it('injects mod step after nav key', () => {
    const base = [
      { id: 'nav-chat', title: 'A', description: 'd', targetSelector: '.sidebar .menu-item[data-view="chat"]', actionType: 'click' as const },
      { id: 'nav-products', title: 'B', description: 'd', targetSelector: '.sidebar .menu-item[data-view="products"]', actionType: 'click' as const },
    ]
    const modSteps = [
      {
        id: 'demo:extra',
        title: 'Extra',
        description: 'after chat',
        targetSelector: '#x',
        actionType: 'observe' as const,
        afterNavKey: 'chat',
      },
    ]
    const out = injectModSteps(base, modSteps)
    expect(out[1]?.id).toBe('demo:extra')
    expect(out[2]?.id).toBe('nav-products')
  })
})
