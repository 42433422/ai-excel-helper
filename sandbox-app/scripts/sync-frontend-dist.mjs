/**
 * 将 FHD 前端构建产物挂到 sandbox-app/web_static（目录联接 / 符号链接）。
 * 用法：node scripts/sync-frontend-dist.mjs
 * 前置：在 FHD/frontend 执行 npm run build（产物默认 templates/vue-dist）
 */
import fs from 'fs'
import path from 'path'
import { fileURLToPath } from 'url'
import { execSync } from 'child_process'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const sandboxRoot = path.resolve(__dirname, '..')
const repoRoot = path.resolve(sandboxRoot, '..')
const src = path.join(repoRoot, 'templates', 'vue-dist')
const dest = path.join(sandboxRoot, 'web_static')

if (!fs.existsSync(path.join(src, 'index.html'))) {
  console.error('[sandbox] 缺少构建产物:', src)
  console.error('  请先: cd frontend && npm run build')
  process.exit(1)
}

if (fs.existsSync(dest)) {
  fs.rmSync(dest, { recursive: true, force: true })
}

try {
  if (process.platform === 'win32') {
    execSync(`cmd /c mklink /J "${dest}" "${src}"`, { stdio: 'inherit' })
    console.log('[sandbox] Junction 已创建:', dest, '->', src)
  } else {
    fs.symlinkSync(src, dest, 'dir')
    console.log('[sandbox] Symlink 已创建:', dest, '->', src)
  }
} catch (e) {
  console.warn('[sandbox] 联接失败，回退为复制目录…', e.message)
  fs.cpSync(src, dest, { recursive: true })
  console.log('[sandbox] 已复制到:', dest)
}
