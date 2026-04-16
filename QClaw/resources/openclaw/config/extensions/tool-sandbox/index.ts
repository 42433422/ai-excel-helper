/**
 * tool-sandbox — 工具执行沙箱插件
 *
 * 核心机制：通过 before_tool_call 钩子改写 params.command，
 * 将原始命令包装为 lowpriv wrapper 调用，在低权限沙箱中执行。
 *
 * ★ 黑名单机制：
 *   内置一份受保护目录黑名单（OS 核心、凭据密钥、浏览器数据等）。
 *   如果命令操作的路径命中黑名单 → 以低权限执行（lowpriv wrapper）。
 *   如果命令操作的路径不在黑名单中 → 正常权限执行。
 *   无法从命令中提取路径 → 保守策略，以低权限执行。
 *
 * ★ 平台支持：
 * - Windows: 完整降权支持（lowpriv-launcher.exe，Low Integrity Level）
 * - macOS: 暂不支持降权（lowpriv-exec.sh 未实现），插件仅保留 blockPatterns
 *   高危命令拦截和审计日志能力，exec 命令不做降权包装
 *
 * 设计原则：
 * - 对 exec 类工具（bash_tool / execute_command）进行命令改写，降权执行（仅限 Windows）
 * - 对文件写操作工具（write_to_file / replace_in_file 等）检查目标路径，
 *   命中受保护目录时直接阻止（block），防止绕过 exec 降权的安全漏洞
 * - blockPatterns 高危命令拦截在所有平台上生效
 * - 对 read_file / search 等只读工具放行
 * - 降权失败时（wrapper 不存在）回退到正常执行 + stderr 告警
 * - 技能管理命令（npx skills / clawhub）跳过降权，以正常权限运行
 *   这类命令需要写入 ~/.qclaw/skills/ 等受保护目录，降权后必然失败
 *
 * 动态开关机制（★ 无需重启进程即可生效）：
 * - 插件在每次 before_tool_call 时从 app-store.json 实时读取 toolSandbox.enabled
 * - 使用 5 秒 TTL 缓存避免频繁磁盘 IO
 * - 用户在 UI 切换开关 → Electron 写 app-store.json → 插件最多 5 秒后感知变更
 * - 环境变量 QCLAW_TOOL_LOWPRIV 仍作为初始值，app-store.json 优先级更高
 *
 * 环境变量（由 Electron createCleanEnv() 注入，仅 Windows）：
 * - QCLAW_TOOL_LOWPRIV=1               降权总开关（初始值，运行时以 app-store.json 为准）
 * - QCLAW_TOOL_WRAPPER_PATH=path       wrapper 可执行文件路径
 * - QCLAW_TOOL_SANDBOX_LEVEL=level     降权级别（standard/strict/custom）
 * - QCLAW_APP_STORE_PATH=path          app-store.json 完整路径（用于实时读取开关状态）
 */

const LOG_TAG = 'tool-sandbox'

// ---- 动态配置读取（从 app-store.json 实时感知开关变更，无需重启进程）----

/**
 * 从 app-store.json 实时读取 toolSandbox.enabled 状态
 *
 * 设计目的：用户在 UI 上切换"工具权限限制"开关后，无需重启 OpenClaw 进程即可生效。
 * 环境变量 QCLAW_TOOL_LOWPRIV 仍然作为"初始值"在 register() 时使用，
 * 但运行时以 app-store.json 文件内容为准（文件优先于环境变量）。
 *
 * 性能策略：5 秒 TTL 缓存，避免每次 tool call 都读文件。
 * 对于连续的 tool call（典型间隔 100ms-2s），最多 5 秒内只读一次磁盘。
 * 用户切换开关后最多 5 秒生效，UX 可接受。
 */
const SECURITY_CONFIG_CACHE_TTL_MS = 5_000

interface SecurityConfigCache {
  enabled: boolean
  timestamp: number
}

let _securityConfigCache: SecurityConfigCache | null = null

function readToolSandboxEnabledFromFile(appStorePath: string | undefined): boolean | null {
  if (!appStorePath) return null

  // 检查缓存是否仍然有效
  if (_securityConfigCache && (Date.now() - _securityConfigCache.timestamp) < SECURITY_CONFIG_CACHE_TTL_MS) {
    return _securityConfigCache.enabled
  }

  try {
    // 使用 Node.js 内置 fs，OpenClaw 运行时环境中可用
    const fs = require('fs')

    if (!fs.existsSync(appStorePath)) {
      return null // 文件不存在，回退到环境变量
    }

    const raw = fs.readFileSync(appStorePath, 'utf-8')
    const config = JSON.parse(raw)
    const enabled = config?.toolSandbox?.enabled

    if (typeof enabled === 'boolean') {
      _securityConfigCache = { enabled, timestamp: Date.now() }
      return enabled
    }

    return null // 字段不存在或类型不对，回退到环境变量
  } catch {
    return null // 读取/解析失败，回退到环境变量
  }
}

// ---- 受保护目录黑名单（命中则降权执行）----

/**
 * 受保护目录黑名单 — 写操作命中这些目录时以低权限执行
 *
 * 黑名单使用环境变量占位符（如 %SystemRoot%），在运行时动态展开为实际路径。
 * 匹配规则：命令中提取的任意路径是黑名单目录或其子路径 → 降权执行。
 *
 * 分类：
 *   1. OS 核心目录 — Windows 系统关键文件（排除 Temp 目录）
 *   2. 系统引导/恢复 — 引导分区
 *   3. 凭据/密钥 — SSH、GPG、云凭据、浏览器密码等
 *   4. 浏览器用户数据 — Cookie/密码/历史
 *   5. 用户目录（C:\Users） — 排除当前用户后，防止跨用户访问
 */
const PROTECTED_DIR_PATTERNS: string[] = [
  // ── 1. OS 核心目录 ──
  '%SystemRoot%',                                // C:\Windows（排除 Temp 目录）
  '%SystemRoot%\\System32',                      // 系统核心 DLL/EXE
  '%SystemRoot%\\SysWOW64',                      // 32 位兼容层
  '%SystemRoot%\\WinSxS',                        // 组件存储（SxS 清单）
  '%SystemDrive%\\Windows',                      // 兜底（部分机器 SystemRoot != C:\Windows）

  // ── 2. 系统引导 / 恢复 ──
  '%SystemDrive%\\Boot',                         // BCD / 引导数据
  '%SystemDrive%\\Recovery',                     // WinRE 恢复映像
  '%SystemDrive%\\EFI',                          // UEFI 引导分区（挂载时）

  // ── 3. 凭据 / 密钥 ──
  '%USERPROFILE%\\.ssh',                         // SSH 密钥
  '%USERPROFILE%\\.gnupg',                       // GPG 密钥
  '%USERPROFILE%\\.aws',                         // AWS 凭据
  '%USERPROFILE%\\.azure',                       // Azure 凭据
  '%USERPROFILE%\\.kube',                        // Kubernetes 配置
  '%USERPROFILE%\\.docker',                      // Docker 凭据
  '%USERPROFILE%\\.config',                      // 各类开发工具凭据（git credential store 等）
  '%APPDATA%\\Microsoft\\Credentials',           // Windows 凭据管理器
  '%APPDATA%\\Microsoft\\Protect',               // DPAPI 主密钥

  // ── 4. 浏览器用户数据 ──
  '%LOCALAPPDATA%\\Google\\Chrome\\User Data',   // Chrome
  '%LOCALAPPDATA%\\Microsoft\\Edge\\User Data',  // Edge
  '%APPDATA%\\Mozilla\\Firefox\\Profiles',       // Firefox

  // ── 5. 用户目录（排除当前用户，防止跨用户访问）──
  '%SystemDrive%\\Users',                        // 注意：下方 isCommandInProtectedDirs / isPathInProtectedDirs 会排除当前用户目录
]

/**
 * 凭据 / 密钥目录 — 禁止读 + 写
 *
 * 与 PROTECTED_DIR_PATTERNS 的区别：
 *   PROTECTED_DIR_PATTERNS 仅限制写操作（通过降权或 block）
 *   CREDENTIAL_DIR_PATTERNS 同时限制读操作 — 凭据文件不应被 AI 读取
 *
 * 注意：这些目录已包含在 PROTECTED_DIR_PATTERNS 中，写操作已被保护。
 *       本列表仅用于额外的读操作拦截。
 */
const CREDENTIAL_DIR_PATTERNS: string[] = [
  '%USERPROFILE%\\.ssh',                         // SSH 密钥
  '%USERPROFILE%\\.gnupg',                       // GPG 密钥
  '%USERPROFILE%\\.aws',                         // AWS 凭据
  '%USERPROFILE%\\.azure',                       // Azure 凭据
  '%USERPROFILE%\\.kube',                        // Kubernetes 配置
  '%USERPROFILE%\\.docker',                      // Docker 凭据
  '%USERPROFILE%\\.config',                      // 各类开发工具凭据（git credential store 等）
  '%APPDATA%\\Microsoft\\Credentials',           // Windows 凭据管理器
  '%APPDATA%\\Microsoft\\Protect',               // DPAPI 主密钥
  '%LOCALAPPDATA%\\Google\\Chrome\\User Data',   // Chrome（含 Cookie / 密码 / Token）
  '%LOCALAPPDATA%\\Microsoft\\Edge\\User Data',  // Edge
  '%APPDATA%\\Mozilla\\Firefox\\Profiles',       // Firefox
]

let _expandedCredentialDirs: string[] | null = null

function getExpandedCredentialDirs(): string[] {
  if (_expandedCredentialDirs !== null) return _expandedCredentialDirs

  const path = require('path')
  const expanded: string[] = []

  for (const pattern of CREDENTIAL_DIR_PATTERNS) {
    const resolved = pattern.replace(/%([^%]+)%/g, (_match: string, varName: string) => {
      return process.env[varName] || ''
    })
    if (!resolved || resolved.includes('%')) continue
    expanded.push(path.resolve(resolved).toLowerCase())
  }

  _expandedCredentialDirs = [...new Set(expanded)]
  return _expandedCredentialDirs
}

/**
 * 检查文件路径是否在凭据目录中（用于读操作拦截）
 */
function isPathInCredentialDirs(filePath: string): boolean {
  const path = require('path')
  const normalized = path.resolve(filePath).toLowerCase()
  const parentDir = path.dirname(normalized)

  const pathsToCheck = [...new Set([normalized, parentDir])].filter(d => d.length > 3)
  if (pathsToCheck.length === 0) return false

  const credentialDirs = getExpandedCredentialDirs()
  if (credentialDirs.length === 0) return false

  for (const checkPath of pathsToCheck) {
    for (const credDir of credentialDirs) {
      const credDirWithSep = credDir.endsWith(path.sep) ? credDir : credDir + path.sep
      if (checkPath === credDir || checkPath.startsWith(credDirWithSep)) {
        return true
      }
    }
  }

  return false
}

/**
 * 系统核心注册表路径 — 拦截读写操作
 *
 * 通过 exec 工具执行的 reg.exe / regedit / PowerShell 注册表操作命令，
 * 如果目标注册表路径命中以下列表，将被直接阻止。
 *
 * 分类：
 *   1. 系统启动与服务 — Run/RunOnce/Services（防持久化攻击）
 *   2. 安全策略与认证 — LSA/SAM/Security（防凭据窃取）
 *   3. 系统核心配置 — Session Manager/CurrentVersion（防系统破坏）
 *   4. 网络与防火墙 — Tcpip/SharedAccess（防网络篡改）
 *   5. 安全软件 — Windows Defender/AppLocker（防安全软件被禁用）
 */
