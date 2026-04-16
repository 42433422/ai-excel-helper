#!/usr/bin/env node

/**
 * Windows 安装后 OpenClaw tar 解压脚本 (fallback 路径)
 *
 * 由 NSIS installer.nsh 的 customInstall 宏调用，
 * 仅在系统无 tar.exe 时作为 fallback 使用。
 * 通过 QClaw.exe (ELECTRON_RUN_AS_NODE=1 模式) 执行。
 *
 * 支持两种格式:
 *   1. 多分片: openclaw_0.tar ~ openclaw_N.tar + openclaw_manifest.json
 *   2. 单文件: openclaw.tar (向后兼容)
 *
 * 用法: QClaw.exe <本脚本路径> <安装目录>
 *
 * 效果:
 *   输入: $INSTDIR/resources/openclaw_*.tar 或 openclaw.tar
 *   输出: $INSTDIR/resources/openclaw/ (还原为散文件目录)
 *   tar 文件解压后自动删除
 *
 * 依赖: 从 app.asar 内加载 tar npm 包 (Electron 内置 ASAR 透明读取支持)
 */

const fs = require('fs')
const path = require('path')

// ============================================================
// 参数解析
// ============================================================

const instDir = process.argv[2]

if (!instDir) {
  console.error('[unpack-openclaw] 错误: 缺少安装目录参数')
  console.error('[unpack-openclaw] 用法: QClaw.exe unpack-openclaw.cjs <安装目录>')
  process.exit(1)
}

const resourcesDir = path.join(instDir, 'resources')
const manifestFile = path.join(resourcesDir, 'openclaw_manifest.json')
const legacyTarFile = path.join(resourcesDir, 'openclaw.tar')
const appAsar = path.join(resourcesDir, 'app.asar')

// ============================================================
// 加载 tar 模块
// ============================================================

/**
 * 从多个可能的路径加载 tar 模块
 * 优先级:
 *   1. ASAR 内的 node_modules (Electron 内置 ASAR 读取支持)
 *   2. 全局 require (如果 tar 碰巧在 NODE_PATH 中)
 */
function loadTarModule() {
  // 策略 1: 从 app.asar 内加载
  const asarTarPath = path.join(appAsar, 'node_modules', 'tar')
  try {
    return require(asarTarPath)
  } catch {
    // ASAR 加载失败，继续尝试
  }

  // 策略 2: 直接 require (可能在 NODE_PATH 或其他路径中)
  try {
    return require('tar')
  } catch {
    // 也失败
  }

  console.error('[unpack-openclaw] 错误: 无法加载 tar 模块')
  console.error(`[unpack-openclaw] 尝试路径: ${asarTarPath}`)
  process.exit(1)
}

// ============================================================
// 收集 tar 文件
// ============================================================

function collectTarFiles() {
  // 优先检查多分片格式
  if (fs.existsSync(manifestFile)) {
    try {
      const manifest = JSON.parse(fs.readFileSync(manifestFile, 'utf-8'))
      const files = []
      for (const shard of manifest.shards) {
        const tarPath = path.join(resourcesDir, shard.file)
        if (fs.existsSync(tarPath)) {
          files.push(tarPath)
        }
      }
      if (files.length > 0) {
        console.log(`[unpack-openclaw] 检测到多分片格式: ${files.length} 个分片`)
        return files
      }
    } catch {
      // manifest 解析失败，继续尝试其他格式
    }
  }

  // 无 manifest 时，扫描 openclaw_*.tar 文件
  const shardFiles = []
  for (let i = 0; i < 20; i++) {
    const f = path.join(resourcesDir, `openclaw_${i}.tar`)
    if (fs.existsSync(f)) {
      shardFiles.push(f)
    }
  }
  if (shardFiles.length > 0) {
    console.log(`[unpack-openclaw] 检测到分片文件 (无 manifest): ${shardFiles.length} 个分片`)
    return shardFiles
  }

  // 向后兼容: 单个 openclaw.tar
  if (fs.existsSync(legacyTarFile)) {
    console.log('[unpack-openclaw] 检测到旧版单文件格式: openclaw.tar')
    return [legacyTarFile]
  }

  console.error('[unpack-openclaw] 错误: 未找到任何 tar 文件')
  process.exit(1)
}

// ============================================================
// 执行解压
// ============================================================

try {
  const tarFiles = collectTarFiles()

  console.log(`[unpack-openclaw] 目标目录: ${resourcesDir}`)

  const tar = loadTarModule()
  const startTime = Date.now()

  // 确保 openclaw 目录存在
  const openclawDir = path.join(resourcesDir, 'openclaw')
  fs.mkdirSync(openclawDir, { recursive: true })
  fs.mkdirSync(path.join(openclawDir, 'node_modules'), { recursive: true })

  // 逐个解压所有分片 (Node.js fallback 不做并行，保持简单可靠)
  for (const tarFile of tarFiles) {
    const shardName = path.basename(tarFile)
    console.log(`[unpack-openclaw] 解压分片: ${shardName}`)

    tar.extract({
      file: tarFile,
      cwd: resourcesDir,
      sync: true,
    })

    // 解压成功后删除 tar 文件
    fs.unlinkSync(tarFile)
  }

  // 清理 manifest 文件
  if (fs.existsSync(manifestFile)) {
    fs.unlinkSync(manifestFile)
  }

  const elapsed = ((Date.now() - startTime) / 1000).toFixed(1)
  console.log(`[unpack-openclaw] 全部解压完成 (${elapsed}s)`)

  // 验证解压结果
  if (!fs.existsSync(openclawDir)) {
    console.error(`[unpack-openclaw] 错误: 解压后目录不存在: ${openclawDir}`)
    process.exit(1)
  }

  console.log('[unpack-openclaw] 完成 ✓')
  process.exit(0)
} catch (err) {
  console.error(`[unpack-openclaw] 解压失败: ${err.message}`)
  process.exit(1)
}
