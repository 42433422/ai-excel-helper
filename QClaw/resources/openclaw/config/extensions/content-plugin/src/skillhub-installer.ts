/**
 * skillhub_install — SkillHub Skill 安装工具
 *
 * 帮助用户自动安装 SkillHub CLI 和 Skill。
 * 自动检测操作系统类型 (macOS / Linux / Windows)，
 * 选择对应的安装命令执行。
 *
 * 核心设计：**一步到位，不让 LLM 思考环境问题**
 *   - install_cli 自动检测 + 安装全部依赖（python3、curl）
 *   - install_skill 如果发现 CLI 未安装，自动先安装 CLI
 *
 * 使用方式：
 *   - 安装 CLI:   skillhub_install install_cli
 *   - 安装 Skill:  skillhub_install install_skill <skillName>
 *   - 检查环境:   skillhub_install check_env
 */

import { execSync, exec, execFile } from "node:child_process";
import os from "node:os";
import fs from "node:fs";
import path from "node:path";
import https from "node:https";
import http from "node:http";
import zlib from "node:zlib";

// ============================================================================
// 常量
// ============================================================================

const LOG_TAG = "[skillhub-installer]";

/** SkillHub CLI 安装脚本地址 */
const INSTALL_SCRIPT_URL =
  "https://skillhub-1388575217.cos.ap-guangzhou.myqcloud.com/install/install.sh";

/** Windows 版安装包地址（tar.gz 包含 CLI 全部文件） */
const INSTALL_PACKAGE_URL =
  "https://skillhub-1388575217.cos.ap-guangzhou.myqcloud.com/install/latest.tar.gz";

// ============================================================================
// 类型定义
// ============================================================================

/** 工具入参 */
interface SkillHubInstallerParams {
  /** 操作类型 */
  action: "install_cli" | "install_skill" | "check_env";
  /** Skill 名称（action=install_skill 时必填） */
  skillName?: string;
  /** 是否安装 CLI 时同时安装默认 Skills (默认 true) */
  withDefaultSkills?: boolean;
}

/** 平台类型 */
type Platform = "macos" | "linux" | "windows" | "unsupported";

/** 环境检查结果 */
interface EnvCheckResult {
  platform: string;
  platformId: Platform;
  python3: { available: boolean; path?: string; version?: string };
  curl: { available: boolean };
  bash: { available: boolean };
  skillhubCli: { installed: boolean; version?: string };
}

// ============================================================================
// 响应构造辅助
// ============================================================================

const textResult = (data: unknown) => ({
  content: [{ type: "text" as const, text: JSON.stringify(data, null, 2) }],
});

// ============================================================================
// 平台检测
// ============================================================================

function detectPlatform(): Platform {
  const platform = os.platform();
  switch (platform) {
    case "darwin":
      return "macos";
    case "linux":
      return "linux";
    case "win32":
      return "windows";
    default:
      return "unsupported";
  }
}

function getPlatformLabel(platform: Platform): string {
  switch (platform) {
    case "macos":
      return "macOS";
    case "linux":
      return "Linux";
    case "windows":
      return "Windows";
    default:
      return "未知";
  }
}

// ============================================================================
// 命令执行
// ============================================================================

/**
 * 同步执行 shell 命令并返回 stdout
 */
function runCommand(cmd: string, options?: { shell?: string; timeout?: number }): {
  success: boolean;
  stdout: string;
  stderr: string;
} {
  try {
    const stdout = execSync(cmd, {
      encoding: "utf-8",
      timeout: options?.timeout ?? 120_000,
      shell: options?.shell,
      stdio: ["pipe", "pipe", "pipe"],
    });
    return { success: true, stdout: stdout.trim(), stderr: "" };
  } catch (err: any) {
    return {
      success: false,
      stdout: (err.stdout ?? "").toString().trim(),
      stderr: (err.stderr ?? err.message ?? "").toString().trim(),
    };
  }
}

/**
 * 异步执行 shell 命令（用于长时间安装任务）
 */
function runCommandAsync(cmd: string, options?: { shell?: string; timeout?: number }): Promise<{
  success: boolean;
  stdout: string;
  stderr: string;
}> {
  return new Promise((resolve) => {
    exec(
      cmd,
      {
        encoding: "utf-8",
        timeout: options?.timeout ?? 300_000,
        shell: options?.shell,
      },
      (error, stdout, stderr) => {
        if (error) {
          resolve({
            success: false,
            stdout: (stdout ?? "").trim(),
            stderr: (stderr ?? error.message ?? "").trim(),
          });
        } else {
          resolve({
            success: true,
            stdout: (stdout ?? "").trim(),
            stderr: (stderr ?? "").trim(),
          });
        }
      },
    );
  });
}

/**
 * 安全的异步命令执行（使用 execFile + 参数数组，不经过 shell 解释）
 * 用于执行参数来自外部输入（如 LLM）的命令，从根本上消除 shell 注入风险
 */
function runCommandAsyncSafe(
  file: string,
  args: string[],
  options?: { timeout?: number },
): Promise<{
  success: boolean;
  stdout: string;
  stderr: string;
}> {
  return new Promise((resolve) => {
    execFile(
      file,
      args,
      {
        encoding: "utf-8",
        timeout: options?.timeout ?? 300_000,
        // 不传 shell 参数，execFile 默认不使用 shell
      },
      (error, stdout, stderr) => {
        if (error) {
          resolve({
            success: false,
            stdout: (stdout ?? "").trim(),
            stderr: (stderr ?? error.message ?? "").trim(),
          });
        } else {
          resolve({
            success: true,
            stdout: (stdout ?? "").trim(),
            stderr: (stderr ?? "").trim(),
          });
        }
      },
    );
  });
}

// ============================================================================
// HTTP 下载工具
// ============================================================================

/**
 * 使用 Node.js 原生 https 模块下载文件，支持 302 重定向
 * 不依赖 curl，完全 Node.js 实现
 */
function downloadFile(url: string, destPath: string, maxRedirects = 5): Promise<void> {
  return new Promise((resolve, reject) => {
    const mod = url.startsWith("https") ? https : http;
    mod.get(url, { timeout: 60_000 }, (res) => {
      // 处理重定向
      if ((res.statusCode === 301 || res.statusCode === 302 || res.statusCode === 307) && res.headers.location) {
        if (maxRedirects <= 0) {
          reject(new Error("下载重定向次数过多"));
          return;
        }
        downloadFile(res.headers.location, destPath, maxRedirects - 1).then(resolve, reject);
        return;
      }
      if (res.statusCode !== 200) {
        reject(new Error(`下载失败: HTTP ${res.statusCode} - ${url}`));
        return;
      }
      const file = fs.createWriteStream(destPath);
      res.pipe(file);
      file.on("finish", () => {
        file.close();
        resolve();
      });
      file.on("error", (err) => {
        fs.unlink(destPath, () => {});
        reject(err);
      });
    }).on("error", (err) => {
      reject(new Error(`下载失败: ${err.message} - ${url}`));
    });
  });
}

/**
 * 多源下载：依次尝试多个 URL，任一成功即返回
 * 适用于国内/海外网络环境差异大的场景
 */
async function downloadFileWithFallback(urls: string[], destPath: string): Promise<void> {
  const errors: string[] = [];
  for (const url of urls) {
    try {
      console.log(`${LOG_TAG} 尝试下载: ${url}`);
      await downloadFile(url, destPath);
      const stat = fs.statSync(destPath);
      if (stat.size < 1_000_000) {
        // 文件太小，可能是错误页面，继续尝试下一个源
        console.log(`${LOG_TAG} 下载文件异常（仅 ${stat.size} 字节），尝试下一个源...`);
        try { fs.unlinkSync(destPath); } catch { /* ignore */ }
        errors.push(`${url}: 文件异常（${stat.size} 字节）`);
        continue;
      }
      console.log(`${LOG_TAG} 下载成功: ${url} (${(stat.size / 1024 / 1024).toFixed(1)}MB)`);
      return; // 成功
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      console.log(`${LOG_TAG} 下载失败: ${url} - ${msg}`);
      errors.push(`${url}: ${msg}`);
      try { fs.unlinkSync(destPath); } catch { /* ignore */ }
    }
  }
  throw new Error(`所有下载源均失败:\n${errors.join("\n")}`);
}

// ============================================================================
// Node.js 原生 tar.gz 解压（不依赖系统 tar 命令）
// ============================================================================