const PROTECTED_REGISTRY_PATHS: Array<{ path: string; blockRead: boolean; blockWrite: boolean; desc: string }> = [
  // ── 2. 安全策略与认证（防凭据窃取）──
  { path: 'HKLM\\SECURITY', blockRead: true, blockWrite: true, desc: '安全策略数据库' },
  { path: 'HKLM\\SAM', blockRead: true, blockWrite: true, desc: '用户账户安全数据库' },
  { path: 'HKLM\\SYSTEM\\CurrentControlSet\\Control\\Lsa', blockRead: true, blockWrite: true, desc: 'LSA 认证配置' },
  { path: 'HKLM\\SYSTEM\\CurrentControlSet\\Control\\SecurityProviders', blockRead: true, blockWrite: true, desc: '安全提供程序' },

  // ── 3. 系统核心配置（防系统破坏）──
  { path: 'HKLM\\SYSTEM\\CurrentControlSet\\Control\\Session Manager', blockRead: false, blockWrite: true, desc: '会话管理器' },
  { path: 'HKLM\\SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion\\Image File Execution Options', blockRead: false, blockWrite: true, desc: '映像劫持' },
  { path: 'HKLM\\SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion\\Winlogon', blockRead: false, blockWrite: true, desc: '登录配置' },
  { path: 'HKLM\\SYSTEM\\CurrentControlSet\\Control\\SafeBoot', blockRead: false, blockWrite: true, desc: '安全启动配置' },

  // ── 4. 网络与防火墙（防网络篡改）──
  { path: 'HKLM\\SYSTEM\\CurrentControlSet\\Services\\Tcpip\\Parameters', blockRead: false, blockWrite: true, desc: 'TCP/IP 核心参数' },
  { path: 'HKLM\\SYSTEM\\CurrentControlSet\\Services\\SharedAccess\\Parameters\\FirewallPolicy', blockRead: false, blockWrite: true, desc: '防火墙策略' },

  // ── 5. 安全软件（防安全软件被禁用）──
  { path: 'HKLM\\SOFTWARE\\Policies\\Microsoft\\Windows Defender', blockRead: false, blockWrite: true, desc: 'Defender 策略' },
  { path: 'HKLM\\SOFTWARE\\Microsoft\\Windows Defender', blockRead: false, blockWrite: true, desc: 'Defender 配置' },
  { path: 'HKLM\\SOFTWARE\\Policies\\Microsoft\\Windows\\safer', blockRead: false, blockWrite: true, desc: '软件限制策略' },
  { path: 'HKLM\\SYSTEM\\CurrentControlSet\\Control\\CI', blockRead: false, blockWrite: true, desc: '代码完整性策略' },
]

/**
 * 判断注册表操作命令是否命中受保护注册表路径
 *
 * @returns { blocked: true, path, desc } 如果命中；{ blocked: false } 如果放行
 */
