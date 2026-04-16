/**
 * zip-reader.mjs - 纯 JS ZIP 解析器（仅支持 STORE 模式）
 *
 * 从 ZIP 文件的 Central Directory 构建文件索引（路径 → {offset, size}）。
 * 配合 STORE 模式的 ZIP（pack-memory-fs.mjs 产出），readFile 可直接
 * zipBuffer.subarray() 零拷贝返回文件内容，无需解压。
 *
 * 不支持：DEFLATE / ZIP64 / 加密 / 多磁盘
 * 遇到非 STORE 条目会抛错（fail-fast）。
 */

// ==================== ZIP 格式常量 ====================

const EOCD_SIG = 0x06054b50
const CENTRAL_DIR_SIG = 0x02014b50
const LOCAL_FILE_HEADER_SIG = 0x04034b50
const METHOD_STORE = 0

// EOCD 最小 22 字节，最大回溯 65557 字节（22 + 65535 comment）
const EOCD_MIN_SIZE = 22
const EOCD_MAX_SEARCH = 65557

/**
 * 解析 ZIP Buffer 中的中央目录，返回文件索引。
 *
 * @param {Buffer} zipBuffer - 完整的 ZIP 文件 Buffer
 * @returns {Map<string, { offset: number, size: number }>}
 *   key: 文件相对路径（如 "express/index.js"）
 *   value: { offset: 数据在 zipBuffer 中的起始偏移, size: 未压缩大小 }
 */
export function parseZipIndex(zipBuffer) {
  const eocd = findEOCD(zipBuffer)

  const entryCount = zipBuffer.readUInt16LE(eocd + 10)  // total entries
  const centralDirOffset = zipBuffer.readUInt32LE(eocd + 16)

  /** @type {Map<string, { offset: number, size: number }>} */
  const index = new Map()
  let pos = centralDirOffset

  for (let i = 0; i < entryCount; i++) {
    if (pos + 46 > zipBuffer.length) {
      throw new Error(`[zip-reader] Central directory entry ${i} truncated`)
    }

    const sig = zipBuffer.readUInt32LE(pos)
    if (sig !== CENTRAL_DIR_SIG) {
      throw new Error(
        `[zip-reader] Invalid central directory signature at offset ${pos}: 0x${sig.toString(16)}`
      )
    }

    const method = zipBuffer.readUInt16LE(pos + 10)
    const uncompressedSize = zipBuffer.readUInt32LE(pos + 24)
    const nameLen = zipBuffer.readUInt16LE(pos + 28)
    const extraLen = zipBuffer.readUInt16LE(pos + 30)
    const commentLen = zipBuffer.readUInt16LE(pos + 32)
    const localHeaderOffset = zipBuffer.readUInt32LE(pos + 42)

    const name = zipBuffer.toString("utf8", pos + 46, pos + 46 + nameLen)

    // 跳过目录条目（名称以 / 结尾）
    if (!name.endsWith("/")) {
      if (method !== METHOD_STORE) {
        throw new Error(
          `[zip-reader] Unsupported compression method ${method} for "${name}". ` +
          `Only STORE (method=0) is supported. Re-pack with: node scripts/pack-memory-fs.mjs`
        )
      }

      // 从 Local File Header 读取 extra field 长度以精确计算 data offset
      // LFH: 30 bytes header + nameLen + extraFieldLen
      const lfhSig = zipBuffer.readUInt32LE(localHeaderOffset)
      if (lfhSig !== LOCAL_FILE_HEADER_SIG) {
        throw new Error(
          `[zip-reader] Invalid local file header signature for "${name}" at offset ${localHeaderOffset}`
        )
      }
      const lfhNameLen = zipBuffer.readUInt16LE(localHeaderOffset + 26)
      const lfhExtraLen = zipBuffer.readUInt16LE(localHeaderOffset + 28)
      const dataOffset = localHeaderOffset + 30 + lfhNameLen + lfhExtraLen

      index.set(name, { offset: dataOffset, size: uncompressedSize })
    }

    pos += 46 + nameLen + extraLen + commentLen
  }

  return index
}

/**
 * 从 ZIP 文件末尾向前搜索 End of Central Directory Record (EOCD)。
 *
 * @param {Buffer} buf
 * @returns {number} EOCD 在 buf 中的偏移量
 */
function findEOCD(buf) {
  const searchStart = Math.max(0, buf.length - EOCD_MAX_SEARCH)

  // 从末尾向前搜索 EOCD 签名
  for (let i = buf.length - EOCD_MIN_SIZE; i >= searchStart; i--) {
    if (buf.readUInt32LE(i) === EOCD_SIG) {
      return i
    }
  }

  throw new Error("[zip-reader] End of Central Directory not found. Is this a valid ZIP file?")
}