/**
 * 使用 Node.js 内置 zlib 模块解压 .tar.gz 文件
 * 完全不依赖系统 tar/PowerShell，适用于裸 Windows 环境
 *
 * tar 格式: 每个文件由 512 字节头 + 文件内容（按 512 字节对齐）组成
 * 头部关键字段:
 *   - 0-99: 文件名
 *   - 100-107: 文件模式
 *   - 124-135: 文件大小（八进制）
 *   - 156: 类型标志 ('0'/'': 普通文件, '5': 目录, 'L': GNU 长文件名)
 *   - 257-262: UStar 标志
 *   - 345-499: 路径前缀
 */
function extractTarGzNative(tarGzPath: string, destDir: string): Promise<void> {
  return new Promise((resolve, reject) => {
    const chunks: Buffer[] = [];

    const gunzip = zlib.createGunzip();
    const readStream = fs.createReadStream(tarGzPath);

    readStream.pipe(gunzip);

    gunzip.on("data", (chunk: Buffer) => {
      chunks.push(chunk);
    });

    gunzip.on("error", (err) => {
      reject(new Error(`gzip 解压失败: ${err.message}`));
    });

    gunzip.on("end", () => {
      try {
        const tarData = Buffer.concat(chunks);
        parseTar(tarData, destDir);
        resolve();
      } catch (err) {
        const msg = err instanceof Error ? err.message : String(err);
        reject(new Error(`tar 解析失败: ${msg}`));
      }
    });

    readStream.on("error", (err) => {
      reject(new Error(`读取文件失败: ${err.message}`));
    });
  });
}

/**
 * 解析 tar 数据并提取文件到目标目录
 */
function parseTar(tarData: Buffer, destDir: string): void {
  let offset = 0;
  let gnuLongName: string | null = null;

  while (offset + 512 <= tarData.length) {
    const header = tarData.subarray(offset, offset + 512);

    // 检查是否为全零块（tar 结束标志）
    if (header.every((b) => b === 0)) {
      break;
    }

    // 解析文件名
    let fileName: string;
    if (gnuLongName) {
      fileName = gnuLongName;
      gnuLongName = null;
    } else {
      // 前缀 (ustar 格式) + 名称
      const prefix = readTarString(header, 345, 155);
      const name = readTarString(header, 0, 100);
      fileName = prefix ? `${prefix}/${name}` : name;
    }

    // 解析文件大小（八进制）
    const sizeStr = readTarString(header, 124, 12);
    const fileSize = parseInt(sizeStr, 8) || 0;

    // 解析类型标志
    const typeFlag = String.fromCharCode(header[156]!);

    offset += 512; // 跳过头部

    // GNU 长文件名扩展（类型标志 'L'）
    if (typeFlag === "L") {
      gnuLongName = tarData.subarray(offset, offset + fileSize).toString("utf-8").replace(/\0+$/, "");
      offset += Math.ceil(fileSize / 512) * 512;
      continue;
    }

    // 安全检查：防止路径穿越
    const normalizedName = fileName.replace(/\\/g, "/");
    if (normalizedName.includes("..") || path.isAbsolute(normalizedName)) {
      console.log(`${LOG_TAG} [tar] 跳过不安全路径: ${fileName}`);
      offset += Math.ceil(fileSize / 512) * 512;
      continue;
    }

    const fullPath = path.join(destDir, normalizedName);

    if (typeFlag === "5" || fileName.endsWith("/")) {
      // 目录
      fs.mkdirSync(fullPath, { recursive: true });
    } else if (typeFlag === "0" || typeFlag === "" || typeFlag === "\0") {
      // 普通文件
      fs.mkdirSync(path.dirname(fullPath), { recursive: true });
      const fileData = tarData.subarray(offset, offset + fileSize);
      fs.writeFileSync(fullPath, fileData);
    }
    // 其他类型（链接等）静默跳过

    // 跳过文件数据（按 512 字节对齐）
    offset += Math.ceil(fileSize / 512) * 512;
  }
}

/**
 * 从 tar 头部读取以 null 结尾的字符串
 */
function readTarString(buffer: Buffer, offset: number, length: number): string {
  const slice = buffer.subarray(offset, offset + length);
  const nullIdx = slice.indexOf(0);
  const end = nullIdx >= 0 ? nullIdx : length;
  return slice.subarray(0, end).toString("utf-8").trim();
}

// ============================================================================
// Windows Python 直接下载安装（降级方案）
// ============================================================================

/** Python 安装包下载地址（多源，按优先级尝试） */
const PYTHON_INSTALLER_URLS = [
  // 华为开源镜像（国内速度快）
  "https://mirrors.huaweicloud.com/python/3.12.8/python-3.12.8-amd64.exe",
  // npmmirror / 淘宝镜像
  "https://registry.npmmirror.com/-/binary/python/3.12.8/python-3.12.8-amd64.exe",
  // 官方源（国内可能较慢或不通）
  "https://www.python.org/ftp/python/3.12.8/python-3.12.8-amd64.exe",
];

/**
 * 降级方案 1: 使用 PowerShell Invoke-WebRequest 下载 Python 安装包并静默安装
 * 不依赖 curl、winget、choco，只依赖 PowerShell（Windows 7+ 自带）
 */
async function installPython3ViaPowerShell(): Promise<{ success: boolean; message: string }> {
  const installerPath = path.join(os.tmpdir(), `python-installer-${Date.now()}.exe`);

  try {
    // 1. 用 PowerShell 下载安装包（多源尝试）
    let downloaded = false;
    const downloadErrors: string[] = [];
    for (const url of PYTHON_INSTALLER_URLS) {
      console.log(`${LOG_TAG} [Windows] 使用 PowerShell 下载 Python 安装包: ${url}`);
      const downloadCmd = [
        `powershell.exe -NoProfile -ExecutionPolicy Bypass -Command`,
        `"[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12;`,
        `Invoke-WebRequest -Uri '${url}' -OutFile '${installerPath}' -UseBasicParsing"`,
      ].join(" ");

      const downloadResult = await runCommandAsync(downloadCmd, { timeout: 300_000 });
      if (downloadResult.success && fs.existsSync(installerPath)) {
        const stat = fs.statSync(installerPath);
        if (stat.size >= 1_000_000) {
          console.log(`${LOG_TAG} [Windows] 下载成功 (${(stat.size / 1024 / 1024).toFixed(1)}MB)`);
          downloaded = true;
          break;
        }
        console.log(`${LOG_TAG} [Windows] 下载文件异常（仅 ${stat.size} 字节），尝试下一个源...`);
        try { fs.unlinkSync(installerPath); } catch { /* ignore */ }
      }
      downloadErrors.push(`${url}: ${downloadResult.stderr || "文件异常"}`);
    }

    if (!downloaded) {
      return { success: false, message: `PowerShell 下载 Python 安装包失败（所有源均失败）:\n${downloadErrors.join("\n")}` };
    }

    const stat = fs.statSync(installerPath);
    console.log(`${LOG_TAG} [Windows] 下载完成 (${(stat.size / 1024 / 1024).toFixed(1)}MB)，开始静默安装...`);

    // 2. 静默安装 Python
    // /passive = 显示进度条但不需要交互
    // InstallAllUsers=0 = 仅当前用户（不需要管理员权限）
    // PrependPath=1 = 将 Python 添加到 PATH
    // Include_pip=1 = 安装 pip
    const installCmd = `powershell.exe -NoProfile -Command "Start-Process '${installerPath}' -ArgumentList '/passive','InstallAllUsers=0','PrependPath=1','Include_pip=1' -Wait"`;

    const installResult = await runCommandAsync(installCmd, { timeout: 600_000 });
    if (!installResult.success) {
      // 某些环境下 Start-Process 可能报错但实际安装成功了，不直接返回失败
      console.log(`${LOG_TAG} [Windows] Start-Process 返回非零: ${installResult.stderr}，继续检查安装结果...`);
    }

    // 3. 安装完成后验证
    // 安装路径通常在 LocalAppData\Programs\Python\Python312
    const localAppData = process.env.LOCALAPPDATA ?? path.join(os.homedir(), "AppData", "Local");
    const expectedPath = path.join(localAppData, "Programs", "Python", "Python312", "python.exe");
    if (fs.existsSync(expectedPath)) {
      const verifyResult = runCommand(`"${expectedPath}" --version`, { shell: "cmd.exe" });
      if (verifyResult.success && verifyResult.stdout.toLowerCase().includes("python 3")) {
        console.log(`${LOG_TAG} [Windows] Python 安装验证成功: ${verifyResult.stdout}`);
        _cachedPython3Path = expectedPath;
        return { success: true, message: `Python 安装成功: ${expectedPath}` };
      }
    }

    // 尝试 PATH 中的 python
    const pathVerify = runCommand("python --version", { shell: "cmd.exe" });
    if (pathVerify.success && pathVerify.stdout.toLowerCase().includes("python 3")) {
      return { success: true, message: `Python 安装成功（PATH 中）: ${pathVerify.stdout}` };
    }

    return { success: false, message: "安装包已执行，但未能检测到 Python。可能需要重启应用使 PATH 生效。" };
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    return { success: false, message: `PowerShell 安装 Python 异常: ${msg}` };
  } finally {
    // 清理安装包
    try { fs.unlinkSync(installerPath); } catch { /* ignore */ }
  }
}