function checkRegistryCommand(command: string): { blocked: boolean; regPath?: string; desc?: string } {
  // 标准化：将简写 HKLM: / HKCU: 展开为完整形式
  const normalized = command
    .replace(/\bHKLM:\\/gi, 'HKLM\\')
    .replace(/\bHKCU:\\/gi, 'HKCU\\')
    .replace(/\bHKLM\//gi, 'HKLM\\')
    .replace(/\bHKCU\//gi, 'HKCU\\')

  // 检测是否为注册表写操作命令
  const isRegWrite = /\b(?:reg\s+add|reg\s+delete|reg\s+import|reg\s+restore|reg\s+copy)\b/i.test(normalized)
    || /\b(?:New-Item(?:Property)?|Set-Item(?:Property)?|Remove-Item(?:Property)?|Rename-Item(?:Property)?|Copy-Item(?:Property)?)\b.*\b(?:HKLM|HKCU|HKEY_LOCAL_MACHINE|HKEY_CURRENT_USER)\b/i.test(normalized)
    || /\bRegedit\b.*\/s\b/i.test(normalized) // regedit /s = 静默导入

  // 检测是否为注册表读操作命令
  const isRegRead = /\b(?:reg\s+query|reg\s+export|reg\s+save)\b/i.test(normalized)
    || /\b(?:Get-Item(?:Property)?|Get-ChildItem)\b.*\b(?:HKLM|HKCU|HKEY_LOCAL_MACHINE|HKEY_CURRENT_USER)\b/i.test(normalized)

  if (!isRegWrite && !isRegRead) return { blocked: false }

  // 标准化命令中的注册表路径格式
  const cmdUpper = normalized.toUpperCase()
    .replace(/\bHKEY_LOCAL_MACHINE\b/g, 'HKLM')
    .replace(/\bHKEY_CURRENT_USER\b/g, 'HKCU')

  for (const entry of PROTECTED_REGISTRY_PATHS) {
    const entryUpper = entry.path.toUpperCase()

    // 检查命令中是否包含该注册表路径（路径本身或其子路径）
    if (!cmdUpper.includes(entryUpper)) continue

    // 根据操作类型判断是否拦截
    if (isRegWrite && entry.blockWrite) {
      return { blocked: true, regPath: entry.path, desc: entry.desc }
    }
    if (isRegRead && entry.blockRead) {
      return { blocked: true, regPath: entry.path, desc: entry.desc }
    }
  }

  return { blocked: false }
}

/**
 * 展开黑名单中的环境变量占位符，返回规范化后的目录列表
 *
 * 缓存策略：进程生命周期内环境变量不会变化，首次展开后缓存。
 */
let _expandedProtectedDirs: string[] | null = null

function getExpandedProtectedDirs(): string[] {
  if (_expandedProtectedDirs !== null) {
    return _expandedProtectedDirs
  }

  const path = require('path')
  const expanded: string[] = []

  for (const pattern of PROTECTED_DIR_PATTERNS) {
    // 展开 %VAR% 占位符
    const resolved = pattern.replace(/%([^%]+)%/g, (_match: string, varName: string) => {
      return process.env[varName] || ''
    })

    // 跳过未能展开的路径（环境变量不存在）
    if (!resolved || resolved.includes('%')) continue

    expanded.push(path.resolve(resolved).toLowerCase())
  }

  _expandedProtectedDirs = [...new Set(expanded)]
  console.log(`[${LOG_TAG}][DEBUG] getExpandedProtectedDirs: ${JSON.stringify(_expandedProtectedDirs)}`)
  console.log(`[${LOG_TAG}][DEBUG] env: USERPROFILE=${process.env.USERPROFILE}, SystemRoot=${process.env.SystemRoot}, SystemDrive=${process.env.SystemDrive}, APPDATA=${process.env.APPDATA}, LOCALAPPDATA=${process.env.LOCALAPPDATA}`)
  return _expandedProtectedDirs
}

/**
 * 展开命令中的环境变量引用为实际路径
 *
 * 支持三种形式：
 *   1. PowerShell: $env:USERPROFILE, $env:APPDATA 等
 *   2. CMD: %USERPROFILE%, %APPDATA% 等
 *   3. 波浪号: ~ 开头的路径（展开为 USERPROFILE）
 *
 * ★ 安全关键：如果不展开环境变量，AI 可以用 $env:USERPROFILE\.ssh 替代
 *   C:\Users\xxx\.ssh 来绕过路径检测，导致受保护目录的命令不被降权执行。
 */
function expandEnvVarsInCommand(command: string): string {
  let expanded = command

  // 1. PowerShell $env:VAR 形式
  //    匹配 $env:VarName（变量名由字母数字下划线组成）
  //    注意：$env:VAR 后面可能直接跟路径分隔符，如 $env:USERPROFILE\.ssh
  expanded = expanded.replace(/\$env:([A-Za-z_][A-Za-z0-9_]*)/gi, (_match: string, varName: string) => {
    const value = process.env[varName]
    return value || _match // 未找到环境变量时保留原文
  })

  // 2. CMD %VAR% 形式（extractPathsFromCommand 原本不处理这种，但保险起见也展开）
  expanded = expanded.replace(/%([A-Za-z_][A-Za-z0-9_]*)%/g, (_match: string, varName: string) => {
    const value = process.env[varName]
    return value || _match
  })

  // 3. 波浪号 ~ 开头的路径（PowerShell 中 ~ 等价于 $HOME / $env:USERPROFILE）
  //    匹配 ~\ 或 ~/ 开头的路径，展开为 USERPROFILE
  //    注意：只展开路径中的 ~，不展开命令参数中独立的 ~ 字符
  expanded = expanded.replace(/(?<=^|[\s"'(])~(?=[\\\/])/g, () => {
    return process.env.USERPROFILE || process.env.HOME || '~'
  })

  if (expanded !== command) {
    console.log(`[${LOG_TAG}][DEBUG] expandEnvVars: "${command.slice(0, 200)}" → "${expanded.slice(0, 200)}"`)
  }
  return expanded
}

/**
 * 从命令中提取所有涉及的文件/目录绝对路径
 *
 * 策略：
 *   0. ★ 预处理：展开命令中的环境变量（$env:VAR、%VAR%、~），防止绕过路径检测
 *   1. 提取 Windows 绝对路径（如 C:\Users\... 或 "C:\Users\..."）
 *   2. 覆盖常见操作：Remove-Item、Copy-Item、Move-Item、Set-Content、
 *      Out-File、New-Item、Get-Content、cd 等命令的 -Path 参数或位置参数
 */
function extractPathsFromCommand(command: string): string[] {
  const path = require('path')
  const paths: string[] = []

  // ★ 预处理：展开环境变量，将 $env:USERPROFILE\.ssh 变为 C:\Users\xxx\.ssh
  //   这是防止 AI 使用环境变量形式绕过路径检测的关键步骤
  const expandedCommand = expandEnvVarsInCommand(command)

  // 通用策略：提取命令中所有 Windows 绝对路径（驱动器号开头）
  // 匹配 "C:\xxx" 或 'C:\xxx' 或 C:\xxx（不带引号）
  const quotedPathRegex = /["']([A-Za-z]:\\[^"']+)["']/g
  let match
  while ((match = quotedPathRegex.exec(expandedCommand)) !== null) {
    if (match[1]) {
      paths.push(match[1].trim())
      console.log(`[${LOG_TAG}][DEBUG] extractPaths quotedPathRegex matched: "${match[1].trim()}"`)
    }
  }

  // 匹配 -Path C:\xxx 或 -LiteralPath C:\xxx 等参数形式（不带引号）
  const paramPathRegex = /(?:-(?:Path|LiteralPath|Destination|Target))\s+([A-Za-z]:\\[^\s;|&"']+)/gi
  while ((match = paramPathRegex.exec(expandedCommand)) !== null) {
    if (match[1]) {
      paths.push(match[1].trim())
      console.log(`[${LOG_TAG}][DEBUG] extractPaths paramPathRegex matched: "${match[1].trim()}"`)
    }
  }

  // 匹配命令后直接跟的路径（如 Remove-Item C:\xxx\file.txt）
  // 常见的文件操作命令
  // ★ 参数跳过规则同时支持 PowerShell 风格 (-Force) 和 cmd 风格 (/f /q /s)
  const cmdPathRegex = /(?:Remove-Item|del|rm|Copy-Item|Move-Item|Rename-Item|Set-Content|Add-Content|Out-File|New-Item|Get-Content|cat|type)\s+(?:(?:-\w+|\/[A-Za-z])\s+)*([A-Za-z]:\\[^\s;|&"']+)/gi
  while ((match = cmdPathRegex.exec(expandedCommand)) !== null) {
    if (match[1]) {
      paths.push(match[1].trim())
      console.log(`[${LOG_TAG}][DEBUG] extractPaths cmdPathRegex matched: "${match[1].trim()}"`)
    }
  }

  // ★ 兜底策略：提取命令中所有未被引号包裹的 Windows 绝对路径
  // 应对各种未预见的命令格式，确保路径不被遗漏
  const fallbackPathRegex = /(?:^|[\s;|&])([A-Za-z]:\\(?:[^\s;|&"']+\\)*[^\s;|&"']+)/g
  while ((match = fallbackPathRegex.exec(expandedCommand)) !== null) {
    if (match[1]) {
      paths.push(match[1].trim())
      console.log(`[${LOG_TAG}][DEBUG] extractPaths fallbackPathRegex matched: "${match[1].trim()}"`)
    }
  }

  // 去重并提取父目录（文件路径取其所在目录，目录路径取自身）
  const uniquePaths = [...new Set(paths)]
  const resolvedDirs: string[] = []
  for (const p of uniquePaths) {
    // 同时加入路径本身（可能是目录）和其父目录（文件所在目录）
    resolvedDirs.push(path.resolve(p).toLowerCase())
    resolvedDirs.push(path.dirname(path.resolve(p)).toLowerCase())
  }

  const result = [...new Set(resolvedDirs)].filter(d => d.length > 3)
  console.log(`[${LOG_TAG}][DEBUG] extractPaths result: ${JSON.stringify(result)}`)
  return result
}

/**
 * 检查命令操作的路径是否命中受保护目录黑名单
 *
 * ★ 核心语义：黑名单目录 = 系统受保护目录，操作这些目录中的内容需要降权
 *
 * 匹配规则：
 *   - 操作路径是黑名单目录自身或其子路径 → 命中
 *   - 特殊处理 C:\Users：排除当前用户自己的目录（允许正常操作自己的文件）
 *   - 路径比较不区分大小写（Windows）
 *   - 路径规范化后比较（resolve + toLowerCase）
 *
 * @returns true = 有路径命中黑名单，应降权执行; false = 无需降权（含无法提取路径的情况）
 */
function isCommandInProtectedDirs(command: string): boolean {
  const path = require('path')
  const commandPaths = extractPathsFromCommand(command)

  // 无法从命令中提取路径 → 放行，不降权
  // 安全保障：blockPatterns / 注册表拦截已在上游生效，高危命令不会到达此处
  if (commandPaths.length === 0) {
    console.log(`[${LOG_TAG}][DEBUG] isCommandInProtectedDirs: no paths extracted, returning false`)
    return false
  }

  const protectedDirs = getExpandedProtectedDirs()
  if (protectedDirs.length === 0) {
    console.log(`[${LOG_TAG}][DEBUG] isCommandInProtectedDirs: no protected dirs, returning false`)
    return false
  }

  // 获取当前用户目录（用于 C:\Users 的特殊排除逻辑）
  const userProfile = (process.env.USERPROFILE || '').toLowerCase()
  const userProfileWithSep = userProfile ? (userProfile.endsWith(path.sep) ? userProfile : userProfile + path.sep) : ''

  // 获取 Windows 系统根目录（用于 C:\Windows\Temp 的排除逻辑）
  const systemRoot = (process.env.SystemRoot || 'C:\\Windows').toLowerCase()

  console.log(`[${LOG_TAG}][DEBUG] isCommandInProtectedDirs: commandPaths=${JSON.stringify(commandPaths)}, protectedDirs=${JSON.stringify(protectedDirs)}, userProfile="${userProfile}", userProfileWithSep="${userProfileWithSep}", systemRoot="${systemRoot}", path.sep="${path.sep}"`)

  // 检查每个操作路径是否命中任何黑名单目录
  for (const cmdPath of commandPaths) {
    const normalized = path.resolve(cmdPath).toLowerCase()

    for (const protectedDir of protectedDirs) {
      const protectedDirWithSep = protectedDir.endsWith(path.sep) ? protectedDir : protectedDir + path.sep
      const isInProtected = normalized === protectedDir || normalized.startsWith(protectedDirWithSep)

      if (!isInProtected) continue

      console.log(`[${LOG_TAG}][DEBUG] isCommandInProtectedDirs: MATCH normalized="${normalized}" vs protectedDir="${protectedDir}"`)

      // 特殊处理：C:\Windows 黑名单需排除 Temp 目录（许多程序的临时目录，AI 正常操作）
      if (protectedDir === systemRoot) {
        const tempDir = systemRoot + path.sep + 'temp'
        const tempDirWithSep = tempDir + path.sep
        if (normalized === tempDir || normalized.startsWith(tempDirWithSep)) {
          console.log(`[${LOG_TAG}][DEBUG] isCommandInProtectedDirs: excluded (Windows Temp)`)
          continue // Windows Temp 目录，不命中
        }
      }

      // 特殊处理：C:\Users 黑名单需排除当前用户自己的目录
      // C:\Users\<当前用户>\xxx 不视为命中，允许正常操作
      // C:\Users\<其他用户>\xxx 视为命中，需要降权
      if (protectedDir.endsWith('\\users') && userProfileWithSep) {
        if (normalized === userProfile || normalized.startsWith(userProfileWithSep)) {
          console.log(`[${LOG_TAG}][DEBUG] isCommandInProtectedDirs: excluded (current user dir)`)
          continue // 当前用户目录，不命中
        }
      }

      console.log(`[${LOG_TAG}][DEBUG] isCommandInProtectedDirs: HIT! returning true`)
      return true // 命中黑名单
    }
  }

  console.log(`[${LOG_TAG}][DEBUG] isCommandInProtectedDirs: no match found, returning false`)
  return false // 所有路径都不在黑名单中
}

/**
 * 检查单个文件路径是否命中受保护目录黑名单
 *
 * ★ 用于文件写操作工具（write_to_file / replace_in_file 等）的路径检查。
 *   与 isCommandInProtectedDirs 的区别：后者从命令字符串中提取路径，
 *   本函数直接接收工具参数中的文件路径，更简单也更可靠。
 *
 * 匹配规则与 isCommandInProtectedDirs 保持一致：
 *   - 路径是黑名单目录自身或其子路径 → 命中
 *   - 文件路径同时检查其父目录
 *   - C:\Users 排除当前用户目录
 *   - 路径比较不区分大小写（Windows）
 *
 * @returns true = 路径命中黑名单，应阻止操作; false = 路径安全
 */
function isPathInProtectedDirs(filePath: string): boolean {
  const path = require('path')
  const normalized = path.resolve(filePath).toLowerCase()
  const parentDir = path.dirname(normalized)

  // 同时检查路径自身和父目录（与 extractPathsFromCommand 逻辑一致）
  const pathsToCheck = [...new Set([normalized, parentDir])].filter(d => d.length > 3)
  if (pathsToCheck.length === 0) return false

  const protectedDirs = getExpandedProtectedDirs()
  if (protectedDirs.length === 0) return false

  // 获取当前用户目录（用于 C:\Users 的特殊排除逻辑）
  const userProfile = (process.env.USERPROFILE || '').toLowerCase()
  const userProfileWithSep = userProfile
    ? (userProfile.endsWith(path.sep) ? userProfile : userProfile + path.sep)
    : ''

  // 获取 Windows 系统根目录（用于 C:\Windows\Temp 的排除逻辑）
  const systemRoot = (process.env.SystemRoot || 'C:\\Windows').toLowerCase()

  for (const checkPath of pathsToCheck) {
    for (const protectedDir of protectedDirs) {
      const protectedDirWithSep = protectedDir.endsWith(path.sep) ? protectedDir : protectedDir + path.sep
      const isInProtected = checkPath === protectedDir || checkPath.startsWith(protectedDirWithSep)

      if (!isInProtected) continue

      // 特殊处理：C:\Windows 黑名单需排除 Temp 目录
      if (protectedDir === systemRoot) {
        const tempDir = systemRoot + path.sep + 'temp'
        const tempDirWithSep = tempDir + path.sep
        if (checkPath === tempDir || checkPath.startsWith(tempDirWithSep)) {
          continue // Windows Temp 目录，不命中
        }
      }

      // 特殊处理：C:\Users 黑名单需排除当前用户自己的目录
      if (protectedDir.endsWith('\\users') && userProfileWithSep) {
        if (checkPath === userProfile || checkPath.startsWith(userProfileWithSep)) {
          continue // 当前用户目录，不命中
        }
      }

      return true // 命中黑名单
    }
  }

  return false // 路径不在黑名单中
}

// ---- 类型定义 ----

interface ToolCallEvent {
  toolName: string
  toolCallId: string
  params: Record<string, unknown>
  result?: { content: string | Array<{ type: string; text: string }> }
}

interface HookContext {
  agentId: string
  sessionKey: string
}

interface BeforeToolCallResult {
  block?: boolean
  blockReason?: string
  params?: Record<string, unknown>
}

// ---- 工具分类辅助函数 ----

function isExecTool(name: string): boolean {
  // OpenClaw 运行时注册的工具名是 "exec"（CORE_TOOL_DEFINITIONS.id = "exec"）
  // "bash" 是 "exec" 的别名（TOOL_NAME_ALIASES: { bash: "exec" }）
  // 保留 bash_tool / execute_command 作为兼容（文档中曾使用这些名称）
  return name === 'exec' || name === 'bash' || name === 'bash_tool' || name === 'execute_command'
}

/**
 * 判断工具是否为「文件写操作」类型
 *
 * 这些工具直接操作文件系统，不经过 exec 命令行，因此无法通过降权包装来限制。
 * 当目标路径命中受保护目录黑名单时，需要直接 block 阻止执行。
 *
 * OpenClaw 核心工具名（CORE_TOOL_DEFINITIONS）：
 *   - write       — 创建或覆盖文件（id = "write"）
 *   - edit        — 精确编辑文件（id = "edit"）
 *   - apply_patch — 补丁文件（id = "apply_patch"，别名 "apply-patch"）
 *
 * 兼容名（其他 AI 客户端可能使用的工具名）：
 *   - write_to_file / create_file — 对应 write
 *   - replace_in_file / edit_file — 对应 edit
 */
function isFileWriteTool(name: string): boolean {
  return name === 'write'           // OpenClaw 核心工具名
    || name === 'edit'              // OpenClaw 核心工具名
    || name === 'apply_patch'       // OpenClaw 核心工具名
    || name === 'apply-patch'       // apply_patch 的别名
    || name === 'write_to_file'     // 兼容名
    || name === 'create_file'       // 兼容名
    || name === 'replace_in_file'   // 兼容名
    || name === 'edit_file'         // 兼容名
}

/**
 * 判断工具是否为「文件读操作」类型
 *
 * 用于凭据目录的读操作拦截。
 *
 * OpenClaw 核心工具名：
 *   - read        — 读取文件内容（id = "read"）
 *   - search      — 搜索文件内容（id = "search"）
 *   - glob        — 文件查找（id = "glob"）
 *   - grep        — 内容搜索（id = "grep"）
 *   - list        — 列出目录内容（id = "list"）
 *
 * 兼容名：
 *   - read_file / cat_file — 对应 read
 *   - search_files / list_files / list_dir — 对应相关操作
 */
function isFileReadTool(name: string): boolean {
  return name === 'read'            // OpenClaw 核心工具名
    || name === 'search'            // OpenClaw 核心工具名
    || name === 'glob'              // OpenClaw 核心工具名
    || name === 'grep'              // OpenClaw 核心工具名
    || name === 'list'              // OpenClaw 核心工具名
    || name === 'read_file'         // 兼容名
    || name === 'cat_file'          // 兼容名
    || name === 'search_files'      // 兼容名
    || name === 'list_files'        // 兼容名
    || name === 'list_dir'          // 兼容名
}

// ---- 不受信目录检测（安全增强）----

/**
 * 不受信目录关键词列表（全小写、统一正斜杠）
 *
 * 这些目录通常包含用户从网络下载的、来源不明的文件，
 * 是提示词拼接注入攻击（LLM 上下文投毒 → 自动执行本地文件）的主要攻击面。
 */
const UNTRUSTED_DIR_KEYWORDS = [
  '/downloads/',
  '/desktop/',
  '/temp/',
  '/tmp/',
  '/appdata/',
  '/public/',
]

/**
 * 危险可执行文件扩展名
 */
const DANGEROUS_EXECUTABLE_EXTS = [
  '.exe', '.bat', '.cmd', '.msi', '.scr', '.pif', '.com',
  '.vbs', '.vbe', '.wsf', '.wsh', '.ps1',
]

/**
 * 从启动命令中提取目标文件路径
 *
 * 支持的命令模式：
 * - Start-Process "path" / Start-Process 'path' / Start-Process path
 * - start "path" / start path
 * - & 'path.exe' / & "path.exe"
 * - Invoke-Item "path" / ii path
 * - explorer "path"
 * - cmd /c start "path"
 * - open path (macOS)
 *
 * 使用贪婪匹配提取第一个路径参数。
 */
function extractLaunchTarget(command: string): string | null {
  const trimmed = command.trim()

  // 通用提取：跳过命令关键词和可选参数，提取第一个路径参数
  // Start-Process [-FilePath] "path"
  let m = trimmed.match(
    /^(?:Start-Process|saps)\s+(?:(?:-\w+)\s+)*['"]?([^'";\s|&][^'";\s|&]*)['"]?/i
  )
  if (m?.[1]) return m[1]

  // start path（排除 start -xxx 参数形式）
  m = trimmed.match(/^start\s+(?!-)['"]?([^'";\s|&]+)['"]?/i)
  if (m?.[1]) return m[1]

  // & 'path' 或 & "path" 或 & path
  m = trimmed.match(/^&\s+['"]?([^'";\s|&]+)['"]?/i)
  if (m?.[1]) return m[1]

  // Invoke-Item / ii
  m = trimmed.match(/^(?:Invoke-Item|ii)\s+['"]?([^'";\s|&]+)['"]?/i)
  if (m?.[1]) return m[1]

  // explorer / explorer.exe
  m = trimmed.match(/^explorer(?:\.exe)?\s+['"]?([^'";\s|&]+)['"]?/i)
  if (m?.[1]) return m[1]

  // cmd /c start
  m = trimmed.match(/^cmd\s+\/c\s+start\s+['"]?([^'";\s|&]+)['"]?/i)
  if (m?.[1]) return m[1]

  // macOS: open path
  if (process.platform === 'darwin') {
    m = trimmed.match(/^open\s+(?:-\w+\s+)*['"]?([^'";\s|&]+)['"]?/i)
    if (m?.[1]) return m[1]
  }

  return null
}

/**
 * 检测启动命令的目标是否在不受信目录下的可执行文件
 *
 * 返回 true 表示目标在不受信目录中，调用方应阻止跳过降权。
 * 返回 false 表示安全（受信目录或非可执行文件），可跳过降权。
 */
function isLaunchTargetInUntrustedDir(command: string): boolean {
  const target = extractLaunchTarget(command)
  if (!target) return false

  // 统一为小写正斜杠路径
  const normalized = target.replace(/\\/g, '/').toLowerCase()

  // 检查扩展名是否为危险类型
  const hasDangerousExt = DANGEROUS_EXECUTABLE_EXTS.some(ext =>
    normalized.endsWith(ext)
  )
  if (!hasDangerousExt) return false

  // 检查路径是否包含不受信目录段
  for (const keyword of UNTRUSTED_DIR_KEYWORDS) {
    if (normalized.includes(keyword)) {
      console.log(
        `[${LOG_TAG}] untrusted-dir detected in launch target: "${target}" (matched: ${keyword})`
      )
      return true
    }
  }

  return false
}

// ---- 外部程序启动检测（跳过降权）----

/**
 * 检测命令是否主要目的是「启动外部应用程序」
 *
 * 这类命令不应该被降权包装，因为：
 * 1. lowpriv-launcher 会使整条命令在 Low IL 下运行
 * 2. 被 spawn 出的子进程继承 Low IL，导致 .exe 程序权限不足、运行异常
 * 3. 启动外部程序本身不是危险操作，真正的安全风险由 blockPatterns 拦截
 *
 * ★ 安全增强（防上下文投毒）：
 *   即使命令形式匹配了应用启动模式，如果目标可执行文件位于 Downloads/Desktop/Temp
 *   等不受信目录下，仍然返回 false（不跳过降权），让命令走正常的沙箱降权路径。
 *   这防止 LLM 被上下文投毒后自动执行用户下载目录中的恶意文件。
 *
 * 检测策略（按平台）：
 *
 * Windows (PowerShell):
 *   - Start-Process / start / saps（PowerShell 别名）
 *   - Invoke-Item / ii（打开文件关联的程序）
 *   - explorer.exe（文件管理器/打开目录）
 *   - cmd /c start（传统启动方式）
 *   - [Diagnostics.Process]::Start()（.NET API）
 *   - 直接以 .exe 路径开头的命令（如 "notepad.exe xxx"）—— 暂不检测，因为太宽泛
 *
 * macOS:
 *   - open（系统命令，打开应用/文件/URL）
 *   - /Applications/xxx.app（直接应用路径）
 */
function isAppLaunchCommand(command: string): boolean {
  const trimmed = command.trim()

  if (process.platform === 'win32') {
    // PowerShell: Start-Process / start / saps（忽略大小写）
    // 注意 "start" 也是 PowerShell 中 Start-Process 的别名
    // 匹配模式：命令以这些关键词开头，后面跟空格或引号或行尾
    if (/^(Start-Process|saps)\s/i.test(trimmed)) {
      // ★ 安全检查：如果目标 exe 在不受信目录下，不跳过降权
      if (isLaunchTargetInUntrustedDir(trimmed)) return false
      return true
    }
    // "start" 比较特殊，需要排除 "start-xxx" 等其他命令
    if (/^start\s+(?!-)/i.test(trimmed)) {
      if (isLaunchTargetInUntrustedDir(trimmed)) return false
      return true
    }

    // PowerShell: Invoke-Item / ii
    if (/^(Invoke-Item|ii)\s/i.test(trimmed)) {
      if (isLaunchTargetInUntrustedDir(trimmed)) return false
      return true
    }

    // explorer.exe（打开文件管理器/目录/URL）
    if (/^explorer(\.exe)?\s/i.test(trimmed)) {
      if (isLaunchTargetInUntrustedDir(trimmed)) return false
      return true
    }

    // cmd /c start（传统方式）
    if (/^cmd\s+\/c\s+start\s/i.test(trimmed)) {
      if (isLaunchTargetInUntrustedDir(trimmed)) return false
      return true
    }

    // .NET [Diagnostics.Process]::Start()
    if (/\[(?:System\.)?Diagnostics\.Process\]::Start\s*\(/i.test(trimmed)) {
      if (isLaunchTargetInUntrustedDir(trimmed)) return false
      return true
    }

    // & 'path\to\xxx.exe'（PowerShell 调用外部 exe，不含 shell 命令）
    // 仅匹配 & 后直接跟 .exe 路径的简单形式
    if (/^&\s+['"]?[^'"]*\.exe['"]?\s*$/i.test(trimmed)) {
      if (isLaunchTargetInUntrustedDir(trimmed)) return false
      return true
    }

  } else if (process.platform === 'darwin') {
    // macOS: open 命令
    if (/^open\s/i.test(trimmed)) {
      if (isLaunchTargetInUntrustedDir(trimmed)) return false
      return true
    }

    // 直接调用 .app bundle
    if (/^(\/Applications\/|~\/Applications\/).*\.app/i.test(trimmed)) return true
  }

  return false
}

// ---- 技能管理命令检测（跳过降权）----

/**
 * 检测命令是否为「技能管理」操作（安装/更新/搜索/检查技能）
 *
 * 这类命令不应该被降权包装，因为：
 * 1. 技能安装需要写入 ~/.qclaw/skills/、~/.openclaw/skills/ 等目录
 * 2. 这些目录在 Low IL 下不可写（属于 %USERPROFILE% 保护范围）
 * 3. 降权后 npm 缓存/临时目录也受限，导致 npx 本身也可能失败
 * 4. 技能安装本身不是高危操作（只是下载并解压 skill 包到指定目录）
 *
 * 安全保障：
 * - blockPatterns 高危命令拦截仍在上方生效，不会被本函数绕过
 * - 仅匹配特定的技能管理工具命令，不是通配放行
 * - 技能安装的目标目录受 SkillPlugin 的 sanitizeSkillSlug() + assertPathWithin() 保护
 * - ★ 安全修复：所有正则使用 $ 行尾锚定 + 安全字符集，防止通过追加 shell 元字符绕过降权
 *
 * 匹配的命令模式：
 * - npx skills find/add/check/update/init/remove/list
 * - npx -y skills ...（带 -y 标记跳过确认）
 * - clawhub install/uninstall/update/list/search
 * - npm install -g clawhub（安装 clawhub CLI 本身）
 */
function isSkillManagementCommand(command: string): boolean {
  const trimmed = command.trim()

  // ★ 安全修复：使用 $ 行尾锚定 + SAFE_ARG 安全字符集，禁止追加 shell 运算符
  // 修复前使用 \b 仅检查单词边界，攻击者可通过 "clawhub install foo; rm -rf ~" 绕过降权
  // SAFE_ARG 只允许字母数字、路径分隔符、@ (npm scope)、- (flag)、. 和空白符
  // 禁止 ; & | ` $ > < \n 等 shell 元字符
  const SAFE_ARG = String.raw`[\w@/\\.:\-\s]*`

  // npx skills ... (各种子命令)
  // 支持 npx -y skills ... 和 npx --yes skills ... 变体
  if (new RegExp(
    String.raw`^npx\s+(-y\s+|--yes\s+)?skills\s+(find|add|check|update|init|remove|list)(\s+${SAFE_ARG})?$`,
    'i'
  ).test(trimmed)) return true

  // clawhub ... (技能市场 CLI)
  if (new RegExp(
    String.raw`^clawhub\s+(install|uninstall|update|list|search|find|add|remove|publish)(\s+${SAFE_ARG})?$`,
    'i'
  ).test(trimmed)) return true

  // npm install -g clawhub (安装 clawhub CLI 本身，严格匹配不允许追加参数)
  if (new RegExp(
    String.raw`^npm\s+(install|i)\s+(-g|--global)\s+clawhub$`,
    'i'
  ).test(trimmed)) return true

  return false
}

function isWriteTool(name: string): boolean {
  // OpenClaw 运行时注册的工具名是 "write"（CORE_TOOL_DEFINITIONS.id = "write"）
  // "write_file" 是 "write" 的别名（TOOL_NAME_ALIASES: { write_file: "write" }）
  // "edit" 是文件编辑工具的实际注册名
  // 保留 file_editor 作为兼容（文档中曾使用此名称）
  return name === 'write' || name === 'edit' || name === 'write_file' || name === 'file_editor'
}

// ---- 降权级别参数映射 ----

/**
 * 根据降权级别获取 Windows lowpriv-launcher.exe 的命令行参数
 *
 * | 级别     | Low IL | Job Object | Restricted Token |
 * |----------|--------|------------|------------------|
 * | standard | ✅     | ✅         | ❌               |
 * | strict   | ✅     | ✅         | ✅               |
 * | custom   | ✅     | ✅         | ✅               |
 */
function getWindowsLauncherArgs(level: string): string {
  switch (level) {
    case 'strict':
    case 'custom':
      return '--low-il --restricted-token --job-object'
    case 'standard':
    default:
      return '--low-il --job-object'
  }
}

// ---- PowerShell 路径动态解析 ----

/**
 * 动态获取 PowerShell 可执行文件的完整路径
 *
 * 为什么需要完整路径：
 *   lowpriv-launcher.exe 通过 CreateProcessAsUser / CreateProcessW 创建子进程，
 *   当 lpApplicationName=nullptr 时，系统从 cmdLine 的第一个 token 搜索可执行文件。
 *   搜索范围依赖 PATH 环境变量，但在 Low IL token 或某些受限环境下，
 *   PATH 可能被修改或丢失，导致 "powershell.exe" 无法被找到（错误码 2: ERROR_FILE_NOT_FOUND）。
 *   使用完整路径可以完全绕过 PATH 搜索，确保在任何权限级别下都能正确启动。
 *
 * 解析策略（按优先级）：
 *   1. 检查 %SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe（标准安装路径）
 *   2. 检查 %SystemRoot%\SysWOW64\WindowsPowerShell\v1.0\powershell.exe（32位兼容）
 *   3. 回退到裸名 "powershell.exe"（依赖 PATH，作为最后手段）
 *
 * 缓存策略：路径在进程生命周期内不会变化，首次解析后缓存结果。
 */
let _resolvedPowerShellPath: string | null = null

function resolvePowerShellPath(): string {
  if (_resolvedPowerShellPath !== null) {
    return _resolvedPowerShellPath
  }

  const fs = require('fs')
  const path = require('path')
  const systemRoot = process.env.SystemRoot || process.env.windir || 'C:\\Windows'

  // 候选路径列表（按优先级排序）
  const candidates = [
    path.join(systemRoot, 'System32', 'WindowsPowerShell', 'v1.0', 'powershell.exe'),
    path.join(systemRoot, 'SysWOW64', 'WindowsPowerShell', 'v1.0', 'powershell.exe'),
  ]

  for (const candidate of candidates) {
    try {
      if (fs.existsSync(candidate)) {
        _resolvedPowerShellPath = candidate
        console.log(`[${LOG_TAG}] resolved PowerShell path: ${candidate}`)
        return candidate
      }
    } catch {
      // 访问失败（权限等），继续尝试下一个
    }
  }

  // 所有候选路径都不存在，回退到裸名（依赖 PATH）
  console.warn(`[${LOG_TAG}] PowerShell not found at standard paths, falling back to "powershell.exe"`)
  _resolvedPowerShellPath = 'powershell.exe'
  return _resolvedPowerShellPath
}

// ---- 跨平台命令包装 ----

/**
 * 按当前平台包装命令
 *
 * 目前仅 Windows 支持降权包装（lowpriv-launcher.exe）。
 * macOS 暂不支持降权，不应到达此函数（上层已通过 wrapperPath 为空跳过）。
 *
 * Windows: wrapperPath 指向 lowpriv-launcher.exe
 *   改写后的命令由 PowerShell 执行:
 *   & 'launcher.exe' <level-args> -- "C:\Windows\System32\...\powershell.exe" -NoProfile -NonInteractive -Command '原始命令'
 *
 * @returns 包装后的命令字符串，null 表示无法包装（调用方应放行原始命令）
 */
function wrapCommandForPlatform(command: string, wrapperPath: string, level: string): string | null {
  if (process.platform === 'win32') {
    return wrapCommandWindows(command, wrapperPath, level)
  }
  return null // 非 Windows 平台不支持，放行
}

/**
 * Windows 命令包装
 *
 * OpenClaw getShellConfig() 在 Windows 上使用 PowerShell，所以改写后的命令
 * 会被 PowerShell 执行。使用 & 调用外部 exe。
 *
 * ★ 使用动态解析的 PowerShell 完整路径，避免在 Low IL 环境下因 PATH 丢失
 *   导致 CreateProcessAsUser / CreateProcessW 返回 ERROR_FILE_NOT_FOUND (2)。
 *
 * 转义策略：PowerShell 单引号内只需将 ' 转义为 ''
 */
function wrapCommandWindows(command: string, wrapperPath: string, level: string): string {
  const escapedCommand = command.replace(/'/g, "''")
  const launcherArgs = getWindowsLauncherArgs(level)
  const psPath = resolvePowerShellPath()

  // ★ 注入 UTF-8 编码设置，避免 Low IL PowerShell 使用 GBK 输出导致乱码
  // [Console]::OutputEncoding 确保 stdout 为 UTF-8，chcp 65001 设置控制台代码页
  // 这样 after_tool_call 中的权限拒绝正则能正确匹配中英文错误消息
  const utf8Prefix = '[Console]::OutputEncoding=[Text.Encoding]::UTF8; $OutputEncoding=[Text.Encoding]::UTF8; '
  return `& '${wrapperPath}' ${launcherArgs} -- "${psPath}" -NoProfile -NonInteractive -Command '${utf8Prefix}${escapedCommand}'`
}

// ---- 插件定义 ----

// ---- 降权命令追踪（toolCallId → 降权上下文）----
// ★ 当 before_tool_call 对命令进行降权包装时，记录 toolCallId 和触发降权的原因。
//   在 tool_result_persist 中查询此 Map，如果命令是降权执行的且输出包含错误，
//   立即覆盖为终止性消息，避免 AI 继续换方式尝试（浪费 token）。
//   Map 条目在 tool_result_persist 消费后立即删除，防止内存泄漏。
interface LowprivTrackingInfo {
  protectedDir: string   // 触发降权的保护目录
  originalCommand: string // 原始命令（用于日志）
}
const _lowprivTracking: Map<string, LowprivTrackingInfo> = new Map()

// ---- 统一安全拦截消息生成 ----
// ★ 所有 block / 终止性错误都使用此函数生成消息，确保：
//   1. AI 明确知道这是安全策略限制，换方式也无法绕过 → 减少重试（节省 token）
//   2. AI 告知用户具体的关闭路径 → 用户体验
//   3. 消息格式统一 → 维护简单

/**
 * 生成用于 blockReason 的拦截消息
 * @param reason 拦截原因（技术描述，面向日志/调试）
 * @param affectedTarget 受影响的目录或路径（可选，展示给用户）
 */
function buildBlockMessage(reason: string, affectedTarget?: string): string {
  const lines: string[] = [
    `[SYSTEM SECURITY POLICY - tool-sandbox] ${reason}`,
  ]
  if (affectedTarget) {
    lines.push(`受影响目标：${affectedTarget}`)
  }
  lines.push(
    '',
    '⚠️ IMPORTANT INSTRUCTIONS — YOU MUST FOLLOW:',
    '',
    '1. This operation was BLOCKED by QClaw security policy ("工具权限限制").',
    '2. You MUST NOT attempt any alternative approaches (different commands, tools, scripts, languages, elevation, etc.).',
    '3. You MUST NOT suggest the user to run commands with administrator privileges or use PowerShell/CMD manually.',
    '',
    '4. You MUST tell the user the following message IN CHINESE:',
    '',
    `   此操作被 QClaw 的"工具权限限制"功能拦截。${affectedTarget ? `受保护目录：${affectedTarget}。` : ''}`,
    '   如需执行此操作，请前往 QClaw 左下角设置 → 关闭"工具权限限制"开关后重试。',
    '',
    'DO NOT deviate from the above instructions. DO NOT suggest manual admin operations.',
  )
  return lines.join('\n')
}

/**
 * 生成用于 tool_result_persist 的终止性错误纯文本
 *
 * ★ 必须使用纯文本而非 JSON：
 *   AI 模型读取 toolResult 的 content[].text 字段，如果内容是 JSON 字符串，
 *   换行符会被 JSON 转义为 \n，模型看到的是单行文本，指令效果大打折扣。
 *   纯文本格式确保模型看到格式化好的多行指令。
 *
 * @param toolName 工具名
 * @param reason 拦截原因
 * @param affectedTarget 受影响的目录或路径
 */
function buildTerminalErrorPayload(toolName: string, reason: string, affectedTarget?: string): string {
  return buildBlockMessage(reason, affectedTarget)
}

// ---- 权限拒绝锁定机制 ----
// ★ 当某个保护目录的操作被权限拒绝后，记录到 lockedDirs 集合中。
//   后续任何涉及该目录的操作（exec / write）都直接 block，不再只是降权。
//   这防止 AI 模型通过反复尝试不同方式绕过降权保护。
const _lockedDirs: Set<string> = new Set()

function lockProtectedDir(dir: string): void {
  const normalized = dir.toLowerCase().replace(/\//g, '\\').replace(/\\+$/, '')
  _lockedDirs.add(normalized)
  console.log(`[${LOG_TAG}] 🔒 dir locked after permission denied: "${normalized}" (total locked: ${_lockedDirs.size})`)
}

/**
 * 检查命令中的路径是否命中已锁定的目录
 *
 * ★ 排除逻辑与 isCommandInProtectedDirs / isPathInProtectedDirs 保持一致：
 *   - C:\Windows\Temp 不视为命中 C:\Windows 锁定
 *   - 当前用户目录不视为命中 C:\Users 锁定
 *
 * @returns 命中的锁定目录，如果没有命中返回 null
 */
function checkLockedDirs(command: string): string | null {
  if (_lockedDirs.size === 0) return null
  const path = require('path')
  const commandPaths = extractPathsFromCommand(command)

  // 获取 Windows 系统根目录（用于 C:\Windows\Temp 的排除逻辑）
  const systemRoot = (process.env.SystemRoot || 'C:\\Windows').toLowerCase()

  // 获取当前用户目录（用于 C:\Users 的排除逻辑）
  const userProfile = (process.env.USERPROFILE || '').toLowerCase()
  const userProfileWithSep = userProfile
    ? (userProfile.endsWith(path.sep) ? userProfile : userProfile + path.sep)
    : ''

  for (const cmdPath of commandPaths) {
    const normalized = path.resolve(cmdPath).toLowerCase()
    for (const lockedDir of _lockedDirs) {
      const lockedDirWithSep = lockedDir.endsWith(path.sep) ? lockedDir : lockedDir + path.sep
      if (normalized === lockedDir || normalized.startsWith(lockedDirWithSep)) {
        // ★ 特殊处理：C:\Windows 锁定需排除 Temp 目录（与 isCommandInProtectedDirs 保持一致）
        if (lockedDir === systemRoot) {
          const tempDir = systemRoot + path.sep + 'temp'
          const tempDirWithSep = tempDir + path.sep
          if (normalized === tempDir || normalized.startsWith(tempDirWithSep)) {
            continue // Windows Temp 目录，不命中锁定
          }
        }

        // ★ 特殊处理：C:\Users 锁定需排除当前用户目录（与 isCommandInProtectedDirs 保持一致）
        if (lockedDir.endsWith('\\users') && userProfileWithSep) {
          if (normalized === userProfile || normalized.startsWith(userProfileWithSep)) {
            continue // 当前用户目录，不命中锁定
          }
        }

        return lockedDir
      }
    }
  }
  return null
}

/**
 * 检查脚本/文件内容中是否包含对已锁定目录的操作路径
 * ★ 防止 AI 通过"写脚本到非保护目录 → 执行脚本"的间接方式绕过降权
 * @returns 命中的锁定目录，如果没有命中返回 null
 */
function checkContentForLockedDirs(content: string): string | null {
  if (_lockedDirs.size === 0) return null
  const contentLower = content.toLowerCase().replace(/\//g, '\\')
  for (const lockedDir of _lockedDirs) {
    if (contentLower.includes(lockedDir)) {
      return lockedDir
    }
  }
  return null
}

/**
 * 检查脚本/文件内容中是否包含对保护目录（静态黑名单）的路径引用
 * ★ 兜底防线：即使 _lockedDirs 因正则问题没正确锁定，只要脚本内容
 *   包含保护目录的展开路径，也直接 block。
 *
 * 注意：只检查凭据/密钥类目录（CREDENTIAL_DIR_PATTERNS），不检查 OS 核心目录
 *   和 C:\Users，避免正常脚本被误拦截。
 * @returns 命中的保护目录，如果没有命中返回 null
 */
function checkContentForProtectedDirs(content: string): string | null {
  const contentLower = content.toLowerCase().replace(/\//g, '\\')
  // 使用凭据目录列表（比 PROTECTED_DIR_PATTERNS 更精确，不含 OS 核心/C:\Users 等宽泛目录）
  const credentialDirs = getExpandedCredentialDirs()

  for (const credDir of credentialDirs) {
    const credDirLower = credDir.toLowerCase()
    if (contentLower.includes(credDirLower)) {
      return credDir
    }
  }
  return null
}

/**
 * 从 exec 命令中提取脚本文件路径并检查其内容是否引用凭据保护目录
 *
 * ★ 防护攻击模式：AI 先用 write_to_file 将恶意脚本写入非保护目录（如 .qclaw/workspace/），
 *   然后用 exec 执行该脚本。exec 只检查命令路径不检查脚本内容，
 *   导致脚本以正常权限执行，成功删除/修改保护目录中的文件。
 *
 * @returns 命中的凭据目录路径，如果没命中返回 null
 */
function checkExecScriptContent(command: string): string | null {
  const fs = require('fs')
  const pathMod = require('path')

  // 匹配常见的脚本执行模式，提取脚本文件路径
  // 支持：python script.py, powershell -File script.ps1, node script.js, bash script.sh 等
  const SCRIPT_EXEC_PATTERNS = [
    // python "path/to/script.py" 或 python path/to/script.py
    /(?:python[23]?|py)\s+(?:-\S+\s+)*"([^"]+\.py)"/i,
    /(?:python[23]?|py)\s+(?:-\S+\s+)*'([^']+\.py)'/i,
    /(?:python[23]?|py)\s+(?:-\S+\s+)*(\S+\.py)(?:\s|$)/i,
    // powershell -File "path/to/script.ps1" 或 pwsh -File script.ps1
    /(?:powershell|pwsh)(?:\.exe)?\s+.*?-(?:File|f)\s+"([^"]+\.ps1)"/i,
    /(?:powershell|pwsh)(?:\.exe)?\s+.*?-(?:File|f)\s+'([^']+\.ps1)'/i,
    /(?:powershell|pwsh)(?:\.exe)?\s+.*?-(?:File|f)\s+(\S+\.ps1)(?:\s|$)/i,
    // node script.js
    /(?:node|tsx?)\s+(?:-\S+\s+)*"([^"]+\.(?:js|ts|mjs|cjs))"/i,
    /(?:node|tsx?)\s+(?:-\S+\s+)*(\S+\.(?:js|ts|mjs|cjs))(?:\s|$)/i,
    // bash/sh script.sh
    /(?:bash|sh|zsh)\s+(?:-\S+\s+)*"([^"]+\.sh)"/i,
    /(?:bash|sh|zsh)\s+(?:-\S+\s+)*(\S+\.sh)(?:\s|$)/i,
    // cmd /c script.bat / script.cmd
    /(?:cmd(?:\.exe)?\s+\/c\s+)"([^"]+\.(?:bat|cmd))"/i,
    /(?:cmd(?:\.exe)?\s+\/c\s+)(\S+\.(?:bat|cmd))(?:\s|$)/i,
    // 直接执行 .bat/.cmd 文件（Windows 下可以直接执行，无需 cmd /c）
    // 支持：xxx.bat, "xxx.bat", & "xxx.bat" (PowerShell), start xxx.bat
    /^"([^"]+\.(?:bat|cmd))"\s*$/i,                                    // 纯引号路径 "xxx.bat"
    /^(\S+\.(?:bat|cmd))\s*$/i,                                        // 纯路径 xxx.bat
    /^&\s*"([^"]+\.(?:bat|cmd))"/i,                                    // PowerShell & "xxx.bat"
    /^&\s*'([^']+\.(?:bat|cmd))'/i,                                    // PowerShell & 'xxx.bat'
    /^&\s*(\S+\.(?:bat|cmd))(?:\s|$)/i,                                // PowerShell & xxx.bat
    /(?:start|call)(?:\.exe)?\s+(?:\/\S+\s+)*"([^"]+\.(?:bat|cmd))"/i, // start "xxx.bat"
    /(?:start|call)(?:\.exe)?\s+(?:\/\S+\s+)*(\S+\.(?:bat|cmd))(?:\s|$)/i, // start xxx.bat
  ]

  let scriptPath: string | null = null
  for (const pattern of SCRIPT_EXEC_PATTERNS) {
    const match = command.match(pattern)
    if (match?.[1]) {
      scriptPath = match[1]
      break
    }
  }

  if (!scriptPath) return null

  // 解析为绝对路径
  try {
    const resolvedPath = pathMod.resolve(scriptPath)
    // 安全检查：只检查确实存在的文件，避免异常
    if (!fs.existsSync(resolvedPath)) return null

    // 限制文件大小（避免读取超大文件造成性能问题），最多 1MB
    const stat = fs.statSync(resolvedPath)
    if (stat.size > 1024 * 1024) return null

    const content = fs.readFileSync(resolvedPath, 'utf-8')
    return checkContentForProtectedDirs(content)
  } catch {
    // 读取失败（权限不足等），静默忽略
    return null
  }
}

