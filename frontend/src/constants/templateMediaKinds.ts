/**
 * 模板库媒体类型：与公开市场「办公员工包」五类文件一致（读/写员工各一类）。
 * 预览/上传 UI 按此枚举扩展，避免仅写死 Excel + Word。
 */
export const TEMPLATE_MEDIA_KINDS = ['excel', 'word', 'csv', 'ppt', 'pdf'] as const

export type TemplateMediaKind = (typeof TEMPLATE_MEDIA_KINDS)[number]

export const TEMPLATE_MEDIA_LABELS: Record<TemplateMediaKind, string> = {
  excel: 'Excel',
  word: 'Word',
  csv: 'CSV',
  ppt: 'PPT',
  pdf: 'PDF',
}

/** 与商店办公员工包分组顺序一致 */
export const TEMPLATE_MEDIA_ORDER: TemplateMediaKind[] = ['ppt', 'excel', 'csv', 'pdf', 'word']

export const TEMPLATE_MEDIA_ACCEPT = '.xlsx,.xls,.docx,.csv,.pptx,.pdf'

const EXT_TO_KIND: Record<string, TemplateMediaKind> = {
  xlsx: 'excel',
  xls: 'excel',
  docx: 'word',
  csv: 'csv',
  pptx: 'ppt',
  pdf: 'pdf',
}

const KIND_ICON: Record<TemplateMediaKind, string> = {
  excel: 'fa-file-excel-o',
  word: 'fa-file-word-o',
  csv: 'fa-file-text-o',
  ppt: 'fa-file-powerpoint-o',
  pdf: 'fa-file-pdf-o',
}

const KIND_CARD_CLASS: Record<TemplateMediaKind, string> = {
  excel: 'tp-card--excel',
  word: 'tp-card--word',
  csv: 'tp-card--csv',
  ppt: 'tp-card--ppt',
  pdf: 'tp-card--pdf',
}

export function isTemplateMediaKind(value: unknown): value is TemplateMediaKind {
  return typeof value === 'string' && (TEMPLATE_MEDIA_KINDS as readonly string[]).includes(value)
}

export function normalizeTemplateMediaKind(
  value: unknown,
  fallback: TemplateMediaKind = 'excel'
): TemplateMediaKind {
  return isTemplateMediaKind(value) ? value : fallback
}

export function templateMediaKindFromFilename(filename?: string | null): TemplateMediaKind | null {
  const name = String(filename || '').trim()
  if (!name.includes('.')) return null
  const ext = name.split('.').pop()?.toLowerCase() || ''
  return EXT_TO_KIND[ext] || null
}

export function templateMediaIconClass(kind: TemplateMediaKind | string): string {
  if (isTemplateMediaKind(kind)) return KIND_ICON[kind]
  return 'fa-file-o'
}

export function templateMediaCardClass(kind: TemplateMediaKind | string): string {
  if (isTemplateMediaKind(kind)) return KIND_CARD_CLASS[kind]
  return 'tp-card--excel'
}

export function templateMediaUploadHint(): string {
  return '支持 Excel、Word、CSV、PPT、PDF（.xlsx / .xls / .docx / .csv / .pptx / .pdf）'
}
