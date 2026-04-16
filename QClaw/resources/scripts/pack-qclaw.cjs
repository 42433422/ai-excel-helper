#!/usr/bin/env node

/**
 * 问题反馈打包脚本：将配置目录（~/.qclaw）和日志目录打包成一个压缩包
 *
 * 压缩包结构：
 *   ├── config/      ← ~/.qclaw 目录内容（排除 node_modules / .git）
 *   └── logs/        ← 应用日志（按平台自动识别路径）
 *
 * 日志目录：
 *   - macOS:   ~/Library/Logs/QClaw/
 *   - Windows: %APPDATA%\QClaw\logs\
 *   - Linux:   ~/.config/QClaw/logs/
 *
 * 支持两种使用方式：
 *   1. 直接执行：node scripts/pack-qclaw.cjs [输出路径]
 *   2. 作为模块导入：const { packQclaw } = require('./scripts/pack-qclaw.cjs')
 *
 * 兼容 macOS / Windows / Linux
 */

const { existsSync, mkdirSync, statSync, readdirSync, cpSync, rmSync } = require('fs')
const { resolve, dirname, join, basename } = require('path')
const { homedir, tmpdir } = require('os')
const { execFile } = require('child_process')

// ============================================
// 配置
// ============================================

/** 用户配置目录 ~/.qclaw */
const CONFIG_DIR = resolve(homedir(), '.qclaw')

/** 应用产品名（与 electron-builder 配置一致） */
const APP_NAME = 'QClaw'

/**
 * 获取日志目录路径（与 Electron app.getPath('logs') 保持一致）
 */
function getLogsDir() {
  switch (process.platform) {
    case 'darwin':
      return join(homedir(), 'Library', 'Logs', APP_NAME)
    case 'win32':
      return join(process.env.APPDATA || join(homedir(), 'AppData', 'Roaming'), APP_NAME, 'logs')
    default:
      // Linux
      return join(process.env.XDG_CONFIG_HOME || join(homedir(), '.config'), APP_NAME, 'logs')
  }
}

const LOGS_DIR = getLogsDir()

/** 打包时需要排除的目录 */
const EXCLUDED_NAMES = new Set(['node_modules', '.git'])

/**
 * 安全地创建 staging 临时目录
 * Windows 下 Temp 目录可能因杀毒软件、GPO 策略等原因无法写入，
 * 此函数会依次尝试多个候选路径，确保找到一个可写的位置
 */
function createSafeStagingDir(dirName) {
  // 候选基础目录列表（按优先级排序）
  const candidates =
    process.platform === 'win32'
      ? [
          tmpdir(),
          join(process.env.USERPROFILE || homedir(), 'AppData', 'Local', 'Temp'),
          join(homedir(), '.qclaw-tmp'),
        ]
      : [tmpdir(), '/tmp', join(homedir(), '.qclaw-tmp')]

  // 去重
  const seen = new Set()
  const uniqueCandidates = candidates.filter((p) => {
    const normalized = resolve(p)
    if (seen.has(normalized)) return false
    seen.add(normalized)
    return true
  })

  for (const base of uniqueCandidates) {
    const target = join(base, dirName)
    try {
      mkdirSync(target, { recursive: true })
      // 验证确实可写：尝试在其中创建并删除一个测试文件
      const testFile = join(target, '.write-test')
      require('fs').writeFileSync(testFile, 'test')
      require('fs').unlinkSync(testFile)
      console.log(`[pack-qclaw] 临时目录：${target}`)
      return target
    } catch (err) {
      console.warn(`[pack-qclaw] ⚠️ 无法使用临时目录 ${target}：${err.message}`)
    }
  }

  throw new Error(
    `无法创建临时工作目录，所有候选路径均不可写：\n` +
      uniqueCandidates.map((p) => `  - ${join(p, dirName)}`).join('\n') +
      `\n\n请尝试以下解决办法：\n` +
      `  以管理员身份运行应用\n`
  )
}

// ============================================
// 工具函数
// ============================================

/**
 * 格式化日期为 YYYYMMDD-HHmmss
 */