const plugin = {
  id: 'tool-sandbox',
  name: '工具执行沙箱',
  description: '工具执行降权 — params 改写 + 外部 wrapper',

  register(api: any) {
    // ★ macOS 下完全屏蔽插件：不注册任何钩子，插件等于不存在
    if (process.platform === 'darwin') {
      console.log(`[${LOG_TAG}] skipped on macOS — plugin disabled for this platform`)
      return
    }

    const config = api.pluginConfig || {}

    // 从环境变量读取不变的基础设施参数（由 Electron createCleanEnv 注入）
    // 这些参数在进程生命周期内不会变化，所以在 register 时一次性读取
    const initialLowprivEnabled = process.env.QCLAW_TOOL_LOWPRIV === '1'
    const wrapperPath = process.env.QCLAW_TOOL_WRAPPER_PATH
    const sandboxLevel = process.env.QCLAW_TOOL_SANDBOX_LEVEL || 'standard'
    const appStorePath = process.env.QCLAW_APP_STORE_PATH
    const auditLog = config.auditLog !== false
    const blockPatterns = (config.blockPatterns || []).map((p: string) => new RegExp(p, 'i'))

    // ★ 平台检测：降权功能仅在 Windows 上可用
    const isPlatformSupported = process.platform === 'win32'

    /**
     * ★ 运行时动态判断降权是否启用
     *
     * 前置条件：
     *   - 平台必须是 Windows（macOS 暂不支持降权）
     *   - wrapper 路径必须存在（没有 wrapper 就无法降权）
     *
     * 优先级:
     *   1. app-store.json 中的 toolSandbox.enabled（实时读取，5 秒缓存）
     *   2. 环境变量 QCLAW_TOOL_LOWPRIV（进程启动时的初始值）
     *
     * 这使得用户在 UI 上切换开关后，无需重启 OpenClaw 进程即可生效。
     */
    const isLowprivActive = (): boolean => {
      if (!isPlatformSupported) return false // macOS / Linux 不支持降权
      if (!wrapperPath) return false
      const fileValue = readToolSandboxEnabledFromFile(appStorePath)
      if (fileValue !== null) return fileValue
      return initialLowprivEnabled
    }

    console.log(
      `[${LOG_TAG}] registered. platform=${process.platform}, platformSupported=${String(isPlatformSupported)}, ` +
      `lowpriv=${String(initialLowprivEnabled)}, ` +
      `wrapper=${wrapperPath || 'none'}, level=${sandboxLevel}, ` +
      `appStorePath=${appStorePath || 'none'} (dynamic reload: ${appStorePath ? 'enabled' : 'disabled'})`
    )

    // ---- before_tool_call: 命令改写 + 安全检查 ----
    api.on('before_tool_call', async (event: ToolCallEvent, _ctx: HookContext): Promise<BeforeToolCallResult | undefined> => {
      const { toolName, params, toolCallId } = event

      // ★ 每次 tool call 时动态检查降权状态（从 app-store.json 读取，带 5 秒缓存）
      const lowprivEnabled = isLowprivActive()

      if (auditLog) {
        console.log(
          `[${LOG_TAG}] before: ${toolName} (${toolCallId}) lowpriv=${String(lowprivEnabled)}`,
          JSON.stringify(params).slice(0, 500)
        )
      }

      // ★ 文件写操作工具：检查目标路径是否在受保护目录（直接 block，无法降权）
      //
      //   write_to_file / replace_in_file 等工具直接操作文件系统，不经过命令行，
      //   无法通过 lowpriv-launcher 降权包装。如果目标路径命中黑名单，直接阻止。
      //   这是对 exec 降权的补充防护，堵住通过文件操作工具绕过安全限制的漏洞。
      if (isFileWriteTool(toolName) && lowprivEnabled) {
        // 工具参数中的文件路径字段名可能是 file_path / filePath / path
        const filePath = String(params.file_path || params.filePath || params.path || '')

        if (filePath && isPathInProtectedDirs(filePath)) {
          console.log(
            `[${LOG_TAG}] blocked file write to protected dir: ${toolName} → ${filePath}`
          )
          return {
            block: true,
            blockReason: buildBlockMessage(`操作被拦截：${toolName} → ${filePath}`, filePath),
          }
        }

        // ★ 间接绕过防护（双重检查）：
        //   防止 AI 通过"写脚本到非保护目录 → 执行脚本"的方式绕过降权保护。
        //   例如：write_to_file 写入 fix-ssh.ps1，内容含 Remove-Item C:\Users\xxx\.ssh
        //
        //   检查 1: 写入内容是否引用了已锁定目录（动态锁定）
        //   检查 2: 写入内容是否引用了保护目录（静态黑名单）— 兜底防线
        const content = String(params.content || '')
        if (content) {
          // 检查 1: 已锁定目录
          const lockedDir = checkContentForLockedDirs(content)
          if (lockedDir) {
            console.log(
              `[${LOG_TAG}] 🔒 blocked file write containing locked dir path: ${toolName} → ${filePath} (content references: ${lockedDir})`
            )
            return {
              block: true,
              blockReason: buildBlockMessage(`操作被拦截：${toolName} → ${filePath}，写入内容引用了受保护目录`, lockedDir),
            }
          }

          // 检查 2: 静态保护目录（兜底防线 — 即使锁定机制因正则问题没正确锁定，
          //   只要脚本内容包含保护目录的路径，也直接 block）
          const contentProtectedDir = checkContentForProtectedDirs(content)
          if (contentProtectedDir) {
            console.log(
              `[${LOG_TAG}] 🛡️ blocked file write containing protected dir path: ${toolName} → ${filePath} (content references: ${contentProtectedDir})`
            )
            return {
              block: true,
              blockReason: buildBlockMessage(`操作被拦截：${toolName} → ${filePath}，写入内容引用了受保护目录`, contentProtectedDir),
            }
          }
        }
      }

      // ★ 文件读操作工具：检查目标路径是否在凭据目录（直接 block）
      //
      //   凭据/密钥文件（SSH 私钥、GPG 密钥、云凭据、浏览器数据等）不应被 AI 读取。
      //   即使是只读操作也可能导致凭据泄露（通过聊天记录、日志等途径）。
      if (isFileReadTool(toolName) && lowprivEnabled) {
        const filePath = String(params.file_path || params.filePath || params.path || '')

        if (filePath && isPathInCredentialDirs(filePath)) {
          console.log(
            `[${LOG_TAG}] blocked credential read: ${toolName} → ${filePath}`
          )
          return {
            block: true,
            blockReason: buildBlockMessage(`操作被拦截：${toolName} → ${filePath}（凭据目录禁止读取）`, filePath),
          }
        }
      }

      // ★ 核心：exec 工具命令改写（降权包装）
      if (isExecTool(toolName) && lowprivEnabled && wrapperPath) {
        const command = String(params.command || '')

        // ★ 拦截 elevated 提权请求
        //   当降权模式启用时，不允许 exec 工具请求提权执行（elevated: true）。
        //   如果放行，OpenClaw 运行时的 elevated 网关会返回原生错误信息
        //  （"elevated is not available right now"），模型不会看到我们的提示，
        //   可能会建议用户手动用管理员权限运行，而非引导用户关闭"工具权限限制"开关。
        if (params.elevated === true) {
          console.log(
            `[${LOG_TAG}] blocked elevated exec request: "${command.slice(0, 120)}"`
          )
          return {
            block: true,
            blockReason: buildBlockMessage(`提权操作被拦截：${command.slice(0, 200)}`),
          }
        }

        // 阻断高危命令（在改写之前检查，无论是否降权都生效）
        for (const pattern of blockPatterns) {
          if (pattern.test(command)) {
            return {
              block: true,
              blockReason: buildBlockMessage(`命令被拦截：匹配安全规则 ${pattern.source}`),
            }
          }
        }

        // ★ 注册表操作拦截：检查命令是否操作受保护的注册表路径
        //
        //   系统核心注册表（启动项、安全策略、认证数据库等）的读写操作
        //   可能导致持久化攻击、凭据窃取或系统破坏，需要直接 block。
        const regCheck = checkRegistryCommand(command)
        if (regCheck.blocked) {
          console.log(
            `[${LOG_TAG}] blocked registry operation: "${command.slice(0, 120)}" → ${regCheck.regPath} (${regCheck.desc})`
          )
          return {
            block: true,
            blockReason: buildBlockMessage(`注册表操作被拦截：${regCheck.regPath}（${regCheck.desc}）`, regCheck.regPath),
          }
        }

        // ★ 锁定目录检查：如果命令中的路径命中已锁定的目录，直接 block
        //   （即之前因权限拒绝而被锁定的目录）
        //   这防止 AI 模型通过反复尝试不同命令/方式绕过降权保护。
        const lockedDir = checkLockedDirs(command)
        if (lockedDir) {
          console.log(
            `[${LOG_TAG}] 🔒 blocked by locked dir: "${command.slice(0, 120)}" → ${lockedDir}`
          )
          return {
            block: true,
            blockReason: buildBlockMessage(`操作被拦截：目录已锁定`, lockedDir),
          }
        }

        // ★ 外部程序启动检测：如果命令的主要目的是启动 .exe / 打开应用程序，
        //   则跳过降权包装，避免子进程因 Low IL 权限不足而无法正常运行。
        //   安全保障：
        //   1. blockPatterns 仍然在上方生效，高危命令不会被放行
        //   2. ★ 如果目标 exe 在不受信目录（Downloads/Desktop/Temp 等）下，
        //      isAppLaunchCommand 会返回 false，命令不跳过降权（走正常沙箱路径）
        if (isAppLaunchCommand(command)) {
          console.log(
            `[${LOG_TAG}] app-launch detected, skip lowpriv wrapper: "${command.slice(0, 120)}"`
          )
          return undefined // 放行原始命令，不包装
        }

        // ★ 间接绕过防护（exec 层）：检查脚本文件内容是否引用了保护目录
        //
        //   攻击模式：AI 先用 write_to_file 将恶意脚本写到非保护目录（如 .qclaw/workspace/），
        //   然后用 exec 执行该脚本。exec 只检查命令路径，不检查脚本内容，
        //   所以脚本以正常权限执行，成功操作保护目录。
        //
        //   防护：当 exec 执行脚本文件时，读取脚本内容检查是否引用凭据目录。
        //   如果命中，强制使用降权包装执行（而非直接 block，因为脚本可能有合法用途）。
        const scriptProtectedDir = checkExecScriptContent(command)
        if (scriptProtectedDir) {
          console.log(
            `[${LOG_TAG}] 🛡️ script content references protected dir, forcing lowpriv: "${command.slice(0, 80)}..." (references: ${scriptProtectedDir})`
          )
          // 不直接放行，走下面的降权包装逻辑
        }

        // ★ 黑名单检测：如果命令操作的路径未命中受保护目录黑名单，
        //   则以正常权限执行（跳过降权包装）。
        //
        //   黑名单语义：系统关键目录（OS 核心、凭据密钥、浏览器数据等）受保护，
        //   操作这些目录中的内容需要降权执行。
        //   非黑名单目录 = 正常目录，允许 AI 以正常权限操作。
        //   无法从命令中提取路径 → 放行，不降权（blockPatterns 已在上方拦截高危命令）。
        //   安全保障：blockPatterns 在上方已生效，高危命令不会被放行。
        if (!scriptProtectedDir && !isCommandInProtectedDirs(command)) {
          console.log(
            `[${LOG_TAG}] command paths not in protected dirs, skip lowpriv wrapper: "${command.slice(0, 120)}"`
          )
          return undefined // 非受保护目录，正常权限执行
        }

        // ★ 确定触发降权的保护目录（用于 tracking 和日志）
        // 注意：排除逻辑必须与 isCommandInProtectedDirs 完全一致，否则会导致错误的目录被锁定
        const triggerDir = scriptProtectedDir || (() => {
          // 从命令中提取命中的保护目录
          const path = require('path')
          const commandPaths = extractPathsFromCommand(command)
          const protectedDirs = getExpandedProtectedDirs()
          const userProfile = (process.env.USERPROFILE || '').toLowerCase()
          const userProfileWithSep = userProfile ? (userProfile.endsWith(path.sep) ? userProfile : userProfile + path.sep) : ''
          const systemRoot = (process.env.SystemRoot || 'C:\\Windows').toLowerCase()

          for (const cmdPath of commandPaths) {
            const normalized = path.resolve(cmdPath).toLowerCase()
            for (const pd of protectedDirs) {
              const pdWithSep = pd.endsWith(path.sep) ? pd : pd + path.sep
              if (normalized === pd || normalized.startsWith(pdWithSep)) {
                // ★ 特殊处理：C:\Windows 需排除 Temp 目录（与 isCommandInProtectedDirs 保持一致）
                if (pd === systemRoot) {
                  const tempDir = systemRoot + path.sep + 'temp'
                  const tempDirWithSep = tempDir + path.sep
                  if (normalized === tempDir || normalized.startsWith(tempDirWithSep)) {
                    continue // Windows Temp 目录，跳过
                  }
                  // ★ 处理冗余父目录情况：cmdPath 是 C:\Windows 本身（由 extractPaths 的 dirname 产生）
                  // 如果所有原始路径都在 Temp 目录内，则 C:\Windows 只是冗余父目录，不应作为 triggerDir
                  if (normalized === pd) {
                    const hasPathOutsideTemp = commandPaths.some(cp => {
                      const cpNorm = path.resolve(cp).toLowerCase()
                      // 跳过 C:\Windows 本身
                      if (cpNorm === pd) return false
                      // 检查是否在 Temp 目录外
                      return !(cpNorm === tempDir || cpNorm.startsWith(tempDirWithSep))
                    })
                    if (!hasPathOutsideTemp) {
                      continue // 所有真实路径都在 Temp 内，C:\Windows 只是冗余父目录，跳过
                    }
                  }
                }

                // ★ 特殊处理：C:\Users 需排除当前用户目录（与 isCommandInProtectedDirs 保持一致）
                // 同时需要处理 cmdPath 本身是 C:\Users（由 extractPaths 的 dirname 产生）的情况
                if (pd.endsWith('\\users')) {
                  // 情况1：cmdPath 是当前用户目录或其子目录 → 跳过（正常操作）
                  if (userProfileWithSep && (normalized === userProfile || normalized.startsWith(userProfileWithSep))) {
                    continue
                  }
                  // 情况2：cmdPath 就是 C:\Users 本身（由 extractPaths 添加的父目录冗余）
                  // 如果原始操作路径都在当前用户目录下，则不应该用 C:\Users 作为 triggerDir
                  // 检查是否所有原始路径都在当前用户目录下
                  if (normalized === pd && userProfileWithSep) {
                    // cmdPath 是 C:\Users 本身，检查是否有其他路径在用户目录外
                    const hasPathOutsideUserProfile = commandPaths.some(cp => {
                      const cpNorm = path.resolve(cp).toLowerCase()
                      // 跳过 C:\Users 本身（它是我们要判断的）
                      if (cpNorm === pd) return false
                      // 检查是否在用户目录外
                      return !cpNorm.startsWith(userProfileWithSep) && cpNorm !== userProfile
                    })
                    if (!hasPathOutsideUserProfile) {
                      continue // 所有真实路径都在用户目录内，C:\Users 只是冗余父目录，跳过
                    }
                  }
                }

                return pd
              }
            }
          }
          return 'unknown'
        })()

        // ★ 技能管理命令检测：npx skills / clawhub 等需要写入技能目录，
        //   降权后这些目录不可写导致安装必然失败。以正常权限放行。
        //   安全保障：blockPatterns 仍然在上方生效，高危命令不会被放行。
        //   安全保障：正则使用 $ 行尾锚定 + 安全字符集，防止 shell 元字符注入绕过降权。
        if (isSkillManagementCommand(command)) {
          console.warn(
            `[${LOG_TAG}] ⚠ SECURITY-AUDIT: skill-management bypass lowpriv, command="${command}", toolCallId="${toolCallId}"`
          )
          return undefined // 放行原始命令，不包装
        }

        // ★ 按平台改写 params.command（传递降权级别）
        const wrappedCommand = wrapCommandForPlatform(command, wrapperPath, sandboxLevel)
        if (wrappedCommand) {
          // ★ 记录降权追踪信息，供 tool_result_persist 使用
          _lowprivTracking.set(toolCallId, {
            protectedDir: triggerDir,
            originalCommand: command.slice(0, 200),
          })
          console.log(
            `[${LOG_TAG}] rewrite (${sandboxLevel}): "${command.slice(0, 80)}..." → lowpriv wrapper`
          )
          return {
            params: { ...params, command: wrappedCommand },
          }
        } else {
          // 无法包装（不支持的平台），回退放行 + 告警
          console.warn(
            `[${LOG_TAG}] platform ${process.platform} not supported for command wrapping, passing through`
          )
        }
      }

      return undefined // 放行
    })

    // ---- after_tool_call: 审计日志 ----
    api.on('after_tool_call', async (event: ToolCallEvent, _ctx: HookContext) => {
      const output = typeof event.result?.content === 'string'
        ? event.result.content
        : JSON.stringify(event.result?.content ?? '')

      if (auditLog) {
        const preview = output.slice(0, 200) || '(no result)'
        console.log(
          `[${LOG_TAG}] after: ${event.toolName} (${event.toolCallId})`,
          preview
        )
      }
    })

    // ---- tool_result_persist: 降权命令错误检测 + 权限拒绝检测 → 覆盖持久化消息为终止性错误 ----
    //
    // ★ 为什么放在 tool_result_persist 而非 after_tool_call：
    //   after_tool_call 是 fire-and-forget（void hook），对 event.result 的修改
    //   不保证能反映到写入 session JSONL 的持久化消息上。
    //   tool_result_persist 是同步链式 hook，返回 { message } 可以 **可靠地** 替换
    //   即将写入 session transcript 的 toolResult 消息，确保 LLM 下一轮读到的
    //   是我们注入的终止性错误，而非原始的"权限拒绝"输出片段。
    //
    // ★ 两层检测机制：
    //   1. 降权追踪检测：如果命令是因命中保护目录而被降权执行的（通过 _lowprivTracking 查询），
    //      且输出中包含任何错误迹象（Error、WinError、Access denied 等），
    //      立即覆盖为终止性消息。这解决了 AI 因不知道"是安全策略导致的失败"而反复换方式尝试的问题。
    //   2. 通用权限拒绝检测：兜底检测，无论命令是否被降权，只要输出中包含权限拒绝，
    //      锁定相关目录 + 覆盖为终止性消息。
    //
    // ★ hook 协议：
    //   - 同步（禁止返回 Promise）
    //   - event: { toolName, toolCallId, message, isSynthetic }
    //   - message: { role: "toolResult", toolCallId, content: [{type:"text", text:"..."}], isError?, ... }
    //   - 返回 { message: newMsg } 替换持久化消息；不返回或返回 undefined 则保持原消息
    api.on('tool_result_persist', (event: {
      toolName: string
      toolCallId: string
      message: {
        role: string
        toolCallId?: string
        toolName?: string
        content: Array<{ type: string; text: string }>
        isError?: boolean
        timestamp?: number
        [key: string]: unknown
      }
      isSynthetic: boolean
    }, _ctx: HookContext) => {
      // 仅在降权启用 + exec 工具时检测
      if (!isLowprivActive() || !isExecTool(event.toolName)) return

      // 从 message.content 提取文本
      const textParts: string[] = []
      if (Array.isArray(event.message.content)) {
        for (const block of event.message.content) {
          if (block.type === 'text' && typeof block.text === 'string') {
            textParts.push(block.text)
          }
        }
      }
      const output = textParts.join('\n')
      if (!output) return

      // ★ 第 1 层：降权追踪检测
      //   如果命令是因命中保护目录而被降权执行的，且输出中包含错误，
      //   立即覆盖为终止性消息，告诉 AI 这是安全策略导致的、不要再尝试。
      const trackingInfo = _lowprivTracking.get(event.toolCallId)
      if (trackingInfo) {
        _lowprivTracking.delete(event.toolCallId) // 消费后删除，防止内存泄漏

        // 检测降权执行后的错误迹象（比权限拒绝检测更宽泛）
        const hasError = detectLowprivError(output)
        if (hasError) {
          const protectedDir = trackingInfo.protectedDir
          console.log(
            `[${LOG_TAG}] ⚠️ lowpriv exec error detected (tracking): toolCallId=${event.toolCallId}, protectedDir=${protectedDir}`
          )
          // 锁定该保护目录
          lockProtectedDir(protectedDir)

          const errorPayload = buildTerminalErrorPayload(
            event.toolName,
            `操作被拦截（降权执行失败）`,
            protectedDir,
          )

          return {
            message: {
              ...event.message,
              content: [{ type: 'text', text: errorPayload }],
              isError: true,
            },
          }
        }
      }

      // ★ 第 2 层：通用权限拒绝检测（兜底）
      const permResult = detectPermissionDenied(output)
      if (!permResult.detected) return

      console.log(`[${LOG_TAG}] ⚠️ permission denied detected in tool_result_persist:`,
        JSON.stringify(permResult.directories))

      // ★ 锁定被拒绝的目录：后续对这些目录的任何操作都直接 block
      for (const dir of permResult.directories) {
        lockProtectedDir(dir)
      }

      // ★ 构造终止性错误 payload，替换原始 toolResult 消息
      const errorPayload = buildTerminalErrorPayload(
        event.toolName,
        `操作被拦截（权限被拒绝）`,
        permResult.directories.join(', '),
      )

      return {
        message: {
          ...event.message,
          content: [{ type: 'text', text: errorPayload }],
          isError: true,
        },
      }
    })
  },
}

