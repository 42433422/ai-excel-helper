import { test, expect } from '@playwright/test';

const DB_READ_TOKEN = '61408693';

test.describe('XCAGI 前端冒烟 @5001', () => {
  test('首页可加载且主壳在超时内可见（非持久 opacity:0）', async ({ page, request }) => {
    const pageErrors: string[] = [];
    page.on('pageerror', (err) => {
      pageErrors.push(err.stack || err.message);
    });

    await page.goto('/', { waitUntil: 'domcontentloaded', timeout: 30_000 });
    await expect(page.locator('#app')).toBeVisible();

    // 与 App.vue STARTUP_FAILSAFE_MS 对齐：最坏约 12s 也应 is-ready
    await expect(page.locator('.app-shell.is-ready')).toBeVisible({ timeout: 20_000 });
    await expect(page.locator('.sidebar')).toBeVisible();
    await expect(page.locator('.sidebar .menu-item').first()).toBeVisible();

    const apiProbe = await request.get('/api/health', { timeout: 15_000 }).catch(() => null);
    if (!apiProbe || !apiProbe.ok()) {
      test.info().annotations.push({
        type: 'notice',
        description:
          '经 Vite 代理的 /api/health 未成功：多为 5000 后端未启动或仍初始化。页面应仍能出壳，但聊天等功能会失效。',
      });
    }

    // 未捕获的 JS 异常才会白屏；网络/API 报错在控制台常见，不据此判失败
    expect(pageErrors, `pageerror: ${pageErrors.join('\n')}`).toEqual([]);

    const industryResp = await request.get('/api/system/industry', { timeout: 15_000 });
    expect(industryResp.ok(), 'industry API should be reachable').toBeTruthy();
    const industryJson = await industryResp.json();
    const industryName = String(industryJson?.data?.name || '').trim();
    expect(industryName.length, 'industry name should not be empty').toBeGreaterThan(0);
  });

  test('http://localhost:5001 与 127.0.0.1 行为一致（Windows IPv6 localhost）', async ({
    page,
  }) => {
    await page.goto('http://localhost:5001/', { waitUntil: 'domcontentloaded', timeout: 30_000 });
    await expect(page.locator('#app')).toBeVisible();
    await expect(page.locator('.app-shell.is-ready')).toBeVisible({ timeout: 20_000 });
  });

  test('顶栏副窗可打开并以 Escape 关闭', async ({ page }) => {
    await page.goto('/', { waitUntil: 'domcontentloaded', timeout: 30_000 });
    await expect(page.locator('.app-shell.is-ready')).toBeVisible({ timeout: 20_000 });
    await page.locator('.assistant-float-toggle').click();
    await expect(page.locator('#xcagi-assistant-float-panel')).toBeVisible();
    await expect(page.locator('#xcagi-assistant-float-title')).toBeVisible();
    await page.keyboard.press('Escape');
    await expect(page.locator('#xcagi-assistant-float-panel')).toHaveCount(0);
  });

  test('并发 API 不被单点阻塞（products/list + system/industries）', async ({ request }) => {
    const jobs: Promise<any>[] = [];
    for (let i = 0; i < 10; i += 1) {
      jobs.push(
        request.get('/api/products/list?page=1&per_page=1', {
          timeout: 20_000,
          headers: { 'X-FHD-Db-Read-Token': DB_READ_TOKEN },
        })
      );
      jobs.push(request.get('/api/system/industries', { timeout: 20_000 }));
    }
    const responses = await Promise.all(jobs);
    const bad: string[] = [];
    for (const [idx, resp] of responses.entries()) {
      if (!resp.ok()) {
        bad.push(`#${idx}:${resp.status()}`);
      }
    }
    expect(bad, `all concurrent API calls should be 200, got ${bad.join(',')}`).toEqual([]);
  });
});
