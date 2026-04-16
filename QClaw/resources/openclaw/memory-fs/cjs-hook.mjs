/**
 * cjs-hook.mjs - Hook Node.js CJS 加载链路
 * 
 * Patch fs 同步方法，使 CJS require() 也能从 archive 加载。
 * 
 * 注意：Node.js ESM 内部（如 createCJSModuleWrap/getSourceSync）有时会传
 * file:// URL 而非文件路径给 readFileSync/openSync，所以需要统一转换。
 * 
 * 已 hook 的方法:
 *   readFileSync, statSync, lstatSync, readdirSync, realpathSync,
 *   existsSync, accessSync, openSync, fstatSync, closeSync
 */

import fs from "node:fs";
import Module from "node:module";
import path from "node:path";
import { fileURLToPath } from "node:url";
import * as archive from "./archive.mjs";

/**
 * 将输入统一转为文件路径：
 * - URL 对象（protocol === "file:"）→ fileURLToPath
 * - file:// 字符串 → fileURLToPath
 * - 其他 → 原样返回
 */
function toFilePath(input) {
  if (input instanceof URL) {
    if (input.protocol === "file:") {
      try { return fileURLToPath(input); } catch { return input; }
    }
    return input;
  }
  if (typeof input !== "string") return input;
  if (input.startsWith("file://")) {
    try { return fileURLToPath(input); } catch { return input; }
  }
  return input;
}

// ============= 虚拟 fd 管理 =============
let nextVirtualFd = 1_000_000;
/** @type {Map<number, { path: string }>} */
const virtualFdMap = new Map();

// ============= Patch fs.readFileSync =============
const originalReadFileSync = fs.readFileSync;

fs.readFileSync = function readFileSync(filePath, options) {
  const resolved = toFilePath(filePath);
  if (typeof resolved === "string") {
    const content = archive.readFile(resolved);
    if (content !== null) {
      if (typeof options === "string") return content.toString(options);
      if (options && options.encoding) return content.toString(options.encoding);
      return content;
    }
  }
  return originalReadFileSync.call(this, filePath, options);
};

// ============= Patch fs.statSync =============
const originalStatSync = fs.statSync;

fs.statSync = function statSync(filePath, options) {
  const resolved = toFilePath(filePath);
  if (typeof resolved === "string") {
    const s = archive.stat(resolved);
    if (s !== null) return s;
  }
  return originalStatSync.call(this, filePath, options);
};

// ============= Patch fs.lstatSync =============
const originalLstatSync = fs.lstatSync;

fs.lstatSync = function lstatSync(filePath, options) {
  const resolved = toFilePath(filePath);
  if (typeof resolved === "string") {
    const s = archive.stat(resolved);
    if (s !== null) return s;
  }
  return originalLstatSync.call(this, filePath, options);
};

// ============= Patch fs.readdirSync =============
const originalReaddirSync = fs.readdirSync;

fs.readdirSync = function readdirSync(dirPath, options) {
  const resolved = toFilePath(dirPath);
  if (typeof resolved === "string") {
    const entries = archive.readdir(resolved);
    if (entries !== null) {
      if (options?.withFileTypes) {
        return entries.map((name) => {
          const fullPath = resolved.replace(/\\/g, "/") + "/" + name;
          const isDir = archive.isDirectory(fullPath);
          return {
            name,
            isFile: () => !isDir,
            isDirectory: () => isDir,
            isBlockDevice: () => false,
            isCharacterDevice: () => false,
            isSymbolicLink: () => false,
            isFIFO: () => false,
            isSocket: () => false,
            parentPath: dirPath,
            path: dirPath,
          };
        });
      }
      return entries;
    }
  }
  return originalReaddirSync.call(this, dirPath, options);
};

// ============= Patch fs.realpathSync =============
const originalRealpathSync = fs.realpathSync;

fs.realpathSync = function realpathSync(filePath, options) {
  const resolved = toFilePath(filePath);
  if (typeof resolved === "string" && archive.exists(resolved)) {
    return resolved;
  }
  return originalRealpathSync.call(this, filePath, options);
};

if (originalRealpathSync.native) {
  const originalRealpathSyncNative = originalRealpathSync.native;
  fs.realpathSync.native = function realpathSyncNative(filePath, options) {
    const resolved = toFilePath(filePath);
    if (typeof resolved === "string" && archive.exists(resolved)) {
      return resolved;
    }
    return originalRealpathSyncNative.call(this, filePath, options);
  };
}

