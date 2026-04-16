/**
 * loader.mjs - ESM Customization Hooks
 * 
 * 策略：保持标准 file:// URL，在 load() 中检查路径是否落在 archive 中。
 * 如果是，从内存读取文件内容并返回 source，触发 shortCircuit 跳过磁盘 IO。
 * 
 * 不使用自定义 URL scheme（Node.js 不允许非 file:/data:/node: scheme）。
 *
 * ⚠️ Node.js ESM Loader 线程中的 ArrayBuffer 陷阱（两个独立问题）：
 *
 * 1. initialize() 返回后 detach:
 *    Node.js 在 initialize() 返回后会 detach 期间创建的所有 ArrayBuffer。
 *    因此 archive.init() 不能在 initialize() 中调用，必须延迟到第一次
 *    resolve()/load() hook 调用时执行（ensureLazyInit）。
 *
 * 2. load() 返回 source 时的 structured clone transfer:
 *    Node.js 内部通过 structured clone 将 load() 的返回值传回主线程。
 *    如果 source 是 zipBuffer.subarray()（与 zipBuffer 共享同一个 ArrayBuffer），
 *    整个 184MB 的 ArrayBuffer 会被 transfer/detach，导致后续所有
 *    readFile() 调用抛出 "Cannot perform Construct on a detached ArrayBuffer"。
 *    因此 load() 返回的 source 必须是独立的 Buffer 副本（Buffer.from()）。
 */

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import * as archive from "./archive.mjs";

/** @type {string} node_modules 的 file:// URL 前缀 */
let baseFileUrl = "";

/** @type {{ zipPath: string, mountPath: string, unpackedPath: string }|null} */
let pendingInitData = null;

/** @type {boolean} */
let lazyInitDone = false;

/**
 * initialize() - 由 module.register() 调用（运行在 loader 线程）
 *
 * 仅保存初始化参数，不在此处加载 ZIP 文件。
 * 实际加载在第一次 resolve()/load() 调用时通过 ensureLazyInit() 执行。
 */
export async function initialize(data) {
  pendingInitData = data;

  // fs patch 不涉及 ArrayBuffer，可以在 initialize 中安全执行
  patchFsForLoaderThread();
}

/**
 * 延迟初始化：在第一次 hook 调用时加载 ZIP 并构建索引。
 * 此时创建的 ArrayBuffer 不会被 V8 detach。
 */
async function ensureLazyInit() {
  if (lazyInitDone) return;
  lazyInitDone = true;

  if (!pendingInitData) {
    throw new Error("[memory-fs] loader: no init data (initialize() was never called)");
  }

  const { zipPath, mountPath, unpackedPath } = pendingInitData;
  await archive.init(zipPath, mountPath, unpackedPath);
  baseFileUrl = pathToFileURL(mountPath).href;
  if (!baseFileUrl.endsWith("/")) baseFileUrl += "/";
  pendingInitData = null;
}

/**
 * Patch loader 线程的 fs 方法。
 * 只 patch getSourceSync 链路需要的方法（readFileSync / openSync / fstatSync / closeSync）
 */