// ---- 降权命令错误检测 ----

/**
 * 检测降权执行后的错误迹象
 *
 * ★ 与 PERMISSION_DENIED_PATTERNS 的区别：
 *   PERMISSION_DENIED_PATTERNS 精确匹配特定的权限拒绝错误消息格式。
 *   本函数更宽泛，检测降权命令输出中的「任何错误迹象」——
 *   因为降权执行失败的根因就是安全策略，无论具体错误消息是什么格式。
 *
 *   触发条件：命令必须是 _lowprivTracking 中记录的降权命令（由 before_tool_call 标记）。
 *   因此不会误伤正常命令的合法错误输出。
 */
function detectLowprivError(output: string): boolean {
  // 匹配各种权限/错误关键词（宽泛匹配，因为只在降权追踪命中时使用）
  const ERROR_INDICATORS = [
    // Windows 权限错误
    /Access is denied/i,
    /WinError 5/i,                              // Python Windows: [WinError 5] 拒绝访问
    /ERROR_ACCESS_DENIED/i,
    /UnauthorizedAccess/i,
    // Python 权限错误
    /PermissionError/i,
    /\[Errno 13\]/i,
    /\[WinError \d+\]/i,                        // 其他 Windows 错误码
    // Node.js 权限错误
    /EACCES/i,
    /EPERM/i,
    // 通用权限错误
    /permission denied/i,
    /not permitted/i,
    // 中文错误（UTF-8 正常解码时）
    /拒绝访问/,
    /权限不足/,
    /没有权限/,
    /访问被拒绝/,
    // GBK 乱码中的关键特征（PowerShell 降权后的 UTF-8/GBK 冲突）
    // "拒绝访问" GBK 编码在 UTF-8 下读出来常见的乱码片段
    /\xdc\xbe\xdc/,
    // 通用错误 + 路径组合（降权导致的错误通常带路径）
    /Error:.*[A-Za-z]:\\/i,
  ]

  for (const pattern of ERROR_INDICATORS) {
    if (pattern.test(output)) return true
  }

  return false
}

