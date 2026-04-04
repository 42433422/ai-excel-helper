interface ParsedDatasetFile {
  rows: number
  columns: string[]
  preview: Array<Record<string, unknown> | unknown[]>
}

let xlsxLibPromise: Promise<typeof import('xlsx')> | null = null

const loadXlsx = async (): Promise<typeof import('xlsx')> => {
  if (!xlsxLibPromise) {
    xlsxLibPromise = import('xlsx')
  }
  return xlsxLibPromise
}

const normalizeObjectArray = (rows: Record<string, unknown>[]): ParsedDatasetFile => {
  const columnSet = new Set<string>()
  for (const row of rows.slice(0, 50)) {
    Object.keys(row || {}).forEach((key) => columnSet.add(key))
  }
  const columns = Array.from(columnSet)
  return {
    rows: rows.length,
    columns,
    preview: rows.slice(0, 3),
  }
}

const normalizeJsonPayload = (payload: unknown): ParsedDatasetFile => {
  if (Array.isArray(payload)) {
    if (payload.length === 0) return { rows: 0, columns: [], preview: [] }
    if (payload.every((item) => item && typeof item === 'object' && !Array.isArray(item))) {
      return normalizeObjectArray(payload as Record<string, unknown>[])
    }
    return {
      rows: payload.length,
      columns: ['value'],
      preview: payload.slice(0, 3).map((value) => ({ value })),
    }
  }

  if (payload && typeof payload === 'object') {
    const asRecord = payload as Record<string, unknown>
    if (Array.isArray(asRecord.data)) return normalizeJsonPayload(asRecord.data)
    return {
      rows: 1,
      columns: Object.keys(asRecord),
      preview: [asRecord],
    }
  }

  throw new Error('JSON 文件结构不支持')
}

const parseCsvLike = async (file: File): Promise<ParsedDatasetFile> => {
  const text = await file.text()
  const XLSX = await loadXlsx()
  const workbook = XLSX.read(text, { type: 'string' })
  const firstSheet = workbook.Sheets[workbook.SheetNames[0]]
  const rows = XLSX.utils.sheet_to_json(firstSheet, { header: 1, defval: '' }) as unknown[][]
  const headers = (rows[0] || []).map((x) => String(x))
  return {
    rows: Math.max(rows.length - 1, 0),
    columns: headers,
    preview: rows.slice(0, 3),
  }
}

const parseExcel = async (file: File): Promise<ParsedDatasetFile> => {
  const buffer = await file.arrayBuffer()
  const XLSX = await loadXlsx()
  const workbook = XLSX.read(buffer, { type: 'array' })
  const firstSheet = workbook.Sheets[workbook.SheetNames[0]]
  const rows = XLSX.utils.sheet_to_json(firstSheet) as Record<string, unknown>[]
  const columns = rows.length > 0 ? Object.keys(rows[0]) : []
  return {
    rows: rows.length,
    columns,
    preview: rows.slice(0, 3),
  }
}

const parseJson = async (file: File): Promise<ParsedDatasetFile> => {
  const text = await file.text()
  const json = JSON.parse(text)
  return normalizeJsonPayload(json)
}

const parseByExt = async (file: File, ext: string): Promise<ParsedDatasetFile> => {
  if (ext === 'csv' || ext === 'txt') return parseCsvLike(file)
  if (ext === 'json') return parseJson(file)
  if (ext === 'xlsx' || ext === 'xls') return parseExcel(file)
  throw new Error(`暂不支持该文件类型: .${ext || 'unknown'}`)
}

self.onmessage = async (event: MessageEvent) => {
  const { requestId, file, ext } = (event.data || {}) as { requestId: number; file: File; ext: string }
  if (!requestId || !file) return
  try {
    const payload = await parseByExt(file, String(ext || '').toLowerCase())
    self.postMessage({ requestId, ok: true, payload })
  } catch (err) {
    self.postMessage({
      requestId,
      ok: false,
      error: err instanceof Error ? err.message : String(err || 'worker parse failed'),
    })
  }
}