function patchFsForLoaderThread() {
  const originalReadFileSync = fs.readFileSync;
  const originalOpenSync = fs.openSync;
  const originalFstatSync = fs.fstatSync;
  const originalCloseSync = fs.closeSync;
  const originalReadSync = fs.readSync;

  let nextVirtualFd = 2_000_000; // 与主线程的 1_000_000 基数分开
  const virtualFdMap = new Map();

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

  fs.readFileSync = function readFileSync(filePath, options) {
    const resolved = toFilePath(filePath);
    if (typeof resolved === "string" && archive.isInitialized()) {
      const content = archive.readFile(resolved);
      if (content !== null) {
        if (typeof options === "string") return content.toString(options);
        if (options && options.encoding) return content.toString(options.encoding);
        return content;
      }
    }
    // fd overload
    if (typeof filePath === "number") {
      const entry = virtualFdMap.get(filePath);
      if (entry) {
        const content = archive.readFile(entry.path);
        if (content !== null) {
          if (typeof options === "string") return content.toString(options);
          if (options && options.encoding) return content.toString(options.encoding);
          return content;
        }
      }
    }
    return originalReadFileSync.call(this, filePath, options);
  };

  fs.openSync = function openSync(filePath, flags, mode) {
    const resolved = toFilePath(filePath);
    if (typeof resolved === "string" && archive.isFile(resolved)) {
      const isReadOnly = flags === "r" || flags === "r+" ||
        (typeof flags === "number" && (flags & (fs.constants.O_WRONLY | fs.constants.O_RDWR | fs.constants.O_CREAT | fs.constants.O_TRUNC)) === 0);
      if (isReadOnly) {
        const fd = nextVirtualFd++;
        virtualFdMap.set(fd, { path: resolved, position: 0 });
        return fd;
      }
    }
    return originalOpenSync.call(this, filePath, flags, mode);
  };

  fs.fstatSync = function fstatSync(fd, options) {
    const entry = virtualFdMap.get(fd);
    if (entry) return archive.stat(entry.path);
    return originalFstatSync.call(this, fd, options);
  };

  fs.closeSync = function closeSync(fd) {
    if (virtualFdMap.has(fd)) { virtualFdMap.delete(fd); return; }
    return originalCloseSync.call(this, fd);
  };

  // Patch fs.readSync：处理虚拟 fd 的读取
  // readFileSync 内部通过 tryReadSync → fs.readSync → binding.read 读取文件。
  // 由于 tryReadSync 通过 fs.readSync 访问（非缓存引用），此 patch 生效。
  fs.readSync = function readSync(fd, buffer, offsetOrOptions, length, position) {
    const entry = virtualFdMap.get(fd);
    if (entry) {
      const content = archive.readFile(entry.path);
      if (content === null) return 0;

      // 解析参数（readSync 支持两种签名）
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

  // Patch binding.fstat：处理虚拟 fd 的 fstat
  //
  // Node.js 内部 readFileSync → tryStatSync → binding.fstat（直接 C++ 绑定调用）。
  // 当 getSourceSync 使用缓存的原始 readFileSync 引用时，其内部的 openSync 会走
  // 我们的 JS patch 返回虚拟 fd，但 tryStatSync 调用 binding.fstat 是 C++ 级别，
  // 虚拟 fd 对内核无效 → EBADF。
  //
  // 通过 process.binding('fs') 获取与 internalBinding('fs') 相同的对象，
  // 在其 fstat 属性上安装拦截器，对虚拟 fd 填充 archive 中的 stat 数据。
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
      sv[10] = now; sv[11] = now; sv[12] = now; sv[13] = now; // atime/mtime/ctime/birthtime
      // atimeNs/mtimeNs/ctimeNs/birthtimeNs (indices 14-17)
      const nowNs = BigInt(Math.floor(now * 1e9));
      sv[14] = Number(nowNs); sv[15] = Number(nowNs); sv[16] = Number(nowNs); sv[17] = Number(nowNs);
      return sv;
    }
    return origBindingFstat.call(this, fd, bigint, req, shouldNotThrow);
  };
}

/**
 * resolve() - 模块路径解析钩子
 * 
 * 对于 bare specifier（如 'express'），如果默认 resolver 因磁盘无文件而失败，
 * 我们从 archive 中查找并返回 file:// URL（虽然磁盘上没有，但 load 会拦截）。
 * 
 * 对于相对路径 import，默认 resolver 可能也会失败（因为磁盘无文件），同样处理。
 */
export async function resolve(specifier, context, nextResolve) {
  await ensureLazyInit();

  // 先尝试从 archive 中解析
  const archiveResult = tryResolveFromArchive(specifier, context.parentURL);

  // 如果请求来自 archive 内的模块且 archive 能 resolve，优先使用 archive 结果。
  // 这避免了磁盘上同名但版本不同的包（如项目根目录的 chalk@4 vs archive 中的 chalk@5）
  // 被默认 resolver 错误命中的问题。
  if (archiveResult && context.parentURL) {
    try {
      const parentPath = fileURLToPath(context.parentURL);
      if (archive.isFile(parentPath)) {
        return archiveResult;
      }
    } catch {
      // parentURL 不是 file:// 协议，忽略
    }
  }

  // 再让默认 resolver 解析
  try {
    const resolved = await nextResolve(specifier, context);

    // 如果默认 resolver 成功了，检查它解析的路径是否在 archive 中
    if (resolved.url.startsWith("file://")) {
      const filePath = fileURLToPath(resolved.url);
      if (archive.isFile(filePath)) {
        return {
          url: resolved.url,
          format: resolved.format || guessFormat(filePath),
          shortCircuit: true,
        };
      }
    }

    return resolved;
  } catch (err) {
    // 默认 resolver 失败，尝试用 archive 结果
    if (
      (err.code === "ERR_MODULE_NOT_FOUND" ||
        err.code === "ERR_PACKAGE_IMPORT_NOT_DEFINED") &&
      archiveResult
    ) {
      return archiveResult;
    }
    throw err;
  }
}

