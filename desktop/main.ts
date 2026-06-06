import { BrowserWindow, Menu, Tray, app, dialog, ipcMain, nativeImage, shell } from 'electron'
import { ChildProcessWithoutNullStreams, spawn } from 'node:child_process'
import crypto from 'node:crypto'
import fs from 'node:fs'
import net from 'node:net'
import { networkInterfaces } from 'node:os'
import path from 'node:path'
import { checkForUpdates, configureUpdater, installUpdate } from './updater'

const APP_NAME = 'XCAGI'
const DEFAULT_PORT = Number(process.env.XCAGI_DESKTOP_PORT || 5000)

type ProductSku = 'personal' | 'enterprise'

const SKU_RUNTIME_EDITION: Record<ProductSku, string> = {
  personal: 'minimal',
  enterprise: 'full'
}

const SKU_UPDATE_URL: Record<ProductSku, string> = {
  personal: 'https://update.xcagi.com/releases/stable/personal/',
  enterprise: 'https://update.xcagi.com/releases/stable/enterprise/'
}

function readPackagedProductSku(): ProductSku | null {
  if (!app.isPackaged) return null
  const candidates = [
    path.join(process.resourcesPath, 'product-sku.json'),
    path.join(process.resourcesPath, 'backend', 'product-sku.json')
  ]
  for (const filePath of candidates) {
    try {
      if (!fs.existsSync(filePath)) continue
      const raw = JSON.parse(fs.readFileSync(filePath, 'utf8')) as { sku?: string }
      const sku = String(raw.sku || '').trim().toLowerCase()
      if (sku === 'personal' || sku === 'enterprise') {
        return sku
      }
    } catch {
      /* ignore */
    }
  }
  return null
}

function backendEditionEnv(): Record<string, string> {
  const sku = readPackagedProductSku()
  if (!sku) {
    return {
      XCAGI_GENERIC_EDITION: '1',
      XCAGI_PLATFORM_SHELL: '1',
      XCAGI_DEFAULT_EDITION: 'generic'
    }
  }
  const edition = SKU_RUNTIME_EDITION[sku]
  const env: Record<string, string> = {
    XCAGI_PRODUCT_SKU: sku,
    XCAGI_PLATFORM_SHELL: '1',
    XCAGI_DEFAULT_EDITION: edition,
    XCAGI_EDITION: edition
  }
  if (edition === 'minimal') {
    env.XCAGI_MINIMAL_EDITION = '1'
  } else if (edition === 'generic') {
    env.XCAGI_GENERIC_EDITION = '1'
  }
  return env
}

let mainWindow: BrowserWindow | null = null
let backendProcess: ChildProcessWithoutNullStreams | null = null
let tray: Tray | null = null
let restartCount = 0

function repoRoot(): string {
  return app.isPackaged ? process.resourcesPath : path.resolve(__dirname, '..', '..')
}

/** 托盘与窗口图标：与 dist 同级打包的 resources（由 beforePack 生成）。 */
function shellIconPath(): string {
  const name = process.platform === 'win32' ? 'icon.ico' : 'icon.png'
  return path.join(__dirname, '..', 'resources', name)
}

function backendExecutable(): { command: string; args: string[]; cwd: string } {
  const dataDir = app.getPath('userData')
  if (!app.isPackaged) {
    const root = repoRoot()
    return {
      command: process.env.PYTHON || 'python',
      args: [
        path.join(root, 'XCAGI', 'run.py'),
        '--desktop',
        '--headless',
        '--host',
        '127.0.0.1',
        '--port',
        String(DEFAULT_PORT),
        '--data-dir',
        dataDir
      ],
      cwd: root
    }
  }

  const backendDir = path.join(process.resourcesPath, 'backend')
  const command =
    process.platform === 'win32'
      ? path.join(backendDir, 'xcagi-backend.exe')
      : path.join(backendDir, 'xcagi-backend')

  return {
    command,
    args: [
      '--desktop',
      '--headless',
      '--host',
      '127.0.0.1',
      '--port',
      String(DEFAULT_PORT),
      '--data-dir',
      dataDir
    ],
    cwd: path.dirname(command)
  }
}

