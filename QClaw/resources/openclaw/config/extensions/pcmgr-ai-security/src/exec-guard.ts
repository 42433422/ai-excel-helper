/**
 * Exec Guard — 不受信目录下可执行文件执行拦截
 *
 * 纵深防御：即使 LLM 被上下文投毒诱导后决定执行本地可执行文件，
 * 本模块在 before_tool_call 阶段硬性拦截来自 Downloads/Desktop/Temp 等
 * 不受信目录的 .exe/.bat/.cmd/.msi/.ps1 等可执行文件。
 *
 * 设计原则：
 * - 仅拦截 exec 类工具（exec/bash/bash_tool/execute_command）
 * - 仅拦截目标为不受信目录下的可执行文件
 * - 系统安装目录（Program Files、Windows）下的程序放行
 * - 拦截时返回人类可读的提示消息，告知用户替代方案
 * - 不依赖 OpenClaw 内置的 Exec Approval System，作为独立的安全层
 */

import path from "node:path";

// ---- Exec 工具名集合 ----

const EXEC_TOOLS = new Set([
  "exec",
  "bash",
  "bash_tool",
  "execute_command",
]);

// ---- 危险可执行文件扩展名 ----

const DANGEROUS_EXTS = new Set([
  ".exe",
  ".bat",
  ".cmd",
  ".msi",
  ".scr",
  ".pif",
  ".com",
  ".vbs",
  ".vbe",
  ".wsf",
  ".wsh",
  ".ps1",
]);

// ---- 不受信目录关键词（小写）----
// 这些目录通常包含用户下载的、来源不明的文件

const UNTRUSTED_DIR_SEGMENTS_WIN = [
  "\\downloads\\",
  "/downloads/",
  "\\desktop\\",
  "/desktop/",
  "\\temp\\",
  "/temp/",
  "\\tmp\\",
  "/tmp/",
  "\\appdata\\",
  "/appdata/",
  "\\public\\",
  "/public/",
];

const UNTRUSTED_DIR_SEGMENTS_MAC = [
  "/downloads/",
  "/desktop/",
  "/tmp/",
  "/public/",
];

// ---- 受信系统安装目录前缀（小写）----
// 这些目录下的程序被视为合法安装软件

const TRUSTED_DIR_PREFIXES_WIN = [
  "c:\\windows\\",
  "c:/windows/",
  "c:\\program files\\",
  "c:/program files/",
  "c:\\program files (x86)\\",
  "c:/program files (x86)/",
];

const TRUSTED_DIR_PREFIXES_MAC = [
  "/usr/",
  "/bin/",
  "/sbin/",
  "/applications/",
  "/system/",
];

// ---- 核心提取逻辑 ----

/**
 * 从命令字符串中提取被直接执行的可执行文件路径
 *
 * 支持的命令模式：
 * - Start-Process "path\to\file.exe"
 * - Start-Process 'path\to\file.exe'
 * - Start-Process path\to\file.exe
 * - & 'path\to\file.exe'
 * - & "path\to\file.exe"
 * - cmd /c "path\to\file.exe"
 * - cmd /c path\to\file.exe
 * - Invoke-Item "path\to\file.exe"
 * - ./file.exe / .\file.exe
 * - 直接路径：C:\Users\xxx\Downloads\file.exe
 * - explorer "path\to\file.exe" (非目录)
 */