/**
 * 降级方案 2: 使用 Node.js 原生 https 模块下载 Python 安装包并通过 cmd 静默安装
 * 不依赖 curl、winget、choco，也不依赖 PowerShell 的 Invoke-WebRequest
 * 仅依赖 Node.js 内置模块
 */
async function installPython3ViaNodeDownload(): Promise<{ success: boolean; message: string }> {
  const installerPath = path.join(os.tmpdir(), `python-installer-${Date.now()}.exe`);

  try {
    // 1. 用 Node.js 原生 https 模块下载（多源尝试）
    console.log(`${LOG_TAG} [Windows] 使用 Node.js 原生多源下载 Python 安装包...`);
    await downloadFileWithFallback(PYTHON_INSTALLER_URLS, installerPath);

    // 验证文件
    if (!fs.existsSync(installerPath)) {
      return { success: false, message: "Node.js 下载完成但安装包文件不存在" };
    }
    const stat = fs.statSync(installerPath);
    console.log(`${LOG_TAG} [Windows] Node.js 下载完成 (${(stat.size / 1024 / 1024).toFixed(1)}MB)，开始静默安装...`);

    // 2. 使用 cmd 启动安装程序
    // /passive = 静默安装但显示进度
    // InstallAllUsers=0 = 当前用户安装，不需要管理员权限
    // PrependPath=1 = 添加到 PATH
    const installCmd = `"${installerPath}" /passive InstallAllUsers=0 PrependPath=1 Include_pip=1`;

    const installResult = await runCommandAsync(installCmd, { shell: "cmd.exe", timeout: 600_000 });
    if (!installResult.success) {
      console.log(`${LOG_TAG} [Windows] 安装程序返回非零: ${installResult.stderr}，继续检查安装结果...`);
    }

    // 3. 验证安装结果
    const localAppData = process.env.LOCALAPPDATA ?? path.join(os.homedir(), "AppData", "Local");
    const expectedPath = path.join(localAppData, "Programs", "Python", "Python312", "python.exe");
    if (fs.existsSync(expectedPath)) {
      const verifyResult = runCommand(`"${expectedPath}" --version`, { shell: "cmd.exe" });
      if (verifyResult.success && verifyResult.stdout.toLowerCase().includes("python 3")) {
        console.log(`${LOG_TAG} [Windows] Python 安装验证成功: ${verifyResult.stdout}`);
        _cachedPython3Path = expectedPath;
        return { success: true, message: `Python 安装成功: ${expectedPath}` };
      }
    }

    const pathVerify = runCommand("python --version", { shell: "cmd.exe" });
    if (pathVerify.success && pathVerify.stdout.toLowerCase().includes("python 3")) {
      return { success: true, message: `Python 安装成功（PATH 中）: ${pathVerify.stdout}` };
    }

    return { success: false, message: "安装包已执行，但未能检测到 Python。可能需要重启应用使 PATH 生效。" };
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    return { success: false, message: `Node.js 下载安装 Python 异常: ${msg}` };
  } finally {
    try { fs.unlinkSync(installerPath); } catch { /* ignore */ }
  }
}

// ============================================================================
// Windows Python 路径搜索
// ============================================================================

/** 缓存已找到的 Python3 完整路径，避免重复搜索 */
let _cachedPython3Path: string | undefined;

/**
 * 在 Windows 上搜索 Python3 的安装路径
 * 依次检查:
 *   1. PATH 中的 python3 / python / py -3
 *   2. 常见安装目录 (winget/官方安装器/Microsoft Store 等)
 *   3. Windows Registry (通过 py launcher)
 * 返回可直接执行的 Python3 完整路径，找不到返回 undefined
 */
function findPython3OnWindows(): { path: string; version: string } | undefined {
  // 如果有缓存，先验证缓存是否仍然有效
  if (_cachedPython3Path) {
    const r = runCommand(`"${_cachedPython3Path}" --version`, { shell: "cmd.exe" });
    if (r.success && r.stdout.toLowerCase().includes("python 3")) {
      return { path: _cachedPython3Path, version: r.stdout };
    }
    _cachedPython3Path = undefined; // 缓存失效
  }

  // 1. 先用 PATH 中的命令名尝试
  for (const cmd of ["python3", "python", "py -3"]) {
    const r = runCommand(`${cmd} --version`, { shell: "cmd.exe" });
    if (r.success && r.stdout.toLowerCase().includes("python 3")) {
      const execName = cmd.split(" ")[0]!;
      _cachedPython3Path = execName;
      return { path: execName, version: r.stdout };
    }
  }

  // 2. 搜索常见安装目录
  const homeDir = os.homedir();
  const localAppData = process.env.LOCALAPPDATA ?? path.join(homeDir, "AppData", "Local");
  const appData = process.env.APPDATA ?? path.join(homeDir, "AppData", "Roaming");
  const programFiles = process.env.ProgramFiles ?? "C:\\Program Files";
  const programFilesX86 = process.env["ProgramFiles(x86)"] ?? "C:\\Program Files (x86)";

  const candidateDirs: string[] = [];

  // winget / 官方安装器默认位置
  for (const base of [localAppData, programFiles, programFilesX86]) {
    // Python 3.9 ~ 3.14
    for (let minor = 9; minor <= 14; minor++) {
      candidateDirs.push(path.join(base, "Programs", "Python", `Python3${minor}`));
      candidateDirs.push(path.join(base, `Python3${minor}`));
    }
    candidateDirs.push(path.join(base, "Programs", "Python", "Python3"));
    candidateDirs.push(path.join(base, "Python3"));
  }

  // Microsoft Store 安装位置
  // 注意: WindowsApps 下的 python.exe 可能是占位符(App Execution Alias)，
  // 需要在后续执行 --version 时过滤掉
  try {
    const msStoreBase = path.join(localAppData, "Microsoft", "WindowsApps");
    if (fs.existsSync(msStoreBase)) {
      // 不直接加 WindowsApps，而是搜索其中的 PythonSoftwareFoundation 子目录
      const entries = fs.readdirSync(msStoreBase, { withFileTypes: true });
      for (const entry of entries) {
        if (entry.isDirectory() && entry.name.toLowerCase().includes("python")) {
          candidateDirs.push(path.join(msStoreBase, entry.name));
        }
      }
    }
  } catch { /* ignore */ }

  // py launcher 默认位置
  candidateDirs.push(path.join(programFiles, "Python Launcher"));

  // 用户级 pip/scripts 可能有 python
  candidateDirs.push(path.join(appData, "Python"));

  for (const dir of candidateDirs) {
    for (const exe of ["python3.exe", "python.exe"]) {
      const fullPath = path.join(dir, exe);
      try {
        if (fs.existsSync(fullPath)) {
          const r = runCommand(`"${fullPath}" --version`, { shell: "cmd.exe" });
          if (r.success && r.stdout.toLowerCase().includes("python 3")) {
            console.log(`${LOG_TAG} [Windows] 在 ${fullPath} 找到 Python3: ${r.stdout}`);
            _cachedPython3Path = fullPath;
            return { path: fullPath, version: r.stdout };
          }
        }
      } catch { /* ignore access errors */ }
    }
  }

  // 3. 最后尝试 where 命令（会搜索整个 PATH + App Paths）
  const whereResult = runCommand("where python.exe 2>nul", { shell: "cmd.exe" });
  if (whereResult.success && whereResult.stdout) {
    // where 可能返回多行，逐行检查
    for (const line of whereResult.stdout.split(/\r?\n/)) {
      const candidate = line.trim();
      if (!candidate || !fs.existsSync(candidate)) continue;
      // 排除 Microsoft Store 占位符 (WindowsApps 目录下的 python.exe 是假的)
      if (candidate.toLowerCase().includes("windowsapps")) continue;
      const r = runCommand(`"${candidate}" --version`, { shell: "cmd.exe" });
      if (r.success && r.stdout.toLowerCase().includes("python 3")) {
        console.log(`${LOG_TAG} [Windows] 通过 where 找到 Python3: ${candidate} (${r.stdout})`);
        _cachedPython3Path = candidate;
        return { path: candidate, version: r.stdout };
      }
    }
  }

  return undefined;
}