// ============= Patch fs.existsSync =============
const originalExistsSync = fs.existsSync;

fs.existsSync = function existsSync(filePath) {
  const resolved = toFilePath(filePath);
  if (typeof resolved === "string" && archive.exists(resolved)) {
    return true;
  }
  return originalExistsSync.call(this, filePath);
};

// ============= Patch fs.accessSync =============
const originalAccessSync = fs.accessSync;

fs.accessSync = function accessSync(filePath, mode) {
  const resolved = toFilePath(filePath);
  if (typeof resolved === "string" && archive.exists(resolved)) {
    return undefined;
  }
  return originalAccessSync.call(this, filePath, mode);
};

// ============= Patch fs.openSync =============
const originalOpenSync = fs.openSync;

fs.openSync = function openSync(filePath, flags, mode) {
  const resolved = toFilePath(filePath);
  if (typeof resolved === "string" && archive.isFile(resolved)) {
    const isReadOnly =
      flags === "r" ||
      flags === "r+" ||
      (typeof flags === "number" && (flags & (fs.constants.O_WRONLY | fs.constants.O_RDWR | fs.constants.O_CREAT | fs.constants.O_TRUNC)) === 0);
    if (isReadOnly) {
      const fd = nextVirtualFd++;
      virtualFdMap.set(fd, { path: resolved, position: 0 });
      return fd;
    }
  }
  return originalOpenSync.call(this, filePath, flags, mode);
};

// ============= Patch fs.fstatSync =============
const originalFstatSync = fs.fstatSync;

fs.fstatSync = function fstatSync(fd, options) {
  const entry = virtualFdMap.get(fd);
  if (entry) {
    return archive.stat(entry.path);
  }
  return originalFstatSync.call(this, fd, options);
};

// ============= Patch fs.closeSync =============
const originalCloseSync = fs.closeSync;

fs.closeSync = function closeSync(fd) {
  if (virtualFdMap.has(fd)) {
    virtualFdMap.delete(fd);
    return;
  }
  return originalCloseSync.call(this, fd);
};

// ============= Patch fs.readFileSync (fd overload) =============
const _readFileSyncPatched = fs.readFileSync;
fs.readFileSync = function readFileSync(filePathOrFd, options) {
  if (typeof filePathOrFd === "number") {
    const entry = virtualFdMap.get(filePathOrFd);
    if (entry) {
      const content = archive.readFile(entry.path);
      if (content !== null) {
        if (typeof options === "string") return content.toString(options);
        if (options && options.encoding) return content.toString(options.encoding);
        return content;
      }
    }
  }
  return _readFileSyncPatched.call(this, filePathOrFd, options);
};

// ============= Patch fs.readSync =============
// Node.js 内部 readFileSync → tryReadSync → fs.readSync 读取文件内容。
// 当虚拟 fd 通过 openSync patch 返回后，需要 readSync 也能从 archive 读取。
const originalReadSync = fs.readSync;

fs.readSync = function readSync(fd, buffer, offsetOrOptions, length, position) {
  const entry = virtualFdMap.get(fd);
  if (entry) {
    const content = archive.readFile(entry.path);
    if (content === null) return 0;

    let offset, pos;
    if (typeof offsetOrOptions === "object" && offsetOrOptions !== null) {
      offset = offsetOrOptions.offset ?? 0;
      length = offsetOrOptions.length ?? (buffer.byteLength - offset);
      pos = offsetOrOptions.position ?? null;
    } else {
      offset = offsetOrOptions ?? 0;
    }
    pos = pos !== undefined ? pos : (position ?? null);

    const readPos = pos !== null ? pos : entry.position;
    const bytesToRead = Math.min(length, content.length - readPos);
    if (bytesToRead <= 0) return 0;
    content.copy(buffer, offset, readPos, readPos + bytesToRead);
    entry.position = readPos + bytesToRead;
    return bytesToRead;
  }
  return originalReadSync.call(this, fd, buffer, offsetOrOptions, length, position);
};

// ============= Patch binding.fstat =============
// Node.js 内部 readFileSync → tryStatSync → binding.fstat（C++ 绑定）。
// binding.fstat 通过 binding 对象属性访问（非缓存引用），可以被 monkey-patch。
// process.binding('fs') 返回与 internalBinding('fs') 相同的对象。
const binding = process.binding("fs");
const S_IFREG = 0o100000;
const origBindingFstat = binding.fstat;

