/**
 * 文件日志模块（无外部依赖，避免循环引用）
 *
 * 默认落盘到应用日志目录：
 *   - Windows: %APPDATA%\QClaw\logs\
 *   - macOS:   ~/Library/Logs/QClaw/
 * 调用 setLogFilePath 可切换路径。
 *
 * 日志开关策略（不区分环境，统一行为）：
 *   - 默认不生成日志
 *   - 在日志目录放置 `.debug-enabled` 文件后重启进程即可开启
 *   - 判断仅在进程启动时执行一次，零运行时开销
 *
 * 开关文件路径：
 *   - Windows: %APPDATA%\QClaw\logs\.debug-enabled
 *   - macOS:   ~/Library/Logs/QClaw/.debug-enabled
 */

import fs, { existsSync } from "node:fs";
import path from "node:path";

/** 日志开关标记文件名：在日志目录下创建此空文件即可开启日志 */
const DEBUG_MARKER_FILE = ".debug-enabled";

/** 默认日志目录：应用日志目录 */
function getDefaultLogDir(): string {
  if (process.platform === "win32") {
    const appData = process.env.APPDATA ?? path.join(process.env.USERPROFILE ?? "", "AppData", "Roaming");
    return path.join(appData, "QClaw", "logs");
  }
  // macOS: ~/Library/Logs/QClaw/
  const home = process.env.HOME ?? "";
  return path.join(home, "Library", "Logs", "QClaw");
}

/**
 * 日志是否启用——进程启动时检测一次，结果缓存，后续零 I/O 开销。
 * 删除或创建 .debug-enabled 文件后需重启进程生效。
 */
const _logEnabled: boolean = existsSync(path.join(getDefaultLogDir(), DEBUG_MARKER_FILE));

let logFilePath = "";

function getEffectiveLogPath(): string {
  if (logFilePath) return logFilePath;
  return path.join(getDefaultLogDir(), "pcmgr-ai-security_debug.log");
}

export function setLogFilePath(filePath: string): void {
  logFilePath = filePath;
}

export function getLogFilePath(): string {
  return getEffectiveLogPath();
}

/** 确保目标目录存在（仅在首次写入时创建，结果缓存） */
let dirEnsured = false;
function ensureLogDir(filePath: string): void {
  if (dirEnsured) return;
  const dir = path.dirname(filePath);
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }
  dirEnsured = true;
}

/**
 * 通用文件日志。
 *
 * - 默认不写日志
 * - 日志目录存在 `.debug-enabled` 文件时才落盘
 * - 开关在进程启动时一次性确定，fileLog 调用本身零 I/O 开销（未启用时）
 */
export function fileLog(message: string): void {
  if (!_logEnabled) return;

  const timestamp = new Date().toISOString();
  const target = getEffectiveLogPath();
  ensureLogDir(target);
  fs.appendFileSync(target, `[${timestamp}] ${message}\n`, "utf-8");
}