// ============================================================================
// 环境检测（内部使用，不留给 LLM 决策）
// ============================================================================

function checkFullEnv(platform: Platform): EnvCheckResult {
  const platformLabel = getPlatformLabel(platform);

  // 检查 python3
  const python3Check = (() => {
    if (platform === "windows") {
      const found = findPython3OnWindows();
      if (found) {
        return { available: true, version: found.version, path: found.path };
      }
      return { available: false };
    } else {
      const r = runCommand("python3 --version");
      if (r.success) {
        return { available: true, version: r.stdout, path: "python3" };
      }
      return { available: false };
    }
  })();

  // 检查 curl
  const curlCheck = (() => {
    if (platform === "windows") {
      // Windows 10+ 内置 curl.exe
      const r = runCommand("curl.exe --version", { shell: "cmd.exe" });
      return { available: r.success };
    } else {
      const r = runCommand("which curl");
      return { available: r.success };
    }
  })();

  // 检查 bash
  const bashCheck = (() => {
    if (platform === "windows") {
      // Windows 上检查 Git Bash 或 WSL
      const gitBash = runCommand('where bash.exe 2>nul || echo ""', { shell: "cmd.exe" });
      return { available: gitBash.success && gitBash.stdout.length > 0 && !gitBash.stdout.includes("Could not find") };
    } else {
      return { available: true }; // macOS/Linux 必定有 bash
    }
  })();

  // 检查 skillhub CLI（先检查 PATH，再降级到完整路径）
  const cliCheck = (() => {
    const shell = platform === "windows" ? "cmd.exe" : undefined;
    const r = runCommand("skillhub --version", { shell });
    if (r.success) {
      return { installed: true, version: r.stdout };
    }
    // 降级：PATH 中找不到时，尝试直接用完整路径检测
    const fullPath = platform === "windows"
      ? path.join(os.homedir(), ".local", "bin", "skillhub.cmd")
      : path.join(os.homedir(), ".local", "bin", "skillhub");
    if (fs.existsSync(fullPath)) {
      const r2 = runCommand(`"${fullPath}" --version`, { shell });
      if (r2.success) {
        // 顺便将 binDir 注入当前进程 PATH，后续调用不再需要降级
        const binDir = path.join(os.homedir(), ".local", "bin");
        if (!process.env.PATH?.includes(binDir)) {
          process.env.PATH = `${binDir}${path.delimiter}${process.env.PATH ?? ""}`;
          console.log(`${LOG_TAG} 已将 ${binDir} 注入当前进程 PATH（检测降级触发）`);
        }
        return { installed: true, version: r2.stdout };
      }
    }
    return { installed: false, version: undefined };
  })();

  return {
    platform: platformLabel,
    platformId: platform,
    python3: python3Check,
    curl: curlCheck,
    bash: bashCheck,
    skillhubCli: cliCheck,
  };
}

// ============================================================================
// 依赖自动安装（静默执行，不暴露给 LLM）
// ============================================================================

/**
 * 在各平台上尝试自动安装 Python3
 * 返回是否安装成功
 */
async function ensurePython3(platform: Platform): Promise<{ success: boolean; message: string }> {
  console.log(`${LOG_TAG} 正在检测 Python3 环境...`);

  // 先检查是否已有
  const env = checkFullEnv(platform);
  if (env.python3.available) {
    return { success: true, message: `Python3 已就绪: ${env.python3.version}` };
  }

  console.log(`${LOG_TAG} Python3 未找到，尝试自动安装...`);

  if (platform === "macos") {
    // macOS: 优先用 brew，其次 xcode-select
    const brewCheck = runCommand("which brew");
    if (brewCheck.success) {
      console.log(`${LOG_TAG} 使用 Homebrew 安装 Python3...`);
      const r = await runCommandAsync("brew install python3", { timeout: 600_000 });
      if (r.success) return { success: true, message: "通过 Homebrew 安装 Python3 成功" };
    }
    // 尝试 xcode-select 自带的 python3
    const xcodeResult = runCommand("xcode-select -p");
    if (xcodeResult.success) {
      const pyCheck = runCommand("/usr/bin/python3 --version");
      if (pyCheck.success) return { success: true, message: `系统 Python3 可用: ${pyCheck.stdout}` };
    }
    return { success: false, message: "macOS 上未找到 Python3，请先执行 `brew install python3` 或安装 Xcode Command Line Tools" };
  }

  if (platform === "linux") {
    // Linux: 尝试 apt / yum / dnf
    for (const [mgr, installCmd] of [
      ["apt-get", "sudo apt-get update && sudo apt-get install -y python3"],
      ["yum", "sudo yum install -y python3"],
      ["dnf", "sudo dnf install -y python3"],
    ] as const) {
      const mgrCheck = runCommand(`which ${mgr}`);
      if (mgrCheck.success) {
        console.log(`${LOG_TAG} 使用 ${mgr} 安装 Python3...`);
        const r = await runCommandAsync(installCmd, { timeout: 600_000 });
        if (r.success) return { success: true, message: `通过 ${mgr} 安装 Python3 成功` };
      }
    }
    return { success: false, message: "Linux 上未找到 Python3，请手动安装: sudo apt install python3" };
  }

  if (platform === "windows") {
    // Windows: 尝试 winget（Win 10 1709+ 自带）
    const wingetCheck = runCommand("winget --version", { shell: "cmd.exe" });
    if (wingetCheck.success) {
      console.log(`${LOG_TAG} 使用 winget 安装 Python3...`);
      const r = await runCommandAsync(
        "winget install -e --id Python.Python.3.12 --accept-source-agreements --accept-package-agreements",
        { shell: "cmd.exe", timeout: 600_000 },
      );
      if (r.success) {
        // winget 安装后当前进程 PATH 不会自动刷新，主动搜索安装路径
        console.log(`${LOG_TAG} [Windows] winget 安装完成，搜索 Python3 安装路径...`);
        // 清除缓存强制重新搜索
        _cachedPython3Path = undefined;
        const found = findPython3OnWindows();
        if (found) {
          console.log(`${LOG_TAG} [Windows] 找到 Python3: ${found.path} (${found.version})`);
          return { success: true, message: `通过 winget 安装 Python 3.12 成功，路径: ${found.path}` };
        }
        // 搜索不到但安装成功了，提示用户
        return { success: false, message: "winget 安装 Python 3.12 完成，但当前进程无法检测到。请重启应用后重试。" };
      }
      console.log(`${LOG_TAG} [Windows] winget 安装失败: ${r.stderr}`);
    } else {
      console.log(`${LOG_TAG} [Windows] winget 不可用: ${wingetCheck.stderr}`);
    }

    // 尝试 choco
    const chocoCheck = runCommand("choco --version", { shell: "cmd.exe" });
    if (chocoCheck.success) {
      console.log(`${LOG_TAG} 使用 Chocolatey 安装 Python3...`);
      const r = await runCommandAsync("choco install python3 -y", { shell: "cmd.exe", timeout: 600_000 });
      if (r.success) {
        // 同样主动搜索路径
        _cachedPython3Path = undefined;
        const found = findPython3OnWindows();
        if (found) {
          return { success: true, message: `通过 Chocolatey 安装 Python3 成功，路径: ${found.path}` };
        }
        return { success: false, message: "Chocolatey 安装 Python3 完成，但当前进程无法检测到。请重启应用后重试。" };
      }
      console.log(`${LOG_TAG} [Windows] choco 安装失败: ${r.stderr}`);
    } else {
      console.log(`${LOG_TAG} [Windows] choco 不可用`);
    }

    // 降级方案: 使用 PowerShell Invoke-WebRequest 直接下载 Python 安装包
    console.log(`${LOG_TAG} [Windows] 包管理器均不可用，尝试 PowerShell 直接下载 Python 安装包...`);
    const psInstallResult = await installPython3ViaPowerShell();
    if (psInstallResult.success) {
      _cachedPython3Path = undefined;
      const found = findPython3OnWindows();
      if (found) {
        console.log(`${LOG_TAG} [Windows] PowerShell 安装后找到 Python3: ${found.path} (${found.version})`);
        return { success: true, message: `通过 PowerShell 下载安装 Python 3.12 成功，路径: ${found.path}` };
      }
      return { success: true, message: "通过 PowerShell 下载安装 Python 3.12 完成，可能需要重启应用使 PATH 生效。" };
    }
    console.log(`${LOG_TAG} [Windows] PowerShell 安装失败: ${psInstallResult.message}`);

    // 最终降级: 使用 Node.js 原生 https 下载 Python 安装包
    console.log(`${LOG_TAG} [Windows] 尝试 Node.js 原生下载 Python 安装包...`);
    const nodeInstallResult = await installPython3ViaNodeDownload();
    if (nodeInstallResult.success) {
      _cachedPython3Path = undefined;
      const found = findPython3OnWindows();
      if (found) {
        console.log(`${LOG_TAG} [Windows] Node.js 下载安装后找到 Python3: ${found.path} (${found.version})`);
        return { success: true, message: `通过 Node.js 下载安装 Python 3.12 成功，路径: ${found.path}` };
      }
      return { success: true, message: "通过 Node.js 下载安装 Python 3.12 完成，可能需要重启应用使 PATH 生效。" };
    }
    console.log(`${LOG_TAG} [Windows] Node.js 下载安装失败: ${nodeInstallResult.message}`);

    // 最后再搜索一次——可能用户已经安装了但不在 PATH 中
    console.log(`${LOG_TAG} [Windows] 所有安装方式均失败，最后搜索已安装的 Python3...`);
    _cachedPython3Path = undefined;
    const lastChance = findPython3OnWindows();
    if (lastChance) {
      console.log(`${LOG_TAG} [Windows] 在系统中找到已安装的 Python3: ${lastChance.path}`);
      return { success: true, message: `找到已安装的 Python3: ${lastChance.path} (${lastChance.version})` };
    }

    return { success: false, message: "Windows 上未找到 Python3，所有自动安装方式均失败（winget/choco/PowerShell 下载/Node.js 下载），请访问 https://mirrors.huaweicloud.com/python/3.12.8/ 手动下载 python-3.12.8-amd64.exe 安装" };
  }

  return { success: false, message: "不支持的平台" };
}

