import { test, expect } from '@playwright/test'

test.describe('In-app navigation', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/', { waitUntil: 'domcontentloaded', timeout: 30_000 })
    await expect(page.locator('#app')).toBeVisible()
  })

  test('sidebar menu has at least one navigable item when shell is ready', async ({ page }) => {
    const ready = page.locator('.app-shell.is-ready')
    if (!(await ready.isVisible({ timeout: 20_000 }).catch(() => false))) {
      test.skip(true, 'App shell not ready (backend or auth may be required)')
    }
    const items = page.locator('.sidebar .menu-item')
    await expect(items.first()).toBeVisible()
    expect(await items.count()).toBeGreaterThan(0)
  })

  test('login help route is reachable', async ({ page }) => {
    await page.goto('/login/help', { waitUntil: 'domcontentloaded' })
    await expect(page.locator('#app')).toBeVisible()
    await expect(page).toHaveURL(/\/login\/help/)
  })
})