binding.fstat = function patchedBindingFstat(fd, bigint, req, shouldNotThrow) {
  const entry = virtualFdMap.get(fd);
  if (entry) {
    const content = archive.readFile(entry.path);
    const size = content ? content.length : 0;
    const sv = binding.statValues;
    const now = Date.now() / 1000;
    sv[0] = 0;                     // dev
    sv[1] = S_IFREG | 0o644;       // mode (regular file)
    sv[2] = 1;                     // nlink
    sv[3] = 0;                     // uid
    sv[4] = 0;                     // gid
    sv[5] = 0;                     // rdev
    sv[6] = 4096;                  // blksize
    sv[7] = 0;                     // ino
    sv[8] = size;                  // size
    sv[9] = Math.ceil(size / 512); // blocks
    sv[10] = now; sv[11] = now; sv[12] = now; sv[13] = now;
    return sv;
  }
  return origBindingFstat.call(this, fd, bigint, req, shouldNotThrow);
};

// ============= Patch Module._resolveFilename =============
// Node.js CJS 的 #imports (package imports) 解析走 C++ 层 packageImportsResolve，
// 它通过 C++ 读取 package.json，无法看到 archive 中的文件。
// 在 _resolveFilename 层拦截 #specifier，从 archive 中的 package.json 手动解析。
const original_resolveFilename = Module._resolveFilename;

Module._resolveFilename = function patchedResolveFilename(request, parent, isMain, options) {
  // 1. 处理 #imports (package imports)
  if (request.startsWith("#") && parent?.filename) {
    const resolved = resolvePackageImportsCjs(request, parent.filename);
    if (resolved) return resolved;
  }

  // 2. 处理绝对路径指向 archive 中的文件
  // 插件 .ts 文件等通过绝对路径 require() 加载，但磁盘上不存在，
  // 原始 _resolveFilename 的 C++ internalModuleStat 会检查磁盘失败。
  if (path.isAbsolute(request) && archive.isFile(request)) {
    return request;
  }

  // 3. 尝试原始解析
  try {
    return original_resolveFilename.call(this, request, parent, isMain, options);
  } catch (err) {
    // 4. 原始解析失败时，尝试从 archive 解析 bare specifier
    if (err.code === "MODULE_NOT_FOUND") {
      // 对于带子路径的 bare specifier，尝试 exports subpath
      if (!request.startsWith(".") && !request.startsWith("/") && !request.startsWith("#")) {
        // 获取 parent 的搜索路径
        const searchPaths = Module._resolveLookupPaths(request, parent);
        if (searchPaths) {
          for (const searchPath of searchPaths) {
            const result = tryResolveExportsSubpath(request, searchPath);
            if (result) return result;
          }
        }
      }
    }
    throw err;
  }
};

/**
 * 解析 CJS 中的 #imports specifier
 * 从 parent 文件向上查找最近的 package.json，读取 imports 字段
 */
function resolvePackageImportsCjs(specifier, parentPath) {
  const basePath = archive.getBasePath();
  const rel = archive.toRelative(parentPath);
  if (rel === null) return null;

  let dir = path.posix.dirname(rel);
  while (true) {
    const pkgJsonRel = (dir === "" ? "" : dir + "/") + "package.json";
    const pkgJsonAbs = basePath + "/" + pkgJsonRel;
    const content = archive.readFileUtf8(pkgJsonAbs);

    if (content) {
      const pkg = JSON.parse(content);
      if (pkg.imports) {
        const pkgDir = dir === "" ? basePath : basePath + "/" + dir;
        const resolved = resolvePackageImportsTarget(pkg.imports, specifier, pkgDir);
        if (resolved) return resolved;
      }
      break;
    }

    if (dir === "" || dir === ".") break;
    dir = path.posix.dirname(dir);
  }

  return null;
}

/**
 * 解析 imports 字段中的 target
 */
function resolvePackageImportsTarget(imports, specifier, pkgDir) {
  const target = imports[specifier];
  if (!target) return null;

  if (typeof target === "string") {
    const absPath = path.posix.normalize(pkgDir + "/" + target);
    if (archive.isFile(absPath)) return absPath;
    return null;
  }

  if (typeof target === "object" && target !== null) {
    // 条件映射：node > require > module-sync > import > default
    for (const cond of ["node", "require", "module-sync", "import", "default"]) {
      if (cond in target) {
        const val = target[cond];
        if (typeof val === "string") {
          const absPath = path.posix.normalize(pkgDir + "/" + val);
          if (archive.isFile(absPath)) return absPath;
        }
      }
    }
  }

  return null;
}

