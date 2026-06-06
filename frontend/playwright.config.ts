import { defineConfig, devices } from '@playwright/test';

/**
 * 冒烟：需本机已启动 Vite :5001（及可选 FastAPI :5000）。
 * 运行：cd frontend && npx playwright install chromium && npm run test:smoke:5001
 */
export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: 0,
  workers: 1,
  reporter: [['list']],
  timeout: 45_000,
  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL || 'http://127.0.0.1:5001',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
});