function waitForPort(port: number, timeoutMs = 45_000): Promise<void> {
  const started = Date.now()
  return new Promise((resolve, reject) => {
    const attempt = () => {
      const socket = net.createConnection({ host: '127.0.0.1', port })
      socket.once('connect', () => {
        socket.end()
        resolve()
      })
      socket.once('error', () => {
        socket.destroy()
        if (Date.now() - started > timeoutMs) {
          reject(new Error(`后端端口 ${port} 在 ${timeoutMs}ms 内未就绪`))
          return
        }
        setTimeout(attempt, 500)
      })
    }
    attempt()
  })
}

type DesktopStartupMarks = {
  backendSpawnMs?: number
  tcp5000Ms?: number
  desktopStatusMs?: number
}

const startupMarks: DesktopStartupMarks = {}

function readPackagedAppVersion(): string {
  if (!app.isPackaged) return 'dev'
  const candidates = [
    path.join(process.resourcesPath, 'backend', 'version.txt'),
    path.join(process.resourcesPath, 'product-sku.json')
  ]
  for (const filePath of candidates) {
    try {
      if (!fs.existsSync(filePath)) continue
      const raw = fs.readFileSync(filePath, 'utf8').trim()
      if (filePath.endsWith('version.txt')) return raw || 'unknown'
      const json = JSON.parse(raw) as { sku?: string; schema_version?: number }
      return `${json.sku || 'enterprise'}-${json.schema_version ?? 1}`
    } catch {
      /* ignore */
    }
  }
  return app.getVersion()
}

function shouldClearFrontendCache(): boolean {
  const marker = path.join(app.getPath('userData'), 'frontend-cache-version.txt')
  const current = readPackagedAppVersion()
  try {
    const prev = fs.readFileSync(marker, 'utf8').trim()
    return prev !== current
  } catch {
    return true
  }
}

function markFrontendCacheCleared(): void {
  const marker = path.join(app.getPath('userData'), 'frontend-cache-version.txt')
  fs.writeFileSync(marker, readPackagedAppVersion(), 'utf8')
}

/** 分阶段就绪：TCP 后即可出窗；desktop/status 软等待，不阻塞 60s 全量 Mod。 */
async function waitForBackendStatus(port: number, timeoutMs = 15_000): Promise<boolean> {
  const started = Date.now()
  while (Date.now() - started <= timeoutMs) {
    try {
      const response = await fetch(`http://127.0.0.1:${port}/api/desktop/status`)
      if (response.ok) {
        startupMarks.desktopStatusMs = Date.now() - (startupMarks.backendSpawnMs ?? started)
        return true
      }
    } catch {
      /* backend still importing routers */
    }
    await new Promise(resolve => setTimeout(resolve, 400))
  }
  console.warn(`[xcagi-desktop] /api/desktop/status 未在 ${timeoutMs}ms 内就绪，仍加载前端`)
  return false
}

function startBackend(): void {
  if (backendProcess) {
    return
  }

  const executable = backendExecutable()
  if (app.isPackaged && !fs.existsSync(executable.command)) {
    void dialog.showErrorBox(APP_NAME, `找不到后端程序：${executable.command}`)
    return
  }

  startupMarks.backendSpawnMs = Date.now()
  backendProcess = spawn(executable.command, executable.args, {
    cwd: executable.cwd,
    env: {
      ...process.env,
      XCAGI_DESKTOP_MODE: '1',
      XCAGI_DATA_DIR: app.getPath('userData'),
      XCAGI_UVICORN_RELOAD: '0',
      ...backendEditionEnv(),
      PYTHONUTF8: '1'
    },
    windowsHide: true
  })

  backendProcess.stdout.on('data', data => process.stdout.write(`[xcagi-backend] ${data}`))
  backendProcess.stderr.on('data', data => process.stderr.write(`[xcagi-backend] ${data}`))
  backendProcess.on('exit', code => {
    backendProcess = null
    if (app.isQuitting) {
      return
    }
    restartCount += 1
    if (restartCount <= 3) {
      setTimeout(startBackend, 1500)
      return
    }
    void dialog.showErrorBox(APP_NAME, `后端服务已退出（code=${code}），请重启 XCAGI。`)
  })
}