function formatDate(date) {
  const pad = (n) => String(n).padStart(2, '0')
  return (
    `${date.getFullYear()}${pad(date.getMonth() + 1)}${pad(date.getDate())}` +
    `-${pad(date.getHours())}${pad(date.getMinutes())}${pad(date.getSeconds())}`
  )
}

/**
 * 格式化字节数
 */
function formatBytes(bytes) {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

/**
 * 获取桌面路径（Windows/macOS 兼容）
 * 优先使用 Electron app.getPath('desktop')，否则回退到 ~/Desktop
 */
function getDesktopPath() {
  try {
    // 在 Electron 主进程中可以直接使用 app
    const { app } = require('electron')
    return app.getPath('desktop')
  } catch {
    // 非 Electron 环境（直接用 node 执行时）回退到 ~/Desktop
    return join(homedir(), 'Desktop')
  }
}

/**
 * 递归复制目录，排除指定的子目录
 */
function copyDirFiltered(src, dest) {
  if (!existsSync(src)) return false

  mkdirSync(dest, { recursive: true })

  const entries = readdirSync(src, { withFileTypes: true })
  for (const entry of entries) {
    if (EXCLUDED_NAMES.has(entry.name)) continue
    const srcPath = join(src, entry.name)
    const destPath = join(dest, entry.name)
    cpSync(srcPath, destPath, { recursive: true })
  }
  return true
}

/**
 * 使用 shell 命令执行打包
 */
function execCommand(cmd, args, options = {}) {
  return new Promise((resolve, reject) => {
    execFile(cmd, args, { timeout: 5 * 60 * 1000, ...options }, (error, stdout, stderr) => {
      if (error) {
        reject(new Error(`命令执行失败：${error.message}\n${stderr}`))
      } else {
        resolve({ stdout, stderr })
      }
    })
  })
}

// ============================================
// 核心打包函数
// ============================================

/**
 * 打包配置和日志到指定路径
 * @param {string} [outputPath] 输出文件路径，不传则输出到桌面
 * @returns {Promise<{ outputFile: string, size: number, sizeFormatted: string }>}
 */
async function packQclaw(outputPath) {
  const desktopPath = getDesktopPath()
  const timestamp = formatDate(new Date())

  // 输出统一为 .zip 格式（Windows PowerShell 仅支持 .zip，保持一致）
  const outputFile = outputPath
    ? resolve(outputPath)
    : resolve(desktopPath, `qclaw-feedback-${timestamp}.zip`)

  console.log('\n[pack-qclaw] 🔧 开始打包问题反馈数据 ...')
  console.log(`[pack-qclaw] 配置目录：${CONFIG_DIR}${existsSync(CONFIG_DIR) ? '' : ' (不存在)'}`)
  console.log(`[pack-qclaw] 日志目录：${LOGS_DIR}${existsSync(LOGS_DIR) ? '' : ' (不存在)'}`)
  console.log(`[pack-qclaw] 输出文件：${outputFile}`)

  // 至少需要一个目录存在
  if (!existsSync(CONFIG_DIR) && !existsSync(LOGS_DIR)) {
    throw new Error(`配置目录和日志目录均不存在：\n  配置：${CONFIG_DIR}\n  日志：${LOGS_DIR}`)
  }

  // 确保输出目录存在
  const outputDir = dirname(outputFile)
  if (!existsSync(outputDir)) {
    mkdirSync(outputDir, { recursive: true })
    console.log(`[pack-qclaw] 已创建输出目录：${outputDir}`)
  }

  // 创建临时 staging 目录，组织好两个子文件夹
  const stagingDirName = `qclaw-feedback-${timestamp}-${process.pid}`
  const stagingDir = createSafeStagingDir(stagingDirName)
  const stagingConfig = join(stagingDir, 'config')
  const stagingLogs = join(stagingDir, 'logs')

  try {
    console.log('[pack-qclaw] 正在收集文件...\n')

    // 复制 config（~/.qclaw，排除 node_modules/.git）
    if (existsSync(CONFIG_DIR)) {
      console.log('[pack-qclaw]   📁 复制配置文件 ...')
      copyDirFiltered(CONFIG_DIR, stagingConfig)
    } else {
      console.log('[pack-qclaw]   ⚠️  配置目录不存在，跳过')
    }

    // 复制 logs
    if (existsSync(LOGS_DIR)) {
      console.log('[pack-qclaw]   📁 复制日志文件 ...')
      cpSync(LOGS_DIR, stagingLogs, { recursive: true })
    } else {
      console.log('[pack-qclaw]   ⚠️  日志目录不存在，跳过')
    }

    // 打包
    console.log('[pack-qclaw]   📦 正在压缩 ...\n')
    const isWindows = process.platform === 'win32'

    if (isWindows) {
      // Windows：使用 PowerShell Compress-Archive
      const entries = readdirSync(stagingDir).map((name) => `"${join(stagingDir, name)}"`)
      if (entries.length === 0) {
        throw new Error('staging 目录为空，没有可打包的文件')
      }
      const pathList = entries.join(',')
      const psScript = `Compress-Archive -Path ${pathList} -DestinationPath "${outputFile}" -Force`
      await execCommand('powershell.exe', ['-NoProfile', '-NonInteractive', '-Command', psScript])
    } else {
      // macOS / Linux：使用 zip 命令（macOS 自带，比 tar.gz 更通用）
      await execCommand('zip', ['-r', '-q', outputFile, '.'], { cwd: stagingDir })
    }

    // 检查输出文件
    if (!existsSync(outputFile)) {
      throw new Error(`打包命令已执行但输出文件未生成：${outputFile}`)
    }

    const size = statSync(outputFile).size
    const sizeFormatted = formatBytes(size)

    console.log(`[pack-qclaw] ✅ 打包完成！`)
    console.log(`[pack-qclaw] 文件路径：${outputFile}`)
    console.log(`[pack-qclaw] 文件大小：${sizeFormatted}\n`)

    return { outputFile, size, sizeFormatted }
  } catch (packError) {
    // 打包失败时的降级方案：直接用 zip 命令压缩 ~/.qclaw 到 ~/Downloads
    console.error(`[pack-qclaw] ❌ 正式打包失败：${packError.message}`)
    console.log('[pack-qclaw] 🔄 尝试降级方案：直接压缩 ~/.qclaw 目录 ...')

    if (process.platform === 'win32') {
      // Windows 不支持此降级方案，直接抛出原错误
      throw packError
    }

    try {
      const fallbackTimestamp = formatDate(new Date())
      const downloadsDir = join(homedir(), 'Downloads')
      const fallbackFile = join(downloadsDir, `qclaw_backup_${fallbackTimestamp}.zip`)

      // 确保 Downloads 目录存在
      if (!existsSync(downloadsDir)) {
        mkdirSync(downloadsDir, { recursive: true })
      }

      await execCommand('zip', ['-r', '-q', fallbackFile, '.qclaw'], { cwd: homedir() })

      if (!existsSync(fallbackFile)) {
        throw new Error('降级打包也未生成文件')
      }

      const size = statSync(fallbackFile).size
      const sizeFormatted = formatBytes(size)

      console.log(`[pack-qclaw] ✅ 降级打包完成！`)
      console.log(`[pack-qclaw] 文件路径：${fallbackFile}`)
      console.log(`[pack-qclaw] 文件大小：${sizeFormatted}`)
      console.log(`[pack-qclaw] ⚠️  注意：降级包仅包含 ~/.qclaw，不含日志文件\n`)

      return { outputFile: fallbackFile, size, sizeFormatted }
    } catch (fallbackError) {
      // 降级方案也失败了，抛出原始错误
      console.error(`[pack-qclaw] 降级打包方案失败：${fallbackError.message}`)
      throw packError
    }
  } finally {
    // 清理临时目录
    try {
      rmSync(stagingDir, { recursive: true, force: true })
    } catch {
      // 清理失败不影响主流程
    }
  }
}

// ============================================
// 导出（供 Electron IPC 调用）
// ============================================

module.exports = { packQclaw }

// ============================================
// 直接执行入口
// ============================================

if (require.main === module) {
  const outputArg = process.argv[2]
  packQclaw(outputArg).catch((err) => {
    console.error(`\n[pack-qclaw] 打包失败：${err.message}`)
    process.exit(1)
  })
}