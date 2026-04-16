/**
 * archive.mjs - Zip archive 内存读取层
 * 
 * 启动时用纯 JS 解析 ZIP Central Directory，构建文件索引（路径 → {offset, size}）。
 * readFile() 通过 zipBuffer.subarray() 零拷贝返回文件内容，无需额外内存分配。
 * 内存开销从 3x（WASM 时代）降到 1x（仅保留一份 zipBuffer）。
 */

import fs from "node:fs";
import path from "node:path";
import { parseZipIndex } from "./zip-reader.mjs";

/** @type {Buffer|null} ZIP 文件完整内容 */
let zipBuffer = null;

/** @type {Map<string, { offset: number, size: number }>} 文件相对路径 → 偏移和大小 */
let fileIndex = new Map();

/** @type {Set<string>} 所有目录路径 */
let dirSet = new Set();

/** @type {string} archive 挂载的基础路径（即原始 node_modules 所在位置） */
let basePath = "";

/** @type {string} .node 文件所在的 unpacked 目录 */
let unpackedPath = "";

/** @type {boolean} 是否已初始化 */
let initialized = false;

/**
 * 初始化 archive
 * @param {string} zipPath - zip 文件路径
 * @param {string} mountPath - 挂载路径（原始 node_modules 目录路径）
 * @param {string} unpackedDir - unpacked 目录路径（.node 文件）
 */
export async function init(zipPath, mountPath, unpackedDir) {
  if (initialized) return;

  const startTime = Date.now();

  basePath = normalizeDriveLetter(path.resolve(mountPath).replace(/\\/g, "/"));
  unpackedPath = normalizeDriveLetter(path.resolve(unpackedDir).replace(/\\/g, "/"));

  // 读取 ZIP 文件。使用 Buffer.from() 创建拥有独立 ArrayBuffer 的副本，
  // 作为额外的安全措施防止底层 ArrayBuffer 被 V8 意外回收。
  zipBuffer = Buffer.from(fs.readFileSync(zipPath));
  fileIndex = parseZipIndex(zipBuffer);

  // 构建目录集合
  for (const name of fileIndex.keys()) {
    let dir = path.posix.dirname(name);
    while (dir && dir !== ".") {
      if (dirSet.has(dir)) break; // 已注册，父目录也已注册
      dirSet.add(dir);
      dir = path.posix.dirname(dir);
    }
  }

  initialized = true;

  const elapsed = Date.now() - startTime;
  console.error(
    `[memory-fs] Loaded ${fileIndex.size} files, ${dirSet.size} dirs from zip in ${elapsed}ms`
  );
}

/**
 * Windows 下统一盘符为小写（D:/... → d:/...）
 * 避免 path.resolve 输入盘符大小写不同导致 startsWith 匹配失败。
 * @param {string} p 已替换为正斜杠的路径
 */
function normalizeDriveLetter(p) {
  if (p.length >= 2 && p[1] === ":" && /[A-Z]/.test(p[0])) {
    return p[0].toLowerCase() + p.slice(1);
  }
  return p;
}

/**
 * 将绝对路径转为 zip 内的相对路径
 * @param {string} absPath 
 * @returns {string|null} zip 内的相对路径，根目录返回 ""，不在 archive 中返回 null
 */
export function toRelative(absPath) {
  const normalized = normalizeDriveLetter(absPath.replace(/\\/g, "/"));
  if (normalized === basePath) {
    return ""; // 根目录
  }
  if (!normalized.startsWith(basePath + "/")) {
    return null;
  }
  return normalized.slice(basePath.length + 1);
}

/**
 * 检查路径是否在 archive 中（文件或目录）
 */
export function exists(absPath) {
  const rel = toRelative(absPath);
  if (rel === null) return false;
  if (rel === "") return true; // 根目录
  return fileIndex.has(rel) || dirSet.has(rel);
}

/**
 * 检查是否是文件
 */
export function isFile(absPath) {
  const rel = toRelative(absPath);
  if (rel === null || rel === "") return false;
  return fileIndex.has(rel);
}