function runBackendMigration(): Promise<void> {
  const executable = backendExecutable()
  return new Promise((resolve, reject) => {
    const child = spawn(executable.command, [...executable.args, '--migrate-only', '--backup'], {
      cwd: executable.cwd,
      env: {
        ...process.env,
        XCAGI_DESKTOP_MODE: '1',
        XCAGI_DATA_DIR: app.getPath('userData'),
        XCAGI_GENERIC_EDITION: '1',
        XCAGI_PLATFORM_SHELL: '1',
        PYTHONUTF8: '1'
      },
      windowsHide: true
    })
    let stderr = ''
    child.stderr.on('data', data => {
      stderr += String(data)
      process.stderr.write(`[xcagi-migrate] ${data}`)
    })
    child.stdout.on('data', data => process.stdout.write(`[xcagi-migrate] ${data}`))
    child.on('error', reject)
    child.on('exit', code => {
      if (code === 0) {
        resolve()
      } else {
        reject(new Error(`数据库迁移失败（code=${code}）: ${stderr}`))
      }
    })
  })
}

async function exportSupportBundleInteractive(): Promise<void> {
  try {
    const res = await fetch(`http://127.0.0.1:${DEFAULT_PORT}/api/desktop/support-bundle`)
    if (!res.ok) {
      void dialog.showErrorBox(APP_NAME, `导出失败：HTTP ${res.status}`)
      return
    }
    const buf = Buffer.from(await res.arrayBuffer())
    const iso = new Date().toISOString().replace(/[:.]/g, '-')
    const defaultPath = path.join(app.getPath('downloads'), `xcagi-support-${iso}.zip`)
    const win = BrowserWindow.getFocusedWindow() ?? mainWindow
    const saveOpts = {
      title: '导出诊断包',
      defaultPath,
      filters: [{ name: 'ZIP', extensions: ['zip'] }]
    }
    const { canceled, filePath } = win
      ? await dialog.showSaveDialog(win, saveOpts)
      : await dialog.showSaveDialog(saveOpts)
    if (canceled || !filePath) {
      return
    }
    await fs.promises.writeFile(filePath, buf)
    const parent = win ?? mainWindow
    const saved = {
      type: 'info' as const,
      title: APP_NAME,
      message: '诊断包已保存',
      detail: filePath
    }
    if (parent) {
      void dialog.showMessageBox(parent, saved)
    } else {
      void dialog.showMessageBox(saved)
    }
  } catch (error) {
    void dialog.showErrorBox(
      APP_NAME,
      error instanceof Error ? error.message : String(error)
    )
  }
}

function stopBackend(): void {
  const child = backendProcess
  backendProcess = null
  if (!child || child.killed) {
    return
  }
  child.kill(process.platform === 'win32' ? undefined : 'SIGTERM')
}

async function createWindow(): Promise<void> {
  const icon = shellIconPath()
  const winOpts: Electron.BrowserWindowConstructorOptions = {
    width: 1440,
    height: 920,
    minWidth: 1180,
    minHeight: 760,
    title: APP_NAME,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true
    }
  }
  if (fs.existsSync(icon)) {
    winOpts.icon = icon
  }
  winOpts.show = false
  winOpts.backgroundColor = '#f4f7fb'
  mainWindow = new BrowserWindow(winOpts)

  mainWindow.on('closed', () => {
    mainWindow = null
  })

  const bootStarted = Date.now()
  await waitForPort(DEFAULT_PORT)
  startupMarks.tcp5000Ms = Date.now() - bootStarted

  if (shouldClearFrontendCache()) {
    try {
      await mainWindow.webContents.session.clearCache()
      markFrontendCacheCleared()
    } catch {
      /* ignore */
    }
  }

  await mainWindow.loadURL(`http://127.0.0.1:${DEFAULT_PORT}/?shell=1`, {
    extraHeaders: 'Cache-Control: no-cache\r\n'
  })
  mainWindow.show()
  mainWindow.focus()

  void waitForBackendStatus(DEFAULT_PORT).then(ok => {
    console.info(
      '[xcagi-desktop] startup',
      JSON.stringify({
        ...startupMarks,
        desktopStatusOk: ok
      })
    )
  })

  configureUpdater(mainWindow, runBackendMigration)
}