function extractExecutablePaths(command: string): string[] {
  const results: string[] = [];
  const trimmed = command.trim();

  // 模式 1: Start-Process / saps
  // Start-Process "C:\path\to\file.exe" -ArgumentList ...
  // Start-Process 'C:\path\to\file.exe'
  // Start-Process C:\path\to\file.exe
  const startProcessMatch = trimmed.match(
    /^(?:Start-Process|saps)\s+(?:(?:-FilePath|-Path)\s+)?['"]?([^'";\s|&]+\.(?:exe|bat|cmd|msi|scr|pif|com|vbs|vbe|wsf|wsh|ps1))['"]?/i
  );
  if (startProcessMatch?.[1]) {
    results.push(startProcessMatch[1]);
  }

  // 模式 2: & 'path.exe' 或 & "path.exe"（PowerShell 调用）
  const ampersandMatch = trimmed.match(
    /^&\s+['"]([^'"]+\.(?:exe|bat|cmd|msi|scr|pif|com|vbs|vbe|wsf|wsh|ps1))['"]/i
  );
  if (ampersandMatch?.[1]) {
    results.push(ampersandMatch[1]);
  }
  // & path.exe（无引号）
  const ampersandNoQuoteMatch = trimmed.match(
    /^&\s+([^'";\s|&]+\.(?:exe|bat|cmd|msi|scr|pif|com|vbs|vbe|wsf|wsh|ps1))/i
  );
  if (ampersandNoQuoteMatch?.[1]) {
    results.push(ampersandNoQuoteMatch[1]);
  }

  // 模式 3: cmd /c "path.exe" 或 cmd /c path.exe
  const cmdMatch = trimmed.match(
    /^cmd\s+\/c\s+['"]?([^'";\s|&]+\.(?:exe|bat|cmd|msi|scr|pif|com|vbs|vbe|wsf|wsh|ps1))['"]?/i
  );
  if (cmdMatch?.[1]) {
    results.push(cmdMatch[1]);
  }

  // 模式 4: Invoke-Item / ii
  const invokeMatch = trimmed.match(
    /^(?:Invoke-Item|ii)\s+['"]?([^'";\s|&]+\.(?:exe|bat|cmd|msi|scr|pif|com|vbs|vbe|wsf|wsh|ps1))['"]?/i
  );
  if (invokeMatch?.[1]) {
    results.push(invokeMatch[1]);
  }

  // 模式 5: explorer "path\file.exe"（排除纯目录路径）
  const explorerMatch = trimmed.match(
    /^explorer(?:\.exe)?\s+['"]?([^'";\s|&]+\.(?:exe|bat|cmd|msi|scr|pif|com|vbs|vbe|wsf|wsh|ps1))['"]?/i
  );
  if (explorerMatch?.[1]) {
    results.push(explorerMatch[1]);
  }

  // 模式 6: 直接路径执行
  // 匹配以驱动器盘符开头或 ./ .\ 开头，以可执行扩展名结尾的路径
  // 例如: C:\Users\xxx\Downloads\openvpn.exe
  //       .\openvpn.exe
  //       ./openvpn.exe
  const directPathMatch = trimmed.match(
    /^['"]?([a-zA-Z]:[\\\/][^'";\s|&]*\.(?:exe|bat|cmd|msi|scr|pif|com|vbs|vbe|wsf|wsh|ps1))['"]?/i
  );
  if (directPathMatch?.[1]) {
    results.push(directPathMatch[1]);
  }
  const relativePathMatch = trimmed.match(
    /^['"]?(\.[\\\/][^'";\s|&]*\.(?:exe|bat|cmd|msi|scr|pif|com|vbs|vbe|wsf|wsh|ps1))['"]?/i
  );
  if (relativePathMatch?.[1]) {
    results.push(relativePathMatch[1]);
  }

  // 模式 7: macOS open 命令
  if (process.platform === "darwin") {
    const openMatch = trimmed.match(
      /^open\s+['"]?([^'";\s|&]+)['"]?/i
    );
    if (openMatch?.[1]) {
      results.push(openMatch[1]);
    }
  }

  // 去重
  return [...new Set(results)];
}

/**
 * 判断可执行文件路径是否位于不受信目录
 */
function isInUntrustedDirectory(filePath: string): boolean {
  const normalized = filePath.replace(/\\/g, "/").toLowerCase();

  // 先检查是否在受信目录中
  const trustedPrefixes =
    process.platform === "win32"
      ? TRUSTED_DIR_PREFIXES_WIN
      : TRUSTED_DIR_PREFIXES_MAC;

  for (const prefix of trustedPrefixes) {
    if (normalized.startsWith(prefix.replace(/\\/g, "/").toLowerCase())) {
      return false; // 受信目录，放行
    }
  }

  // 检查路径中是否包含不受信目录段
  const untrustedSegments =
    process.platform === "win32"
      ? UNTRUSTED_DIR_SEGMENTS_WIN
      : UNTRUSTED_DIR_SEGMENTS_MAC;

  // 在路径前后加分隔符以确保匹配完整目录段
  const normalizedWithTrailing = normalized.endsWith("/")
    ? normalized
    : normalized + "/";
  const pathToCheck = "/" + normalizedWithTrailing;

  for (const segment of untrustedSegments) {
    const normalizedSegment = segment.replace(/\\/g, "/").toLowerCase();
    if (pathToCheck.includes(normalizedSegment)) {
      return true; // 不受信目录
    }
  }

  return false;
}

/**
 * 判断文件扩展名是否为危险可执行文件
 */
function isDangerousExtension(filePath: string): boolean {
  const ext = path.extname(filePath).toLowerCase();
  return DANGEROUS_EXTS.has(ext);
}

// ---- 对外接口 ----

export interface ExecGuardResult {
  blocked: boolean;
  filePath?: string;
  reason?: string;
  dirSegment?: string;
}

/**
 * 检查 exec 工具的 command 参数是否为不受信目录下的可执行文件执行
 *
 * @param toolName 工具名
 * @param command  命令字符串
 * @returns 检查结果，blocked=true 表示应拦截
 */
export function checkExecGuard(
  toolName: string,
  command: string | undefined
): ExecGuardResult {
  // 仅处理 exec 类工具
  if (!EXEC_TOOLS.has(toolName)) {
    return { blocked: false };
  }

  if (!command || typeof command !== "string") {
    return { blocked: false };
  }

  const exePaths = extractExecutablePaths(command);

  for (const exePath of exePaths) {
    // 检查扩展名是否为危险类型
    if (!isDangerousExtension(exePath)) {
      continue;
    }

    // 检查是否在不受信目录中
    if (isInUntrustedDirectory(exePath)) {
      const fileName = path.basename(exePath);
      const dirName = path.dirname(exePath);

      return {
        blocked: true,
        filePath: exePath,
        reason:
          `安全策略拦截：检测到执行不受信目录下的可执行文件 "${fileName}"（路径: ${dirName}）。` +
          `出于安全考虑，QClaw 不允许自动执行 Downloads、Desktop、Temp 等目录下的可执行文件。` +
          `如果这是您信任的程序，请在文件管理器中手动双击运行，或将其移至受信目录后重试。`,
        dirSegment: dirName,
      };
    }
  }

  return { blocked: false };
}

/**
 * 工具名是否属于 exec 类工具
 */
export function isExecTool(toolName: string): boolean {
  return EXEC_TOOLS.has(toolName);
}