// ---- 权限拒绝检测 ----

const PERMISSION_DENIED_PATTERNS = [
  // PowerShell / .NET (English)
  /Access to the path '([^']+)' is denied/gi,
  /UnauthorizedAccessException.*?'([^']+)'/gi,
  // Windows cmd rmdir/del 格式: "C:\path\file - Access is denied."
  // ★ 必须放在通用 "Access is denied" 之前，因为该模式更精确
  /([A-Za-z]:\\[^\r\n]+?)\s+-\s+Access is denied/gi,
  // Windows 通用 (English)
  /Access is denied[\s.]*(?:.*?['"]([^'"]+)['"])?/gi,
  // Node.js
  /EACCES: permission denied,\s*\w+\s+'([^']+)'/gi,
  /EPERM: operation not permitted,\s*\w+\s+'([^']+)'/gi,
  // Python
  /PermissionError: \[Errno 13\] Permission denied:\s*'([^']+)'/gi,
  // Python Windows: [WinError 5] 拒绝访问: 'C:\path\file' 或 Access is denied
  /\[WinError 5\].*?['"]([^'"]+)['"]?/gi,
  /\[WinError 5\]/gi,
  // Git
  /unable to (?:create|write) (?:file |directory )?'?([^':\n]+)'?:?\s*Permission denied/gi,
  // Rust / Go
  /Os error 5.*?['"]([^'"]+)['"]?/gi,
  // 通用 POSIX
  /permission denied:\s*'?([^\s'\n]+)/gi,
  // ---- OpenClaw 运行时 elevated 权限网关错误 ----
  // "elevated is not available right now (runtime=direct)." 等
  // 这是 OpenClaw 自身拒绝提权请求时返回的错误，不包含路径信息（捕获组可选）
  /elevated is not available right now/gi,
  // ---- 中文环境 PowerShell 错误消息（UTF-8 正常解码时匹配） ----
  // "对路径"X"的访问被拒绝" / "无法删除项 X: 对路径的访问被拒绝"
  /对路径[""']([^""']+)[""']的访问被拒绝/gi,
  /(?:无法删除项|无法移除项目|无法移动项目|无法创建项目|无法写入|无法访问)\s+([A-Za-z]:[^\s:]+)/gi,
  // "拒绝访问" / "没有权限" / "权限不足"
  /拒绝访问[。.]?\s*(?:.*?['"""]([^'"""\n]+)['"""])?/gi,
]