function createMenu(): void {
  const template: Electron.MenuItemConstructorOptions[] = [
    {
      label: APP_NAME,
      submenu: [
        { label: '打开数据目录', click: () => void shell.openPath(app.getPath('userData')) },
        {
          label: '导出诊断包…',
          click: () => void exportSupportBundleInteractive()
        },
        { label: '检查更新', click: () => void checkForUpdates() },
        { type: 'separator' },
        { role: 'quit', label: '退出' }
      ]
    },
    { role: 'editMenu', label: '编辑' },
    { role: 'viewMenu', label: '视图' },
    { role: 'windowMenu', label: '窗口' }
  ]
  Menu.setApplicationMenu(Menu.buildFromTemplate(template))
}

function createTray(): void {
  const iconPath = shellIconPath()
  if (!fs.existsSync(iconPath)) {
    return
  }
  const image = nativeImage.createFromPath(iconPath)
  tray = new Tray(image)
  tray.setToolTip(APP_NAME)
  tray.setContextMenu(
    Menu.buildFromTemplate([
      { label: '显示 XCAGI', click: () => mainWindow?.show() },
      { label: '打开数据目录', click: () => void shell.openPath(app.getPath('userData')) },
      { type: 'separator' },
      { label: '退出', click: () => app.quit() }
    ])
  )
}

const gotLock = app.requestSingleInstanceLock()
if (!gotLock) {
  app.quit()
} else {
  app.on('second-instance', () => {
    if (mainWindow) {
      if (mainWindow.isMinimized()) mainWindow.restore()
      mainWindow.focus()
    }
  })

  app.on('before-quit', () => {
    app.isQuitting = true
    stopBackend()
  })

  app.whenReady().then(async () => {
    const sku = readPackagedProductSku()
    if (sku && !process.env.XCAGI_UPDATE_URL) {
      process.env.XCAGI_UPDATE_URL = SKU_UPDATE_URL[sku]
    }
    function getLanIPv4(): string {
      const nets = networkInterfaces()
      for (const name of Object.keys(nets)) {
        for (const iface of nets[name] || []) {
          if (iface.family === 'IPv4' && !iface.internal) {
            return iface.address
          }
        }
      }
      return '127.0.0.1'
    }

    ipcMain.handle('xcagi:pairing-qr', async () => {
      const host = getLanIPv4()
      const port = DEFAULT_PORT
      const nonce = crypto.randomBytes(12).toString('base64url')
      const exp = Math.floor(Date.now() / 1000) + 300
      try {
        const res = await fetch(`http://127.0.0.1:${port}/api/mobile/v1/pairing/issue`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ host, port })
        })
        if (res.ok) {
          const json = (await res.json()) as { data?: { nonce?: string; exp?: number; host?: string; port?: number } }
          if (json?.data?.nonce) {
            return JSON.stringify(json.data)
          }
        }
      } catch {
        /* backend offline — return local payload */
      }
      return JSON.stringify({ host, port, nonce, exp })
    })

    ipcMain.handle('xcagi:get-data-dir', () => app.getPath('userData'))
    ipcMain.handle('xcagi:export-support-bundle', () => exportSupportBundleInteractive())
    ipcMain.handle('xcagi:check-for-updates', () => checkForUpdates())
    ipcMain.handle('xcagi:install-update', () => installUpdate(runBackendMigration))

    createMenu()
    createTray()
    startBackend()
    try {
      await createWindow()
    } catch (error) {
      void dialog.showErrorBox(APP_NAME, error instanceof Error ? error.message : String(error))
      app.quit()
    }
  })

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      void createWindow()
    }
  })
}

declare global {
  namespace Electron {
    interface App {
      isQuitting?: boolean
    }
  }
}