// ============= Patch Module._findPath =============
// Node.js CJS 解析器的 _findPath 使用 C++ 层的 internalModuleStat
// 直接检查磁盘文件，绕过了所有 JS 层的 fs hooks。
// 另外，原始 _findPath 会向上遍历 node_modules 目录树，可能找到项目根目录
// 中同名但版本不同的包（如 lru-cache@7 vs archive 中的 @11），导致兼容性错误。
// 因此，当搜索路径涉及 archive 区域时，必须优先从 archive 解析。
const original_findPath = Module._findPath;
const CJS_EXTENSIONS = [".js", ".json", ".node"];

Module._findPath = function patchedFindPath(request, paths, isMain) {
  if (!paths) return original_findPath.call(this, request, paths, isMain);

  // 按 Node.js 搜索路径的原始顺序逐个处理：
  // - 属于 archive 范围的路径 → 在 archive 中查找
  // - 不属于 archive 范围的路径 → 跳过，交给下方 original_findPath 处理
  //
  // 这保持了 Node.js 原生的搜索路径优先级：
  // 例如 wecom 插件的 node_modules（路径靠前但不在 archive 范围）不会被
  // archive 中同名包（路径靠后但在 archive 范围）抢先。
  for (const curPath of paths) {
    // 只对属于 archive 管辖范围的搜索路径查 archive
    if (!archive.isInScope(curPath)) continue;

    const basePath = path.resolve(curPath, request);
    // 精确匹配
    if (archive.isFile(basePath)) return basePath;
    // 尝试扩展名
    for (const ext of CJS_EXTENSIONS) {
      if (archive.isFile(basePath + ext)) return basePath + ext;
    }
    // 尝试作为目录
    if (archive.isDirectory(basePath)) {
      // 先检查 package.json 入口
      const pkgJsonPath = basePath.replace(/\\/g, "/") + "/package.json";
      const pkgContent = archive.readFileUtf8(pkgJsonPath);
      if (pkgContent) {
        const pkg = JSON.parse(pkgContent);
        // 按 Node.js CJS 规则解析：exports (require 条件) > main > index
        const entry = resolveCjsPackageEntry(pkg, basePath);
        if (entry && archive.isFile(entry)) return entry;
      }
      // 回退到 index 文件
      for (const ext of CJS_EXTENSIONS) {
        const indexPath = path.join(basePath, "index" + ext);
        if (archive.isFile(indexPath)) return indexPath;
      }
    }

    // 尝试 exports subpath 解析（如 strtok3/core → strtok3 包的 exports["./core"]）
    // 当 request 形如 pkgName/subpath 且直接拼接路径找不到文件时，
    // 需要读取 pkgName/package.json 的 exports 字段解析 subpath。
    const subpathResult = tryResolveExportsSubpath(request, curPath);
    if (subpathResult) return subpathResult;
  }

  // 非 archive 范围的路径 + archive 中未找到的，回退到原始 _findPath（磁盘查找）
  return original_findPath.call(this, request, paths, isMain);
};

/**
 * 从 package.json 解析 CJS 入口
 * 遵循 Node.js CJS 解析规则：exports.require > main > index.js
 */
function resolveCjsPackageEntry(pkg, pkgDir) {
  const normalized = pkgDir.replace(/\\/g, "/");

  // 检查 exports 字段（CJS require 条件）
  if (pkg.exports) {
    const entry = resolveCjsExports(pkg.exports, normalized);
    if (entry) return entry;
  }

  // 回退到 main
  if (pkg.main) {
    const mainPath = path.posix.normalize(normalized + "/" + pkg.main);
    if (archive.isFile(mainPath)) return mainPath;
    // main 可能没有扩展名
    for (const ext of CJS_EXTENSIONS) {
      if (archive.isFile(mainPath + ext)) return mainPath + ext;
    }
    // main 可能指向目录
    if (archive.isDirectory(mainPath)) {
      for (const ext of CJS_EXTENSIONS) {
        if (archive.isFile(mainPath + "/index" + ext)) return mainPath + "/index" + ext;
      }
    }
  }

  return null;
}

/**
 * 从 exports 字段解析 CJS 入口（"." subpath）
 * 条件优先级：require > node > module-sync > import > default
 */
