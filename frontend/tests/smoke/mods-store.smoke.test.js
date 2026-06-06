/**
 * 前端冒烟：Mod 列表 Pinia 商店（不启 dev server，mock fetch）
 *
 * 单次：npm run test:smoke
 * 热重跑（改测试或 src/stores/mods 即重跑）：npm run test:smoke:watch
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'

/** initialize 末尾会 dynamic import 真 router + 注册 Mod 路由；单测里避免 import.meta.glob 与 replace 等副作用拖死用例 */
vi.mock('@/router/registerModRoutes', () => ({
  registerModRoutes: vi.fn(() => Promise.resolve()),
  registerAllModRoutesFromGlob: vi.fn(() => Promise.resolve()),
}))
vi.mock('@/stores/hostConfig', async (importOriginal) => {
  const actual = await importOriginal()
  return {
    ...actual,
    bootstrapHostConfig: vi.fn(() => Promise.resolve()),
  }
})
vi.mock('@/stores/industry', () => ({
  useIndustryStore: () => ({
    currentIndustryId: '',
    switchIndustry: vi.fn(() => Promise.resolve(true)),
    error: null,
  }),
}))
import { setActivePinia, createPinia } from 'pinia'
import { useModsStore } from '@/stores/mods'
import { XCAGI_ACTIVE_EXTENSION_MOD_ID_KEY } from '@/utils/xcagiStorageKeys'

describe('mods store smoke', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.stubGlobal('fetch', vi.fn())
    localStorage.removeItem(XCAGI_ACTIVE_EXTENSION_MOD_ID_KEY)
  })

  it('initialize 成功后写入 mods 并标记 isLoaded', async () => {
    // initialize：fetchModsWithRetry → GET /api/mods/，再 fetchModRoutes → GET /api/mods/routes（apiFetch → fetch）
    global.fetch
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true,
          data: [
            {
              id: 'taiyangniao-pro',
              name: '太阳鸟pro',
              version: '1.0.0',
              author: '',
              description: '',
            },
          ],
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true,
          data: [{ mod_id: 'taiyangniao-pro', routes_path: 'mods/taiyangniao-pro/frontend/routes' }],
        }),
      })

    const store = useModsStore()
    await store.initialize()

    expect(store.isLoaded).toBe(true)
    expect(store.mods.length).toBe(1)
    expect(store.mods[0].id).toBe('taiyangniao-pro')
    expect(global.fetch).toHaveBeenNthCalledWith(
      1,
      '/api/mods/',
      expect.objectContaining({ credentials: 'include' })
    )
  })

  it('登录权益覆盖 localStorage 中的旧 activeModId', async () => {
    localStorage.setItem(XCAGI_ACTIVE_EXTENSION_MOD_ID_KEY, 'xcagi-erp-domain-bridge')
    global.fetch
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true,
          data: [
            {
              id: 'taiyangniao-pro',
              name: '太阳鸟pro',
              version: '1.0.0',
              author: '',
              description: '',
              primary: true,
              industry: { id: '考勤', name: '考勤' },
            },
            {
              id: 'sz-qsm-pro',
              name: '全塑美pro',
              version: '1.0.0',
              author: '',
              description: '',
            },
          ],
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ success: true, data: [] }),
      })

    const store = useModsStore()
    await store.initialize(true, {
      entitledModIds: ['taiyangniao-pro', 'sz-qsm-pro'],
      forceFromEntitlements: true,
    })

    expect(store.activeModId).toBe('taiyangniao-pro')
    expect(localStorage.getItem(XCAGI_ACTIVE_EXTENSION_MOD_ID_KEY)).toBe('taiyangniao-pro')
  })

  it('SUNBIRD 账号无 entitled 时仍强制太阳鸟 Mod', async () => {
    localStorage.setItem(XCAGI_ACTIVE_EXTENSION_MOD_ID_KEY, 'xcagi-erp-domain-bridge')
    global.fetch
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true,
          data: [
            {
              id: 'taiyangniao-pro',
              name: '太阳鸟pro',
              version: '1.0.0',
              author: '',
              description: '',
              primary: true,
              industry: { id: '考勤', name: '考勤' },
            },
          ],
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ success: true, data: [] }),
      })

    const store = useModsStore()
    await store.initialize(true, {
      entitledModIds: [],
      forceFromEntitlements: true,
      accountUsername: 'SUNBIRD',
    })

    expect(store.activeModId).toBe('taiyangniao-pro')
  })
})