/**
 * load() - 模块内容加载钩子
 * 
 * 当 URL 指向 archive 中的文件时，从内存读取并返回 source，触发 shortCircuit 跳过磁盘 IO。
 * 
 * CJS 模块不在此提供 source：异步 load hook 为 CJS 提供 source 会导致 Node.js
 * 将其注册为 ESM-managed 模块，后续 require() 同一模块时因 module status 冲突
 * 触发 ERR_INTERNAL_ASSERTION。CJS 模块的加载由 binding.fstat + fs.readSync
 * patch（patchFsForLoaderThread）处理，确保 Node.js 内部 readFileSync 能正确
 * 读取虚拟 fd 指向的 archive 文件。
 */
export async function load(url, context, nextLoad) {
  await ensureLazyInit();

  if (!url.startsWith("file://")) {
    return nextLoad(url, context);
  }

  let filePath;
  try {
    filePath = fileURLToPath(url);
  } catch {
    return nextLoad(url, context);
  }

  if (!archive.isFile(filePath)) {
    return nextLoad(url, context);
  }

  const format = context.format || guessFormat(filePath);

  // CJS 模块不提供 source，让 Node.js 内部的 readFileSync 读取。
  // patchFsForLoaderThread 中的 binding.fstat + fs.readSync patch 确保虚拟 fd 正常工作。
  if (format === "commonjs") {
    return nextLoad(url, { ...context, format });
  }

  const source = archive.readFile(filePath);
  if (source === null) {
    return nextLoad(url, context);
  }

  // ⚠️ 关键：必须返回独立的 Buffer 副本，不能返回 subarray。
  // archive.readFile() 返回 zipBuffer.subarray()，与 zipBuffer 共享同一个 ArrayBuffer。
  // Node.js 内部会通过 structured clone 将 load() 返回值传回主线程，
  // 这会导致 subarray 关联的整个 zipBuffer ArrayBuffer 被 transfer/detach，
  // 使后续所有 readFile() 调用失败（Cannot perform Construct on a detached ArrayBuffer）。
  return {
    format,
    source: Buffer.from(source),
    shortCircuit: true,
  };
}

// ============= 辅助函数 =============

/**
 * 尝试从 archive 中解析模块
 */
function tryResolveFromArchive(specifier, parentURL) {
  let absPath;

  if (specifier.startsWith(".") || specifier.startsWith("/")) {
    // 相对路径：基于 parentURL 解析
    if (!parentURL) return null;
    let parentPath;
    try {
      parentPath = fileURLToPath(parentURL);
    } catch {
      return null;
    }
    absPath = path.resolve(path.dirname(parentPath), specifier);
  } else if (specifier.startsWith("file://")) {
    try {
      absPath = fileURLToPath(specifier);
    } catch {
      return null;
    }
  } else if (specifier.startsWith("#")) {
    // package imports (#specifier)
    return tryResolvePackageImport(specifier, parentURL);
  } else if (specifier.startsWith("node:") || specifier.startsWith("data:")) {
    return null; // 内建模块不处理
  } else {
    // bare specifier (如 'express')
    // 需要在 node_modules 中查找
    return tryResolveBareSpecifier(specifier, parentURL);
  }

  return tryResolveAbsPath(absPath);
}

/**
 * 解析 package imports (#specifier)
 * 
 * 从 parentURL 向上查找最近的 package.json，读取 imports 字段，
 * 按 Node.js subpath imports 算法解析 #specifier。
 */
function tryResolvePackageImport(specifier, parentURL) {
  if (!parentURL) return null;

  let parentPath;
  try {
    parentPath = fileURLToPath(parentURL);
  } catch {
    return null;
  }

  const basePath = archive.getBasePath();
  const rel = archive.toRelative(parentPath);
  if (rel === null) return null;

  // 向上查找最近的 package.json
  let dir = path.posix.dirname(rel);
  while (true) {
    const pkgJsonRel = (dir === "" ? "" : dir + "/") + "package.json";
    const pkgJsonAbs = basePath + "/" + pkgJsonRel;
    const content = archive.readFileUtf8(pkgJsonAbs);

    if (content) {
      const pkg = JSON.parse(content);
      if (pkg.imports) {
        const pkgDir = dir === "" ? basePath : basePath + "/" + dir;
        const resolved = resolveImports(pkg.imports, specifier, pkgDir);
        if (resolved) return resolved;
      }
      // 找到 package.json 但没有 imports 字段或未匹配，停止查找
      break;
    }

    if (dir === "" || dir === ".") break;
    dir = path.posix.dirname(dir);
  }

  return null;
}