function resolveCjsExports(exports, pkgDir) {
  if (typeof exports === "string") {
    return path.posix.normalize(pkgDir + "/" + exports);
  }
  if (typeof exports !== "object" || exports === null) return null;

  // 条件映射（"." 子路径或直接条件）
  const target = exports["."] || exports;

  if (typeof target === "string") {
    return path.posix.normalize(pkgDir + "/" + target);
  }
  if (typeof target === "object" && target !== null) {
    for (const cond of ["require", "node", "module-sync", "import", "default"]) {
      if (cond in target) {
        const val = target[cond];
        if (typeof val === "string") {
          return path.posix.normalize(pkgDir + "/" + val);
        }
        if (typeof val === "object" && val !== null) {
          // 嵌套条件映射，按 CJS require 优先级解析
          // 例如 axios exports["."].default = { require: "./dist/node/axios.cjs", default: "./index.js" }
          // 必须优先取 require 条件（CJS 入口），而非 default（可能是 ESM 入口）
          for (const innerCond of ["require", "node", "module-sync", "import", "default"]) {
            if (innerCond in val && typeof val[innerCond] === "string") {
              return path.posix.normalize(pkgDir + "/" + val[innerCond]);
            }
          }
        }
      }
    }
  }

  return null;
}

/**
 * 尝试通过 exports subpath 解析 require('pkg/subpath')
 * 
 * 当 request 形如 'strtok3/core' 时，拆分为 packageName='strtok3' + subpath='./core'，
 * 读取 strtok3/package.json 的 exports["./core"] 字段解析实际文件路径。
 * 支持 @scope/pkg/subpath 格式。
 */
function tryResolveExportsSubpath(request, searchPath) {
  // 只处理 bare specifier 形式（不是相对路径、绝对路径）
  if (request.startsWith(".") || request.startsWith("/") || request.startsWith("\\")) return null;

  // 拆分 packageName 和 subpath
  let packageName, subpath;
  if (request.startsWith("@")) {
    const parts = request.split("/");
    if (parts.length < 3) return null; // @scope/pkg 没有 subpath
    packageName = parts.slice(0, 2).join("/");
    subpath = "./" + parts.slice(2).join("/");
  } else {
    const slashIndex = request.indexOf("/");
    if (slashIndex < 0) return null; // 没有 subpath
    packageName = request.slice(0, slashIndex);
    subpath = "./" + request.slice(slashIndex + 1);
  }

  const pkgDir = path.resolve(searchPath, packageName);
  const pkgJsonPath = pkgDir.replace(/\\/g, "/") + "/package.json";
  const pkgContent = archive.readFileUtf8(pkgJsonPath);
  if (!pkgContent) return null;

  const pkg = JSON.parse(pkgContent);
  if (!pkg.exports) return null;

  const resolved = resolveCjsExportsSubpath(pkg.exports, subpath, pkgDir.replace(/\\/g, "/"));
  if (resolved && archive.isFile(resolved)) return resolved;

  return null;
}

/**
 * 从 exports 字段解析特定 subpath（如 "./core"）
 * 按 CJS require 条件优先级解析：require > node > default
 */
function resolveCjsExportsSubpath(exports, subpath, pkgDir) {
  if (typeof exports !== "object" || exports === null) return null;

  const target = exports[subpath];
  if (!target) {
    // 通配符匹配
    for (const [pattern, value] of Object.entries(exports)) {
      if (pattern.includes("*")) {
        const regex = new RegExp("^" + pattern.replace(/[.*+?^${}()|[\]\\]/g, (m) => m === "*" ? "(.+)" : "\\" + m) + "$");
        const match = subpath.match(regex);
        if (match) {
          return resolveExportsTarget(value, pkgDir, match[1]);
        }
      }
    }
    return null;
  }

  return resolveExportsTarget(target, pkgDir);
}

/**
 * 解析 exports target（字符串、条件对象）
 * CJS 优先级：require > node > module-sync > import > default
 * 
 * Node.js 22+ 支持 require(esm)，CJS 可以加载仅提供 "import" 条件的 ESM 包。
 * "module-sync" 是 Node.js 22+ 专门为 require(esm) 引入的条件。
 */
function resolveExportsTarget(target, pkgDir, wildcardValue) {
  if (typeof target === "string") {
    const resolved = wildcardValue !== undefined ? target.replace(/\*/g, wildcardValue) : target;
    return path.posix.normalize(pkgDir + "/" + resolved);
  }
  if (typeof target === "object" && target !== null) {
    for (const cond of ["require", "node", "module-sync", "import", "default"]) {
      if (cond in target) {
        const result = resolveExportsTarget(target[cond], pkgDir, wildcardValue);
        if (result) return result;
      }
    }
  }
  return null;
}

console.error("[memory-fs] CJS fs hooks installed");