/**
 * 检查是否是目录
 */
export function isDirectory(absPath) {
  const rel = toRelative(absPath);
  if (rel === null) return false;
  if (rel === "") return true; // 根目录
  return dirSet.has(rel);
}

/**
 * 读取文件内容
 * @returns {Buffer|null}
 */
export function readFile(absPath) {
  const rel = toRelative(absPath);
  if (rel === null || rel === "") return null;
  const entry = fileIndex.get(rel);
  if (!entry) return null;
  return zipBuffer.subarray(entry.offset, entry.offset + entry.size);
}

/**
 * 读取文件内容为字符串
 * @returns {string|null}
 */
export function readFileUtf8(absPath) {
  const buf = readFile(absPath);
  return buf ? buf.toString("utf-8") : null;
}

/**
 * 列出目录下的直接子条目
 * @returns {string[]|null}
 */
export function readdir(absPath) {
  const rel = toRelative(absPath);
  if (rel === null) return null;
  if (rel !== "" && !dirSet.has(rel)) return null;

  const prefix = rel === "" ? "" : rel + "/";
  const children = new Set();

  // 从文件索引中收集
  for (const key of fileIndex.keys()) {
    if (prefix === "" || key.startsWith(prefix)) {
      const rest = prefix === "" ? key : key.slice(prefix.length);
      const firstSeg = rest.split("/")[0];
      if (firstSeg) children.add(firstSeg);
    }
  }

  // 从目录 Set 中收集
  for (const dir of dirSet) {
    if (prefix === "" || dir.startsWith(prefix)) {
      const rest = prefix === "" ? dir : dir.slice(prefix.length);
      const firstSeg = rest.split("/")[0];
      if (firstSeg) children.add(firstSeg);
    }
  }

  return [...children].sort();
}

/**
 * 构造一个 stat-like 对象
 */
export function stat(absPath) {
  const rel = toRelative(absPath);
  if (rel === null) return null;

  if (rel === "") {
    return makeStat(true, 0); // 根目录
  }

  if (fileIndex.has(rel)) {
    return makeStat(false, fileIndex.get(rel).size);
  }

  if (dirSet.has(rel)) {
    return makeStat(true, 0);
  }

  return null;
}

function makeStat(isDir, size) {
  const now = new Date();
  return {
    dev: 0,
    ino: 0,
    mode: isDir ? 16877 : 33188, // drwxr-xr-x : -rw-r--r--
    nlink: 1,
    uid: 0,
    gid: 0,
    rdev: 0,
    size,
    blksize: 4096,
    blocks: Math.ceil(size / 512),
    atimeMs: now.getTime(),
    mtimeMs: now.getTime(),
    ctimeMs: now.getTime(),
    birthtimeMs: now.getTime(),
    atime: now,
    mtime: now,
    ctime: now,
    birthtime: now,
    isFile: () => !isDir,
    isDirectory: () => isDir,
    isBlockDevice: () => false,
    isCharacterDevice: () => false,
    isSymbolicLink: () => false,
    isFIFO: () => false,
    isSocket: () => false,
  };
}

/**
 * 判断路径是否属于 archive 管辖范围（以 basePath 为前缀）
 * 
 * 与 isFile/isDirectory 不同：isInScope 仅判断路径前缀，不检查文件是否实际存在于 archive 中。
 * 用途：_findPath patch 需要区分"这个搜索路径是否应该由 archive 处理"，
 * 对于不在 archive 范围内的路径（如插件自身的 node_modules），应跳过 archive 查找，
 * 交由原始 _findPath 走磁盘解析，保持 Node.js 原生的搜索路径优先级。
 */
export function isInScope(absPath) {
  const normalized = normalizeDriveLetter(absPath.replace(/\\/g, "/"));
  return normalized === basePath || normalized.startsWith(basePath + "/");
}

/** 获取基础路径 */
export function getBasePath() {
  return basePath;
}

/** 获取 unpacked 路径 */
export function getUnpackedPath() {
  return unpackedPath;
}

/** 是否已初始化 */
export function isInitialized() {
  return initialized;
}