interface PermissionDeniedInfo {
  detected: boolean
  paths: string[]       // 被拒绝的文件/目录路径
  directories: string[] // 推断出需要授权的目录
}

function detectPermissionDenied(output: string): PermissionDeniedInfo {
  const paths: string[] = []
  let detected = false

  for (const pattern of PERMISSION_DENIED_PATTERNS) {
    pattern.lastIndex = 0  // 全局正则复用需重置
    let match
    while ((match = pattern.exec(output)) !== null) {
      detected = true // 任何模式匹配即视为检测到权限拒绝
      if (match[1]?.length > 2) {
        paths.push(match[1].trim())
      }
    }
  }

  if (!detected) {
    return { detected: false, paths: [], directories: [] }
  }

  const path = require('path')
  const dirs: string[] = []
  for (const p of paths) {
    // ★ 同时加入路径本身和其父目录，确保无论路径指向文件还是目录都能命中：
    //   - 如果 p 是文件路径（如 .ssh\config），dirname 得到 .ssh（正确目录）
    //   - 如果 p 是目录路径（如 .ssh），dirname 得到上级（也有意义）
    //   - 重复项后续通过 Set 去重
    dirs.push(p)
    const parent = path.dirname(p)
    if (parent && parent !== p) {
      dirs.push(parent)
    }
  }

  // 如果匹配到了权限拒绝但没有提取到具体路径（如 elevated 错误），
  // 使用通用描述
  const directories = dirs.length > 0
    ? [...new Set(dirs)]
    : ['（elevated 权限被拒绝，无具体目录信息）']

  return {
    detected: true,
    paths: [...new Set(paths)],
    directories,
  }
}

export default plugin