/**
 * 确保 curl 可用（仅 macOS/Linux 需要，Windows 走 Node.js 原生下载）
 */
async function ensureCurl(platform: Platform): Promise<{ success: boolean; message: string }> {
  if (platform === "windows") {
    // Windows 不需要 curl，我们用 Node.js 原生 https 下载
    return { success: true, message: "Windows 使用 Node.js 原生下载，不需要 curl" };
  }

  const curlCheck = runCommand("which curl");
  if (curlCheck.success) {
    return { success: true, message: "curl 已就绪" };
  }

  console.log(`${LOG_TAG} curl 未找到，尝试自动安装...`);

  if (platform === "macos") {
    // macOS 通常自带 curl，如果没有用 brew
    const r = await runCommandAsync("brew install curl", { timeout: 300_000 });
    if (r.success) return { success: true, message: "通过 Homebrew 安装 curl 成功" };
    return { success: false, message: "macOS 上 curl 未找到，请执行 `brew install curl`" };
  }

  if (platform === "linux") {
    for (const [mgr, installCmd] of [
      ["apt-get", "sudo apt-get update && sudo apt-get install -y curl"],
      ["yum", "sudo yum install -y curl"],
      ["dnf", "sudo dnf install -y curl"],
    ] as const) {
      const mgrCheck = runCommand(`which ${mgr}`);
      if (mgrCheck.success) {
        const r = await runCommandAsync(installCmd, { timeout: 300_000 });
        if (r.success) return { success: true, message: `通过 ${mgr} 安装 curl 成功` };
      }
    }
    return { success: false, message: "Linux 上 curl 未找到，请手动安装" };
  }

  return { success: false, message: "不支持的平台" };
}

// ============================================================================
// Windows 专用：持久化 PATH 环境变量
// ============================================================================

/**
 * 将指定目录持久化写入 Windows 用户级 PATH 环境变量
 * 使用 PowerShell [Environment]::SetEnvironmentVariable 写入注册表
 * 这样即使应用重启、系统重启，PATH 也不会丢失
 */
function persistPathOnWindows(binDir: string): void {
  try {
    // 读取当前用户级 PATH（不是进程级的 process.env.PATH，而是注册表中持久化的值）
    const getUserPath = runCommand(
      `powershell.exe -NoProfile -Command "[Environment]::GetEnvironmentVariable('Path', 'User')"`,
      { shell: "cmd.exe" },
    );
    const currentUserPath = getUserPath.success ? (getUserPath.stdout || "").trim() : "";

    // 检查是否已存在（大小写不敏感比较，Windows 路径不区分大小写）
    const pathEntries = currentUserPath.split(";").map(p => p.trim().toLowerCase());
    if (pathEntries.includes(binDir.toLowerCase())) {
      console.log(`${LOG_TAG} [Windows] ${binDir} 已存在于用户 PATH 中，无需重复添加`);
      return;
    }

    // 拼接新 PATH 并写入（追加到末尾，不破坏已有路径）
    const newUserPath = currentUserPath
      ? `${currentUserPath};${binDir}`
      : binDir;

    const setResult = runCommand(
      `powershell.exe -NoProfile -Command "[Environment]::SetEnvironmentVariable('Path', '${newUserPath.replace(/'/g, "''")}', 'User')"`,
      { shell: "cmd.exe" },
    );

    if (setResult.success) {
      console.log(`${LOG_TAG} [Windows] 已将 ${binDir} 持久化写入用户级 PATH 环境变量`);
    } else {
      console.log(`${LOG_TAG} [Windows] 持久化 PATH 失败（非致命）: ${setResult.stderr}`);
    }
  } catch (err) {
    // 持久化 PATH 失败不应阻止安装成功
    const msg = err instanceof Error ? err.message : String(err);
    console.log(`${LOG_TAG} [Windows] 持久化 PATH 异常（非致命）: ${msg}`);
  }
}

/**
 * 将指定目录持久化写入 macOS/Linux shell profile
 * 如果 shell profile 中已有对应 export 行则跳过
 * 仅追加到用户当前 shell 对应的 profile 文件
 */
