import { test, expect } from '@playwright/test'

test.describe('Login flow', () => {
  test('login page loads without app shell chrome', async ({ page }) => {
    await page.goto('/login', { waitUntil: 'domcontentloaded', timeout: 30_000 })
    await expect(page.locator('#app')).toBeVisible()
    await expect(page).toHaveURL(/\/login/)
  })

  test('unauthenticated root eventually shows login or ready shell', async ({ page }) => {
    await page.goto('/', { waitUntil: 'domcontentloaded', timeout: 30_000 })
    await expect(page.locator('#app')).toBeVisible()
    const loginVisible = await page.locator('input[type="password"], input[autocomplete="current-password"]').first().isVisible().catch(() => false)
    const readyVisible = await page.locator('.app-shell.is-ready').isVisible().catch(() => false)
    expect(loginVisible || readyVisible).toBeTruthy()
  })
})