/**
 * 解析 package.json imports 字段
 */
function resolveImports(imports, specifier, pkgDir) {
  // 精确匹配
  const target = imports[specifier];
  if (target) {
    return resolveImportTarget(target, pkgDir);
  }

  // 通配符匹配
  for (const [pattern, value] of Object.entries(imports)) {
    if (pattern.includes("*")) {
      const regex = new RegExp(
        "^" + pattern.replace(/\*/g, "(.+)") + "$"
      );
      const match = specifier.match(regex);
      if (match) {
        return resolveImportTarget(value, pkgDir, match[1]);
      }
    }
  }

  return null;
}

/**
 * 解析 import target（可能是字符串、条件对象或数组）
 */
function resolveImportTarget(target, pkgDir, wildcardValue) {
  if (typeof target === "string") {
    const resolved = wildcardValue
      ? target.replace(/\*/g, wildcardValue)
      : target;
    const absPath = path.posix.normalize(pkgDir + "/" + resolved);
    return tryResolveAbsPath(absPath);
  }

  if (Array.isArray(target)) {
    for (const item of target) {
      const result = resolveImportTarget(item, pkgDir, wildcardValue);
      if (result) return result;
    }
    return null;
  }

  if (typeof target === "object" && target !== null) {
    // 条件映射：node-addons > node > import > default
    const conditions = ["node-addons", "node", "import", "default"];
    for (const cond of conditions) {
      if (cond in target) {
        const result = resolveImportTarget(target[cond], pkgDir, wildcardValue);
        if (result) return result;
      }
    }
  }

  return null;
}

/**
 * 解析 bare specifier
 */
function tryResolveBareSpecifier(specifier, parentURL) {
  const basePath = archive.getBasePath();

  // 解析 scope package (如 @scope/pkg/sub)
  let packageName, subpath;
  if (specifier.startsWith("@")) {
    const parts = specifier.split("/");
    packageName = parts.slice(0, 2).join("/");
    subpath = parts.length > 2 ? "./" + parts.slice(2).join("/") : ".";
  } else {
    const parts = specifier.split("/");
    packageName = parts[0];
    subpath = parts.length > 1 ? "./" + parts.slice(1).join("/") : ".";
  }

  const pkgDir = (basePath + "/" + packageName).replace(/\\/g, "/");
  const pkgJsonPath = pkgDir + "/package.json";

  const hasPkgJson = archive.isFile(pkgJsonPath);

  if (!hasPkgJson) {
    return null;
  }

  const pkgContent = archive.readFileUtf8(pkgJsonPath);
  if (!pkgContent) return null;

  const pkg = JSON.parse(pkgContent);

  // 解析 exports
  if (pkg.exports) {
    const resolved = resolveExports(pkg.exports, subpath, pkgDir);
    if (resolved && archive.isFile(resolved)) {
      return {
        url: pathToFileURL(resolved).href,
        format: guessFormat(resolved),
        shortCircuit: true,
      };
    }
  }

  // subpath 不是 "."，直接拼接路径
  if (subpath !== ".") {
    const target = path.posix.normalize(pkgDir + "/" + subpath.slice(2)); // 去掉 "./"
    return tryResolveAbsPath(target);
  }

  // 回退到 main
  // 注意：不使用 pkg.module，因为 Node.js 原生 ESM resolver 不认 module 字段
  // （module 是 bundler 惯例，对应的文件可能包含 ESM 语法但没有 type:module 声明）
  if (pkg.main) {
    const entry = path.posix.normalize(pkgDir + "/" + pkg.main);
    return tryResolveAbsPath(entry);
  }

  // 默认 index.js
  return tryResolveAbsPath(pkgDir + "/index");
}

/**
 * 解析 package.json exports 字段
 */
