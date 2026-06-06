import { describe, expect, it } from 'vitest'
import { pinMenuKeyFirst, PRIMARY_CHAT_MENU_KEY, sidebarLayoutSeedKeys } from './coreMenuCatalog'

describe('coreMenuCatalog', () => {
  it('pinMenuKeyFirst moves chat to front', () => {
    const rows = [
      { key: 'mod-a', name: 'A' },
      { key: PRIMARY_CHAT_MENU_KEY, name: 'Chat' },
      { key: 'products', name: 'P' },
    ]
    expect(pinMenuKeyFirst(rows).map((r) => r.key)).toEqual([
      PRIMARY_CHAT_MENU_KEY,
      'mod-a',
      'products',
    ])
  })

  it('sidebarLayoutSeedKeys starts with chat', () => {
    expect(sidebarLayoutSeedKeys()[0]).toBe(PRIMARY_CHAT_MENU_KEY)
  })
})
