import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useModsStore, CLIENT_MODS_UI_OFF_KEY } from './mods'

describe('useModsStore (Pinia)', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    // ensure a clean storage between tests
    try {
      localStorage.clear()
    } catch {
      // jsdom may not have full localStorage in some environments
    }
    setActivePinia(createPinia())
  })

  it('applyLoadingStatusPreview populates mods when empty', () => {
    const store = useModsStore()
    store.mods = []
    store.applyLoadingStatusPreview([{ id: 'm1', name: 'Mod One', version: '1.0' }])
    expect(store.mods.length).toBe(1)
    expect(store.mods[0].id).toBe('m1')
    expect(store.mods[0].name).toBe('Mod One')
  })

  it('setClientModsUiOff toggles and persists', () => {
    const store = useModsStore()
    store.mods = [{ id: 'm1', name: 'Mod One', version: '1.0', author: '', description: '' }]
    store.setClientModsUiOff(true)
    expect(store.clientModsUiOff).toBe(true)
    expect(localStorage.getItem(CLIENT_MODS_UI_OFF_KEY)).toBe('1')
    expect(store.mods.length).toBe(0)
    expect(store.isLoaded).toBe(true)

    store.setClientModsUiOff(false)
    expect(store.clientModsUiOff).toBe(false)
    expect(localStorage.getItem(CLIENT_MODS_UI_OFF_KEY)).toBeNull()
  })

  it('getModMenu aggregates menu items from modsForUi', () => {
    const store = useModsStore()
    store.mods = [
      {
        id: 'm1',
        name: 'm1',
        version: '1',
        author: '',
        description: '',
        menu: [{ id: 'i1', label: 'Item1', icon: '', path: '/p1' }],
      },
    ]
    const menu = store.getModMenu()
    expect(menu.length).toBe(1)
    expect(menu[0].modId).toBe('m1')
    expect(menu[0].id).toBe('i1')
  })

  it('getModMenu shows sunbird attendance entries when active but API list omits pack', () => {
    const store = useModsStore()
    store.mods = [
      {
        id: 'xcagi-planner-bridge',
        name: 'Planner',
        version: '1',
        author: '',
        description: '',
      },
    ]
    store.setActiveModId('taiyangniao-pro')
    const menu = store.getModMenu()
    const labels = menu.map((m) => m.label)
    expect(labels).toContain('考勤表转换')
    expect(labels).not.toContain('考勤转换设置')
  })
})