function persistPathOnUnix(binDir: string): void {
  try {
    // 确定要写入的 profile 文件
    const shell = process.env.SHELL || "";
    const home = os.homedir();
    const profiles: string[] = [];

    if (shell.includes("zsh")) {
      profiles.push(path.join(home, ".zshrc"));
    } else if (shell.includes("bash")) {
      // macOS 使用 .bash_profile, Linux 使用 .bashrc
      if (os.platform() === "darwin") {
        profiles.push(path.join(home, ".bash_profile"));
      } else {
        profiles.push(path.join(home, ".bashrc"));
      }
    } else {
      // 默认写 .profile（POSIX 通用）
      profiles.push(path.join(home, ".profile"));
    }

    // 转义 binDir 中可能破坏 shell 双引号语法的特殊字符（" \ $ `）
    const safeBinDir = binDir.replace(/["\\$`]/g, "\\$&");
    const exportLine = `export PATH="${safeBinDir}:$PATH"`;
    const marker = `# Added by SkillHub CLI installer`;

    for (const profilePath of profiles) {
      try {
        const content = fs.existsSync(profilePath) ? fs.readFileSync(profilePath, "utf-8") : "";
        // 检查是否已存在（精确匹配 binDir）
        if (content.includes(binDir)) {
          console.log(`${LOG_TAG} [Unix] ${binDir} 已存在于 ${profilePath}，无需重复添加`);
          continue;
        }
        // 追加到文件末尾
        const appendContent = `\n${marker}\n${exportLine}\n`;
        fs.appendFileSync(profilePath, appendContent, "utf-8");
        console.log(`${LOG_TAG} [Unix] 已将 ${binDir} 写入 ${profilePath}`);
      } catch (fileErr) {
        const msg = fileErr instanceof Error ? fileErr.message : String(fileErr);
        console.log(`${LOG_TAG} [Unix] 写入 ${profilePath} 失败（非致命）: ${msg}`);
      }
    }
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    console.log(`${LOG_TAG} [Unix] 持久化 PATH 异常（非致命）: ${msg}`);
  }
}

// ============================================================================
// Windows 专用：Node.js 原生安装流程（完全绕过 bash/curl 依赖）
// ============================================================================

/**
 * Windows 上通过 Node.js 原生实现完整的 CLI 安装
 * 不依赖 bash、curl，仅需 python3
 */
async function installCliOnWindows(withDefaultSkills: boolean): Promise<{
  success: boolean;
  message: string;
  output?: string;
}> {
  const homeDir = os.homedir();
  const installBase = path.join(homeDir, ".skillhub");
  const binDir = path.join(homeDir, ".local", "bin");
  const findSkillTargetDir = path.join(homeDir, ".openclaw", "workspace", "skills", "find-skills");
  const preferenceSkillTargetDir = path.join(homeDir, ".openclaw", "workspace", "skills", "skillhub-preference");

  const tmpDir = path.join(os.tmpdir(), `skillhub-install-${Date.now()}`);
  const tarPath = path.join(tmpDir, "latest.tar.gz");

  try {
    // 1. 创建目录
    fs.mkdirSync(tmpDir, { recursive: true });
    fs.mkdirSync(installBase, { recursive: true });
    fs.mkdirSync(binDir, { recursive: true });

    // 2. 下载安装包
    console.log(`${LOG_TAG} [Windows] 下载 CLI 安装包...`);
    await downloadFile(INSTALL_PACKAGE_URL, tarPath);
    console.log(`${LOG_TAG} [Windows] 下载完成: ${tarPath}`);

    // 3. 解压 tar.gz（Windows 10+ 内置 tar 命令）
    const extractDir = path.join(tmpDir, "extracted");
    fs.mkdirSync(extractDir, { recursive: true });
    const unzipResult = await runCommandAsync(
      `tar -xzf "${tarPath}" -C "${extractDir}"`,
      { shell: "cmd.exe", timeout: 120_000 },
    );
    if (!unzipResult.success) {
      // 降级 1: 尝试使用 PowerShell 调用 tar
      console.log(`${LOG_TAG} [Windows] cmd tar 解压失败 (${unzipResult.stderr})，尝试 PowerShell 降级解压...`);
      const psResult = await runCommandAsync(
        `powershell.exe -NoProfile -Command "tar -xzf '${tarPath}' -C '${extractDir}'"`,
        { timeout: 120_000 },
      );
      if (!psResult.success) {
        // 降级 2: Node.js 原生 zlib + tar 解析（完全不依赖系统命令）
        console.log(`${LOG_TAG} [Windows] PowerShell tar 也失败 (${psResult.stderr})，使用 Node.js 原生解压...`);
        try {
          await extractTarGzNative(tarPath, extractDir);
          console.log(`${LOG_TAG} [Windows] Node.js 原生解压成功`);
        } catch (nativeErr) {
          const msg = nativeErr instanceof Error ? nativeErr.message : String(nativeErr);
          return { success: false, message: `解压安装包失败（所有方式均失败）: cmd tar: ${unzipResult.stderr} | PowerShell tar: ${psResult.stderr} | Node.js: ${msg}` };
        }
      }
    }

    // 4. 定位解压后的文件（支持 cli/ 子目录结构）
    let cliSrcDir = extractDir;
    if (fs.existsSync(path.join(extractDir, "cli", "skills_store_cli.py"))) {
      cliSrcDir = path.join(extractDir, "cli");
    } else if (!fs.existsSync(path.join(extractDir, "skills_store_cli.py"))) {
      // 查找一层子目录
      const entries = fs.readdirSync(extractDir, { withFileTypes: true });
      for (const entry of entries) {
        if (entry.isDirectory()) {
          const candidate = path.join(extractDir, entry.name);
          if (fs.existsSync(path.join(candidate, "skills_store_cli.py"))) {
            cliSrcDir = candidate;
            break;
          }
        }
      }
    }

    if (!fs.existsSync(path.join(cliSrcDir, "skills_store_cli.py"))) {
      return { success: false, message: "安装包中未找到 skills_store_cli.py，安装包结构异常" };
    }

    // 5. 复制 CLI 文件
    const filesToCopy = [
      "skills_store_cli.py",
      "skills_upgrade.py",
      "version.json",
      "metadata.json",
    ];
    for (const file of filesToCopy) {
      const src = path.join(cliSrcDir, file);
      const dest = path.join(installBase, file);
      if (fs.existsSync(src)) {
        fs.copyFileSync(src, dest);
      }
    }
    // 可选文件
    const optionalFiles = ["skills_index.local.json"];
    for (const file of optionalFiles) {
      const src = path.join(cliSrcDir, file);
      const dest = path.join(installBase, file);
      if (fs.existsSync(src)) {
        fs.copyFileSync(src, dest);
      }
    }

    // 6. 生成配置文件（如果不存在）
    const configPath = path.join(installBase, "config.json");
    if (!fs.existsSync(configPath)) {
      fs.writeFileSync(configPath, JSON.stringify({
        self_update_url: "https://skillhub-1388575217.cos.ap-guangzhou.myqcloud.com/version.json",
      }, null, 2) + "\n", "utf-8");
    }

    // 7. 生成 wrapper 脚本
    // 获取已缓存的 Python 路径，用于写入 wrapper
    const pythonExe = _cachedPython3Path;

    // Windows batch wrapper
    const wrapperBat = path.join(binDir, "skillhub.cmd");
    // 如果有完整路径，优先使用；否则降级用命令名
    const batPythonLine = pythonExe && pythonExe.includes("\\")
      ? `"${pythonExe}" "%CLI%" %*`
      : `python3 "%CLI%" %* 2>nul || python "%CLI%" %* 2>nul || py -3 "%CLI%" %*`;
    fs.writeFileSync(wrapperBat, [
      `@echo off`,
      `set "CLI=%USERPROFILE%\\.skillhub\\skills_store_cli.py"`,
      `if not exist "%CLI%" (`,
      `  echo Error: CLI not found at %CLI% >&2`,
      `  exit /b 1`,
      `)`,
      batPythonLine,
    ].join("\r\n"), "utf-8");

    // Bash wrapper（如果有 Git Bash 等）
    const wrapperSh = path.join(binDir, "skillhub");
    fs.writeFileSync(wrapperSh, [
      `#!/usr/bin/env bash`,
      `set -euo pipefail`,
      `BASE="$HOME/.skillhub"`,
      `CLI="$BASE/skills_store_cli.py"`,
      `if [[ ! -f "$CLI" ]]; then`,
      `  echo "Error: CLI not found at $CLI" >&2`,
      `  exit 1`,
      `fi`,
      `exec python3 "$CLI" "$@"`,
    ].join("\n"), "utf-8");

    // 8. 安装 workspace skills（如果需要）
    if (withDefaultSkills) {
      const skillSrcDir = path.join(cliSrcDir, "skill");
      if (!fs.existsSync(skillSrcDir)) {
        // 尝试上级目录的 skill 子目录
        const parentSkillDir = path.join(path.dirname(cliSrcDir), "skill");
        if (fs.existsSync(parentSkillDir)) {
          installWorkspaceSkills(parentSkillDir, findSkillTargetDir, preferenceSkillTargetDir);
        }
      } else {
        installWorkspaceSkills(skillSrcDir, findSkillTargetDir, preferenceSkillTargetDir);
      }
    }

    // 9. 将 binDir 注入当前进程 PATH + 持久化到用户级 PATH 环境变量
    if (!process.env.PATH?.includes(binDir)) {
      process.env.PATH = `${binDir}${path.delimiter}${process.env.PATH ?? ""}`;
      console.log(`${LOG_TAG} [Windows] 已将 ${binDir} 注入当前进程 PATH`);
    }
    // 持久化: 将 binDir 写入 Windows 用户级 PATH 环境变量（重启后仍生效）
    persistPathOnWindows(binDir);
    const pathMsg = "";

    // 验证安装 —— 使用缓存的 Python 路径
    const cliScript = path.join(installBase, "skills_store_cli.py");
    let verifyResult = { success: false, stdout: "", stderr: "" };
    if (pythonExe) {
      verifyResult = runCommand(`"${pythonExe}" "${cliScript}" --version`, { shell: "cmd.exe" });
    }
    if (!verifyResult.success) {
      // 降级尝试多种命令名
      for (const pyCmd of ["python3", "python", "py -3"]) {
        verifyResult = runCommand(`${pyCmd} "${cliScript}" --version`, { shell: "cmd.exe" });
        if (verifyResult.success) break;
      }
    }

    return {
      success: true,
      message: `SkillHub CLI 安装成功 (Windows)。${pathMsg}`,
      output: verifyResult.success ? `版本: ${verifyResult.stdout}` : "已安装但版本验证待确认",
    };
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    return { success: false, message: `Windows CLI 安装失败: ${msg}` };
  } finally {
    // 清理临时文件
    try { fs.rmSync(tmpDir, { recursive: true, force: true }); } catch { /* ignore */ }
  }
}

/**
 * 安装 workspace skills（find-skills 和 skillhub-preference）
 */
function installWorkspaceSkills(
  skillSrcDir: string,
  findSkillTargetDir: string,
  preferenceSkillTargetDir: string,
): void {
  const findSkillSrc = path.join(skillSrcDir, "SKILL.md");
  if (fs.existsSync(findSkillSrc)) {
    fs.mkdirSync(findSkillTargetDir, { recursive: true });
    fs.copyFileSync(findSkillSrc, path.join(findSkillTargetDir, "SKILL.md"));
    console.log(`${LOG_TAG} 安装 workspace skill: find-skills`);
  }

  const prefSkillSrc = path.join(skillSrcDir, "SKILL.skillhub-preference.md");
  if (fs.existsSync(prefSkillSrc)) {
    fs.mkdirSync(preferenceSkillTargetDir, { recursive: true });
    fs.copyFileSync(prefSkillSrc, path.join(preferenceSkillTargetDir, "SKILL.md"));
    console.log(`${LOG_TAG} 安装 workspace skill: skillhub-preference`);
  }
}

// ============================================================================
// check_env — 检查当前环境（对外暴露给 LLM，但结论直接给出，不留决策空间）
// ============================================================================

function handleCheckEnv(): unknown {
  const platform = detectPlatform();
  const env = checkFullEnv(platform);

  // 根据环境状态直接给出结论性的 recommendation
  if (env.skillhubCli.installed) {
    return {
      ...env,
      status: "ready",
      recommendation: `SkillHub CLI 已就绪 (${env.skillhubCli.version})，可以直接使用 install_skill 安装技能。`,
      nextAction: "install_skill",
    };
  }

  // CLI 未安装时，直接建议调用 install_cli，不需要 LLM 思考依赖问题
  return {
    ...env,
    status: "cli_not_installed",
    recommendation: "SkillHub CLI 尚未安装，请调用 install_cli。install_cli 会自动检测并安装所有依赖环境（包括 Python3、curl 等），无需手动处理。",
    nextAction: "install_cli",
  };
}

// ============================================================================
// install_cli — 端到端安装 SkillHub CLI（自动处理所有依赖）
// ============================================================================

async function handleInstallCli(withDefaultSkills: boolean): Promise<unknown> {
  const platform = detectPlatform();
  const platformLabel = getPlatformLabel(platform);
  const steps: string[] = [];

  if (platform === "unsupported") {
    return {
      success: false,
      error: `不支持的操作系统: ${os.platform()}`,
      message: "SkillHub CLI 目前仅支持 macOS、Linux 和 Windows。",
    };
  }

  // ========== Step 0: 检查是否已安装 ==========
  const env = checkFullEnv(platform);
  if (env.skillhubCli.installed) {
    return {
      success: true,
      alreadyInstalled: true,
      platform: platformLabel,
      version: env.skillhubCli.version,
      message: `SkillHub CLI 已安装 (${env.skillhubCli.version})，无需重复安装。`,
    };
  }

  console.log(`${LOG_TAG} 开始在 ${platformLabel} 上安装 SkillHub CLI（端到端模式）...`);

  // ========== Step 1: 确保 Python3 可用 ==========
  const pythonResult = await ensurePython3(platform);
  steps.push(`[Python3] ${pythonResult.message}`);
  if (!pythonResult.success) {
    return {
      success: false,
      platform: platformLabel,
      steps,
      error: pythonResult.message,
      message: `安装失败: Python3 是必要依赖。${pythonResult.message}`,
    };
  }

  // ========== Step 2: Windows 走 Node.js 原生安装，macOS/Linux 走 curl|bash ==========
  if (platform === "windows") {
    // Windows: 使用 Node.js 原生 https 下载，完全不依赖 curl/bash
    console.log(`${LOG_TAG} [Windows] 使用 Node.js 原生安装流程...`);
    steps.push("[安装方式] Windows: Node.js 原生下载 + PowerShell 解压");

    const installResult = await installCliOnWindows(withDefaultSkills);
    steps.push(`[安装结果] ${installResult.message}`);

    if (installResult.success) {
      return {
        success: true,
        platform: platformLabel,
        steps,
        output: installResult.output,
        message: withDefaultSkills
          ? "SkillHub CLI 安装成功（含默认 Skills）。"
          : "SkillHub CLI 安装成功（不含默认 Skills）。可使用 install_skill 安装指定技能。",
      };
    } else {
      return {
        success: false,
        platform: platformLabel,
        steps,
        error: installResult.message,
        message: `SkillHub CLI 安装失败: ${installResult.message}`,
      };
    }
  }

  // ========== macOS / Linux: 确保 curl 可用 ==========
  const curlResult = await ensureCurl(platform);
  steps.push(`[curl] ${curlResult.message}`);
  if (!curlResult.success) {
    // 降级: 使用 Node.js 原生下载 install.sh
    console.log(`${LOG_TAG} curl 不可用，降级使用 Node.js 原生下载...`);
    steps.push("[降级] curl 不可用，使用 Node.js 原生下载 install.sh");

    const tmpDir = path.join(os.tmpdir(), `skillhub-install-${Date.now()}`);
    const scriptPath = path.join(tmpDir, "install.sh");
    try {
      fs.mkdirSync(tmpDir, { recursive: true });
      await downloadFile(INSTALL_SCRIPT_URL, scriptPath);
      fs.chmodSync(scriptPath, 0o755);

      const noSkillsFlag = withDefaultSkills ? "" : " --no-skills";
      const result = await runCommandAsync(`bash "${scriptPath}"${noSkillsFlag}`, {
        shell: "/bin/bash",
        timeout: 300_000,
      });

      if (result.success) {
        // 将 ~/.local/bin 注入当前进程 PATH，确保后续检测可用
        const binDir = path.join(os.homedir(), ".local", "bin");
        if (!process.env.PATH?.includes(binDir)) {
          process.env.PATH = `${binDir}${path.delimiter}${process.env.PATH ?? ""}`;
          console.log(`${LOG_TAG} 已将 ${binDir} 注入当前进程 PATH`);
        }
        // 持久化到 shell profile（install.sh 可能已做，这里兜底）
        persistPathOnUnix(binDir);
        const verifyResult = runCommand("skillhub --version");
        steps.push(`[安装] 成功: ${verifyResult.stdout || "版本待确认"}`);
        return {
          success: true,
          platform: platformLabel,
          steps,
          version: verifyResult.success ? verifyResult.stdout : "安装完成但版本检测失败",
          output: result.stdout || undefined,
          message: "SkillHub CLI 安装成功。",
        };
      } else {
        steps.push(`[安装] 失败: ${result.stderr}`);
        return {
          success: false,
          platform: platformLabel,
          steps,
          error: result.stderr,
          message: "SkillHub CLI 安装失败。",
        };
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      return { success: false, platform: platformLabel, steps, error: msg, message: `安装失败: ${msg}` };
    } finally {
      try { fs.rmSync(tmpDir, { recursive: true, force: true }); } catch { /* ignore */ }
    }
  }

  // ========== macOS / Linux: 正常 curl | bash 安装 ==========
  const noSkillsFlag = withDefaultSkills ? "" : " --no-skills";
  const installCmd = `curl -fsSL ${INSTALL_SCRIPT_URL} | bash -s --${noSkillsFlag}`;
  steps.push(`[安装命令] ${installCmd}`);

  const result = await runCommandAsync(installCmd, { shell: "/bin/bash", timeout: 300_000 });

  if (result.success) {
    // 将 ~/.local/bin 注入当前进程 PATH，确保后续检测可用
    const binDir = path.join(os.homedir(), ".local", "bin");
    if (!process.env.PATH?.includes(binDir)) {
      process.env.PATH = `${binDir}${path.delimiter}${process.env.PATH ?? ""}`;
      console.log(`${LOG_TAG} 已将 ${binDir} 注入当前进程 PATH`);
    }
    // 持久化到 shell profile（install.sh 可能已做，这里兜底）
    persistPathOnUnix(binDir);
    const verifyResult = runCommand("skillhub --version");
    steps.push(`[安装] 成功: ${verifyResult.stdout || "版本待确认"}`);
    return {
      success: true,
      platform: platformLabel,
      steps,
      version: verifyResult.success ? verifyResult.stdout : "安装完成但版本检测失败",
      output: result.stdout || undefined,
      message: withDefaultSkills
        ? "SkillHub CLI 安装成功（含默认 Skills）。"
        : "SkillHub CLI 安装成功（不含默认 Skills）。可使用 install_skill 安装指定技能。",
    };
  } else {
    steps.push(`[安装] 失败: ${result.stderr}`);
    return {
      success: false,
      platform: platformLabel,
      steps,
      error: result.stderr,
      output: result.stdout || undefined,
      message: "SkillHub CLI 安装失败。",
    };
  }
}

// ============================================================================
// install_skill — 安装指定 Skill（如果 CLI 未安装，自动先安装）
// ============================================================================

async function handleInstallSkill(skillName: string): Promise<unknown> {
  const platform = detectPlatform();
  const platformLabel = getPlatformLabel(platform);

  if (!skillName || typeof skillName !== "string" || !skillName.trim()) {
    return {
      success: false,
      error: "必须提供 skillName 参数",
      message: "请指定要安装的 Skill 名称，例如: openai-whisper",
    };
  }

  const name = skillName.trim();

  // 安全校验：Skill 名称只允许 Unicode 字母、数字、连字符、下划线、点
  // 阻止 shell 元字符（;, &&, ||, $(), `, |, >, <, & 等）注入
  const SKILL_NAME_PATTERN = /^[\p{L}\p{N}_\-\.]{1,128}$/u;
  if (!SKILL_NAME_PATTERN.test(name)) {
    return {
      success: false,
      error: "skillName 格式非法",
      message: "Skill 名称只能包含字母、数字、连字符、下划线和点，长度不超过 128 字符。例如: openai-whisper",
    };
  }

  // 自动检查 CLI，未安装则自动先安装
  const shell = platform === "windows" ? "cmd.exe" : undefined;
  let checkResult = runCommand("skillhub --version", { shell });

  if (!checkResult.success) {
    console.log(`${LOG_TAG} CLI 未安装，自动执行 install_cli...`);
    const installResult = await handleInstallCli(true);
    const ir = installResult as any;
    if (!ir.success) {
      return {
        success: false,
        error: "SkillHub CLI 未安装且自动安装失败",
        installCliResult: installResult,
        message: `需要先安装 SkillHub CLI，但自动安装失败: ${ir.error || ir.message}`,
      };
    }
    // 重新验证
    checkResult = runCommand("skillhub --version", { shell });
    if (!checkResult.success) {
      // 可能 PATH 未刷新，尝试直接用完整路径
      const fullPath = platform === "windows"
        ? path.join(os.homedir(), ".local", "bin", "skillhub.cmd")
        : path.join(os.homedir(), ".local", "bin", "skillhub");
      if (!fs.existsSync(fullPath)) {
        return {
          success: false,
          error: "CLI 安装完成但无法找到可执行文件",
          message: "SkillHub CLI 似乎安装成功但 PATH 中找不到，可能需要重启终端。",
        };
      }
    }
  }

  console.log(`${LOG_TAG} 开始安装 Skill: ${name} (${platformLabel})...`);

  // 安全执行：使用 execFile + 参数数组，不经过 shell 解释，从根本上消除命令注入
  // 确定 skillhub 可执行路径
  let skillhubPath = "skillhub";
  if (!checkResult.success) {
    const wrapperPath = platform === "windows"
      ? path.join(os.homedir(), ".local", "bin", "skillhub.cmd")
      : path.join(os.homedir(), ".local", "bin", "skillhub");
    if (fs.existsSync(wrapperPath)) {
      skillhubPath = wrapperPath;
    }
  }

  // Windows 上 .cmd 文件需要通过 cmd.exe 执行（Node.js execFile 对 .cmd 会自动设置 shell）
  // 为了在 Windows 上也完全规避注入，直接调用 Python 脚本
  let result: { success: boolean; stdout: string; stderr: string };
  if (platform === "windows" && skillhubPath.endsWith(".cmd")) {
    // Windows: 直接调用 Python 脚本，彻底绕过 .cmd 的 shell 陷阱
    const pythonExe = _cachedPython3Path ?? "python3";
    const cliScript = path.join(os.homedir(), ".skillhub", "skills_store_cli.py");
    if (fs.existsSync(cliScript)) {
      result = await runCommandAsyncSafe(pythonExe, [cliScript, "install", name], { timeout: 300_000 });
    } else {
      // CLI 脚本不存在，降级用 skillhub 命令（但通过参数数组传递）
      result = await runCommandAsyncSafe(skillhubPath, ["install", name], { timeout: 300_000 });
    }
  } else {
    result = await runCommandAsyncSafe(skillhubPath, ["install", name], { timeout: 300_000 });
  }

  if (result.success) {
    return {
      success: true,
      platform: platformLabel,
      skillName: name,
      output: result.stdout || undefined,
      message: `Skill "${name}" 安装成功。`,
    };
  } else {
    return {
      success: false,
      platform: platformLabel,
      skillName: name,
      error: result.stderr,
      output: result.stdout || undefined,
      message: `Skill "${name}" 安装失败。`,
      suggestion: "请检查 Skill 名称是否正确，或在终端中手动执行: skillhub install <skillName>",
    };
  }
}

// ============================================================================
// 工具定义 & 导出
// ============================================================================

/**
 * 创建 skillhub_install Agent Tool 定义
 */
export function createSkillHubInstallerTool() {
  return {
    name: "skillhub_install",
    label: "SkillHub 技能安装器",
    description: [
      "一键安装 SkillHub CLI 和 Skills（技能包）。",
      "当用户需要安装 skill、技能、插件时使用此工具。",
      "",
      "此工具**自动处理所有依赖环境**（Python3、curl 等），无需手动检查或安装依赖。",
      "",
      "支持三种操作：",
      "  - check_env: 快速检查当前环境状态",
      "  - install_cli: 端到端安装 SkillHub CLI（自动检测+安装全部依赖，一步到位）",
      "  - install_skill: 安装指定的 Skill（如果 CLI 未安装会自动先安装 CLI）",
      "",
      "**最简流程（推荐）：直接调用 install_skill，工具会自动处理一切。**",
      "",
      "示例：",
      "  安装 Skill:    skillhub_install install_skill openai-whisper  (会自动安装 CLI 如果需要)",
      "  检查环境:      skillhub_install check_env",
      "  安装 CLI:      skillhub_install install_cli",
    ].join("\n"),
    parameters: {
      type: "object" as const,
      properties: {
        action: {
          type: "string",
          enum: ["check_env", "install_cli", "install_skill"],
          description:
            "操作类型：check_env（检查环境）、install_cli（安装 CLI，自动处理所有依赖）、install_skill（安装 Skill，自动安装 CLI 如需要）",
        },
        skillName: {
          type: "string",
          pattern: "^[\\w\\-\\.]{1,128}$",
          description:
            "要安装的 Skill 名称（action=install_skill 时必填，只能包含字母、数字、连字符、下划线和点），例如: openai-whisper",
        },
        withDefaultSkills: {
          type: "boolean",
          description:
            "安装 CLI 时是否同时安装默认 Skills（默认 true）。设为 false 可加速安装，后续再按需安装。",
        },
      },
      required: ["action"],
    },
    async execute(_toolCallId: string, params: unknown) {
      const p = params as SkillHubInstallerParams;
      console.log(`${LOG_TAG} ✅ Tool 被 LLM 调用 | toolCallId=${_toolCallId} | action=${p.action} | skillName=${p.skillName ?? "N/A"} | withDefaultSkills=${p.withDefaultSkills ?? "default"}`);
      const startTime = Date.now();
      try {
        let result: unknown;
        switch (p.action) {
          case "check_env":
            result = handleCheckEnv();
            break;
          case "install_cli":
            result = await handleInstallCli(p.withDefaultSkills !== false);
            break;
          case "install_skill": {
            if (!p.skillName) {
              result = {
                error: "action 为 install_skill 时必须提供 skillName 参数",
              };
              break;
            }
            result = await handleInstallSkill(p.skillName);
            break;
          }
          default:
            result = {
              error: `未知操作类型: ${String(p.action)}，支持 check_env、install_cli 和 install_skill`,
            };
        }
        const elapsed = Date.now() - startTime;
        console.log(`${LOG_TAG} ✅ Tool 执行完成 | action=${p.action} | elapsed=${elapsed}ms | result=${JSON.stringify(result).slice(0, 500)}`);
        return textResult(result);
      } catch (err) {
        const message = err instanceof Error ? err.message : String(err);
        const elapsed = Date.now() - startTime;
        console.error(`${LOG_TAG} ❌ Tool 执行异常 | action=${p.action} | elapsed=${elapsed}ms | error=${message}`);
        return textResult({ error: message });
      }
    },
  };
}