function resolveExports(exports, subpath, pkgDir) {
  if (typeof exports === "string") {
    if (subpath === ".") {
      return path.posix.normalize(pkgDir + "/" + exports);
    }
    return null;
  }

  if (typeof exports !== "object" || exports === null) {
    return null;
  }

  // 如果 exports 有 subpath key
  const target = exports[subpath];
  if (target) {
    return resolveExportTarget(target, pkgDir);
  }

  // 如果 exports 直接是条件映射 (没有 "." key)
  if (!("." in exports) && subpath === ".") {
    return resolveExportTarget(exports, pkgDir);
  }

  // 处理通配符 exports
  for (const [pattern, value] of Object.entries(exports)) {
    if (pattern.includes("*")) {
      const regex = new RegExp(
        "^" + pattern.replace(/\*/g, "(.+)") + "$"
      );
      const match = subpath.match(regex);
      if (match) {
        const resolved = resolveExportTarget(value, pkgDir, match[1]);
        if (resolved) return resolved;
      }
    }
  }

  return null;
}

/**
 * 解析 export target (可能是字符串或条件对象)
 */
function resolveExportTarget(target, pkgDir, wildcardValue) {
  if (typeof target === "string") {
    const resolved = wildcardValue !== undefined
      ? target.replace(/\*/g, wildcardValue)
      : target;
    return path.posix.normalize(pkgDir + "/" + resolved);
  }

  if (typeof target === "object" && target !== null) {
    // 条件映射：import > node > default > require
    const conditions = ["import", "node", "default", "require"];
    for (const cond of conditions) {
      if (cond in target) {
        const result = resolveExportTarget(target[cond], pkgDir, wildcardValue);
        if (result) return result;
      }
    }
  }

  return null;
}

/**
 * 尝试解析绝对路径（带扩展名猜测）
 */
function tryResolveAbsPath(absPath) {
  const normalized = absPath.replace(/\\/g, "/");

  // 精确匹配
  if (archive.isFile(normalized)) {
    return {
      url: pathToFileURL(normalized).href,
      format: guessFormat(normalized),
      shortCircuit: true,
    };
  }

  // 尝试扩展名
  const extensions = [".js", ".mjs", ".cjs", ".json"];
  for (const ext of extensions) {
    if (archive.isFile(normalized + ext)) {
      return {
        url: pathToFileURL(normalized + ext).href,
        format: guessFormat(normalized + ext),
        shortCircuit: true,
      };
    }
  }

  // 作为目录 → index
  for (const ext of extensions) {
    const indexPath = normalized + "/index" + ext;
    if (archive.isFile(indexPath)) {
      return {
        url: pathToFileURL(indexPath).href,
        format: guessFormat(indexPath),
        shortCircuit: true,
      };
    }
  }

  // 作为目录 → package.json
  const pkgPath = normalized + "/package.json";
  if (archive.isFile(pkgPath)) {
    const content = archive.readFileUtf8(pkgPath);
    if (content) {
      const pkg = JSON.parse(content);
      const entry = resolvePackageEntry(pkg, normalized);
      if (entry && archive.isFile(entry)) {
        return {
          url: pathToFileURL(entry).href,
          format: guessFormat(entry),
          shortCircuit: true,
        };
      }
    }
  }

  return null;
}

/**
 * 从 package.json 解析入口
 */
function resolvePackageEntry(pkg, pkgDir) {
  if (pkg.exports) {
    const resolved = resolveExports(pkg.exports, ".", pkgDir);
    if (resolved) return resolved;
  }
  // 不使用 pkg.module（bundler 惯例，非 Node.js 标准）
  if (pkg.main) {
    return path.posix.normalize(pkgDir + "/" + pkg.main);
  }
  return null;
}

function guessFormat(filePath) {
  if (filePath.endsWith(".mjs")) return "module";
  if (filePath.endsWith(".cjs")) return "commonjs";
  if (filePath.endsWith(".json")) return "json";

  // 检查最近的 package.json 的 type 字段
  const rel = archive.toRelative(filePath);
  if (rel !== null) {
    let dir = path.posix.dirname(rel);
    while (true) {
      const pkgPath = (dir === "" ? "" : dir + "/") + "package.json";
      const basePath = archive.getBasePath();
      const content = archive.readFileUtf8(basePath + "/" + pkgPath);
      if (content) {
        const pkg = JSON.parse(content);
        if (pkg.type === "module") return "module";
        return "commonjs";
      }
      if (dir === "" || dir === ".") break;
      dir = path.posix.dirname(dir);
    }
  }

  return "commonjs";
}
