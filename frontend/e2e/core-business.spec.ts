import { test, expect } from '@playwright/test'

test.describe('Core business flows (basic)', () => {
  test('chat send triggers backend request', async ({ page }) => {
    // Intercept AI chat endpoint and return canned response
    await page.route('**/api/ai/chat*', (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ success: true, data: { reply: 'ok' } }),
      })
    )

    await page.goto('/', { waitUntil: 'domcontentloaded', timeout: 30_000 })
    await expect(page.locator('#app')).toBeVisible()
    // wait for app ready marker
    await expect(page.locator('.app-shell.is-ready')).toBeVisible({ timeout: 20_000 })

    // Call the page-level chat send bridge if available
    const hasBridge = await page.evaluate(() => {
      return typeof (window as any).__VUE_CHAT_SEND__ === 'function'
    })
    if (hasBridge) {
      // trigger send via bridge; wait for the network call to be observed
      await page.evaluate(() => {
        ;(window as any).__VUE_CHAT_SEND__('测试消息 from E2E')
      })
      await page.waitForResponse((resp) => resp.url().includes('/api/ai/chat') && resp.status() === 200, {
        timeout: 5000,
      })
    } else {
      test.skip('No chat bridge available in this build')
    }
  })

  test('mods list loads and displays mod name', async ({ page }) => {
    await page.route('**/api/mods/**', (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: [{ id: 'm1', name: 'TestMod', version: '1.0', author: '', description: '' }],
        }),
      })
    )

    await page.goto('/', { waitUntil: 'domcontentloaded', timeout: 30_000 })
    await expect(page.locator('.app-shell.is-ready')).toBeVisible({ timeout: 20_000 })
    // best-effort: look for the mod name text somewhere in the page
    await expect(page.locator('text=TestMod')).toBeVisible({ timeout: 5000 })
  })

  test('pro mode toggle (dispatch event)', async ({ page }) => {
    await page.goto('/', { waitUntil: 'domcontentloaded', timeout: 30_000 })
    await expect(page.locator('.app-shell.is-ready')).toBeVisible({ timeout: 20_000 })
    // dispatch a custom pro-mode-changed event and ensure page doesn't crash
    await page.evaluate(() => {
      window.dispatchEvent(new CustomEvent('xcagi:pro-mode-changed', { detail: { enabled: true } }))
    })
    // no uncaught exceptions implies success; also ensure app root still visible
    await expect(page.locator('#app')).toBeVisible()
  })
})

