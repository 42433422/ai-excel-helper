import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { defineConfig } from 'vitest/config'
import vue from '@vitejs/plugin-vue'
import { webcrypto } from 'node:crypto'

const __dirname = path.dirname(fileURLToPath(import.meta.url))

// 兼容部分 Windows/Node 环境：Vitest 启动阶段需要 crypto.getRandomValues。
if (!globalThis.crypto || typeof globalThis.crypto.getRandomValues !== 'function') {
  Object.defineProperty(globalThis, 'crypto', {
    value: webcrypto,
    configurable: true,
  })
}

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
      '@mod-views/xcagi-planner-bridge/ChatView.vue': path.resolve(
        __dirname,
        './src/test-stubs/ModChatViewStub.vue'
      ),
    },
  },
  test: {
    setupFiles: ['./vitest.setup.ts'],
    globals: true,
    environment: 'jsdom',
    testTimeout: 30_000,
    include: [
      'src/**/*.test.js',
      'src/**/*.test.ts',
      'tests/**/*.test.js',
      'tests/**/*.test.ts',
      'tests/smoke/**/*.test.js',
    ],
    exclude: [
      '**/node_modules/**',
      '**/dist/**',
      // CI 无 Mod 视图构建产物；本地有 mods 时可跑
      ...(process.env.CI === 'true' ? ['src/views/ChatView.proTaskStatus.test.js'] : []),
    ],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
      include: ['src/**/*'],
      exclude: ['src/**/*.test.js', 'src/**/*.test.ts'],
      /** 全仓含大量 .vue 占位行；阈值略高于当前基线，新增 utils/store 单测后应稳定通过 */
      thresholds: {
        lines: 18,
        branches: 10,
        functions: 12,
        statements: 18,
      },
    },
  },
})
