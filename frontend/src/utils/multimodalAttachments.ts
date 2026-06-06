/**
 * 聊天多模态附件：转为后端 ``context.multimodal_attachments`` 所需的行结构。
 * 支持图片（jpeg/png/webp/gif）与 PDF（文本抽取由服务端 pdfplumber 完成）。
 */

export type MultimodalAttachmentRow = {
  kind: 'image' | 'pdf'
  filename: string
  mime_type: string
  /** ``data:<mime>;base64,...`` */
  data_url: string
}

const MAX_FILES = 6
const MAX_BYTES_PER_FILE = 12 * 1024 * 1024

function extOf(name: string): string {
  const i = name.lastIndexOf('.')
  return i >= 0 ? name.slice(i).toLowerCase() : ''
}

/** 浏览器端不用 ``mime-types``（其依赖 Node ``path``，会被 Vite 外部化并告警）。 */
const EXT_TO_MIME: Record<string, string> = {
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.webp': 'image/webp',
  '.gif': 'image/gif',
  '.pdf': 'application/pdf',
}

function resolveMime(file: File): string {
  const t = (file.type || '').trim().toLowerCase()
  if (t) return t
  const ext = extOf(file.name)
  return EXT_TO_MIME[ext] || 'application/octet-stream'
}

function readAsDataURL(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const fr = new FileReader()
    fr.onload = () => resolve(String(fr.result || ''))
    fr.onerror = () => reject(fr.error || new Error('read failed'))
    fr.readAsDataURL(file)
  })
}

export async function filesToMultimodalRows(
  files: FileList | File[]
): Promise<{ ok: true; rows: MultimodalAttachmentRow[] } | { ok: false; error: string }> {
  const arr = Array.from(files as FileList)
  if (!arr.length) return { ok: false, error: '未选择文件' }
  if (arr.length > MAX_FILES) {
    return { ok: false, error: `一次最多 ${MAX_FILES} 个文件` }
  }
  const rows: MultimodalAttachmentRow[] = []
  for (const file of arr) {
    if (file.size > MAX_BYTES_PER_FILE) {
      return { ok: false, error: `「${file.name}」超过 ${Math.round(MAX_BYTES_PER_FILE / (1024 * 1024))}MB 上限` }
    }
    const mime = resolveMime(file)
    const ext = extOf(file.name)
    const allowedExt = new Set(['.png', '.jpg', '.jpeg', '.webp', '.gif', '.pdf'])
    if (!allowedExt.has(ext)) {
      return { ok: false, error: `不支持的扩展名: ${ext || '(无)'}（允许: ${[...allowedExt].join(', ')}）` }
    }
    if (mime !== 'application/pdf' && !mime.startsWith('image/')) {
      return { ok: false, error: `不支持的类型: ${mime}（${file.name}）` }
    }
    const dataUrl = await readAsDataURL(file)
    if (!dataUrl.startsWith('data:')) {
      return { ok: false, error: `读取失败: ${file.name}` }
    }
    const kind: MultimodalAttachmentRow['kind'] = mime === 'application/pdf' ? 'pdf' : 'image'
    rows.push({
      kind,
      filename: file.name || (kind === 'pdf' ? 'upload.pdf' : 'image.bin'),
      mime_type: mime,
      data_url: dataUrl,
    })
  }
  return { ok: true, rows }
}
