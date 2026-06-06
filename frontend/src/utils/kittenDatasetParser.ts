let xlsxLibPromise: Promise<typeof import('xlsx')> | null = null

const loadXlsx = async (): Promise<typeof import('xlsx')> => {
  if (!xlsxLibPromise) {
    xlsxLibPromise = import('xlsx')
  }
  return xlsxLibPromise
}

export interface ParsedDatasetFile {
  rows: number
  columns: string[]
  preview: Array<Record<string, unknown> | unknown[]>
  sampleRows: Record<string, unknown>[]
  fieldProfiles: KittenFieldProfile[]
}

export type KittenFieldType = 'number' | 'date' | 'category' | 'text'

export interface KittenFieldProfile {
  name: string
  type: KittenFieldType
  nonEmpty: number
  uniqueCount: number
}

const WORKER_SUPPORTED_EXTS = new Set(['csv', 'txt', 'json', 'xlsx', 'xls'])
const WORKER_PARSE_MIN_BYTES = 96 * 1024
export const KITTEN_DATASET_SAMPLE_LIMIT = 1000
let parserWorker: Worker | null = null
let parserWorkerReqId = 0

const getExtension = (filename: string): string => {
  const idx = filename.lastIndexOf('.')
  return idx >= 0 ? filename.slice(idx + 1).toLowerCase() : ''
}

const getParserWorker = (): Worker => {
  if (!parserWorker) {
    parserWorker = new Worker(new URL('../workers/datasetParser.worker.ts', import.meta.url), { type: 'module' })
    parserWorker.addEventListener('error', () => {
      parserWorker = null
    })
  }
  return parserWorker
}

const parseWithWorker = (file: File, ext: string): Promise<ParsedDatasetFile> => {
  const worker = getParserWorker()
  const requestId = ++parserWorkerReqId
  return new Promise((resolve, reject) => {
    const timeout = window.setTimeout(() => {
      cleanup()
      reject(new Error('Worker 解析超时，请稍后重试。'))
    }, 30000)

    const cleanup = () => {
      window.clearTimeout(timeout)
      worker.removeEventListener('message', onMessage)
    }

    const onMessage = (event: MessageEvent) => {
      const data = event.data as { requestId?: number; ok?: boolean; payload?: ParsedDatasetFile; error?: string }
      if (!data || data.requestId !== requestId) return
      cleanup()
      if (!data.ok || !data.payload) {
        reject(new Error(data.error || 'Worker 解析失败'))
        return
      }
      resolve(data.payload)
    }

    worker.addEventListener('message', onMessage)
    worker.postMessage({ requestId, file, ext })
  })
}

const toFiniteNumber = (value: unknown): number | null => {
  if (typeof value === 'number') return Number.isFinite(value) ? value : null
  if (typeof value !== 'string') return null
  const cleaned = value.replace(/[,，\s¥￥%]/g, '').trim()
  if (!cleaned) return null
  const n = Number(cleaned)
  return Number.isFinite(n) ? n : null
}

const isDateLike = (value: unknown): boolean => {
  if (value instanceof Date) return !Number.isNaN(value.getTime())
  if (typeof value !== 'string' && typeof value !== 'number') return false
  const raw = String(value).trim()
  if (!raw || /^\d+(\.\d+)?$/.test(raw)) return false
  const ts = Date.parse(raw)
  return Number.isFinite(ts)
}

const profileFields = (rows: Record<string, unknown>[], columns: string[]): KittenFieldProfile[] => {
  return columns.map((name) => {
    const values = rows.map((row) => row[name]).filter((value) => value !== null && value !== undefined && String(value).trim() !== '')
    const nonEmpty = values.length
    const uniqueCount = new Set(values.map((value) => String(value))).size
    const numericCount = values.filter((value) => toFiniteNumber(value) !== null).length
    const dateCount = values.filter(isDateLike).length
    let type: KittenFieldType = 'text'
    if (nonEmpty > 0 && numericCount / nonEmpty >= 0.8) {
      type = 'number'
    } else if (nonEmpty > 0 && dateCount / nonEmpty >= 0.7) {
      type = 'date'
    } else if (uniqueCount <= Math.max(20, Math.ceil(nonEmpty * 0.35))) {
      type = 'category'
    }
    return { name, type, nonEmpty, uniqueCount }
  })
}

const normalizeRows = (rows: Record<string, unknown>[], columns: string[]): ParsedDatasetFile => {
  const sampleRows = rows.slice(0, KITTEN_DATASET_SAMPLE_LIMIT)
  return {
    rows: rows.length,
    columns,
    preview: rows.slice(0, 3),
    sampleRows,
    fieldProfiles: profileFields(sampleRows, columns)
  }
}

const normalizeObjectArray = (rows: Record<string, unknown>[]): ParsedDatasetFile => {
  const columnSet = new Set<string>()
  for (const row of rows.slice(0, 50)) {
    Object.keys(row || {}).forEach((key) => columnSet.add(key))
  }
  const columns = Array.from(columnSet)
  return normalizeRows(rows, columns)
}

const readFileText = async (file: File): Promise<string> => {
  if (typeof file.text === 'function') return file.text()
  const buffer = await file.arrayBuffer()
  return new TextDecoder('utf-8').decode(buffer)
}

const normalizeJsonPayload = (payload: unknown): ParsedDatasetFile => {
  if (Array.isArray(payload)) {
    if (payload.length === 0) {
      return { rows: 0, columns: [], preview: [], sampleRows: [], fieldProfiles: [] }
    }
    if (payload.every((item) => item && typeof item === 'object' && !Array.isArray(item))) {
      return normalizeObjectArray(payload as Record<string, unknown>[])
    }
    return {
      rows: payload.length,
      columns: ['value'],
      preview: payload.slice(0, 3).map((value) => ({ value })),
      sampleRows: payload.slice(0, KITTEN_DATASET_SAMPLE_LIMIT).map((value) => ({ value })),
      fieldProfiles: profileFields(payload.slice(0, KITTEN_DATASET_SAMPLE_LIMIT).map((value) => ({ value })), ['value'])
    }
  }

  if (payload && typeof payload === 'object') {
    const asRecord = payload as Record<string, unknown>
    if (Array.isArray(asRecord.data)) {
      return normalizeJsonPayload(asRecord.data)
    }
    return normalizeRows([asRecord], Object.keys(asRecord))
  }

  throw new Error('JSON 文件结构不支持，请使用对象、对象数组或 { data: [] } 格式。')
}

const parseCsvLike = async (file: File): Promise<ParsedDatasetFile> => {
  const text = await readFileText(file)
  const XLSX = await loadXlsx()
  const workbook = XLSX.read(text, { type: 'string' })
  const firstSheet = workbook.Sheets[workbook.SheetNames[0]]
  const rows = XLSX.utils.sheet_to_json(firstSheet, { header: 1, defval: '' }) as unknown[][]
  const headers = (rows[0] || []).map((x) => String(x))
  const bodyRows = rows.slice(1).map((row) => Object.fromEntries(headers.map((header, idx) => [header, row[idx] ?? ''])))
  return {
    ...normalizeRows(bodyRows, headers),
    preview: rows.slice(0, 3)
  }
}

const parseExcel = async (file: File): Promise<ParsedDatasetFile> => {
  const buffer = await file.arrayBuffer()
  const XLSX = await loadXlsx()
  const workbook = XLSX.read(buffer, { type: 'array' })
  const firstSheet = workbook.Sheets[workbook.SheetNames[0]]
  const rows = XLSX.utils.sheet_to_json(firstSheet) as Record<string, unknown>[]
  const columns = rows.length > 0 ? Object.keys(rows[0]) : []
  return normalizeRows(rows, columns)
}

const parseJson = async (file: File): Promise<ParsedDatasetFile> => {
  const text = await readFileText(file)
  try {
    const json = JSON.parse(text)
    return normalizeJsonPayload(json)
  } catch (_error) {
    throw new Error('JSON 解析失败，请检查文件格式是否正确。')
  }
}

export const parseDatasetFile = async (file: File): Promise<ParsedDatasetFile> => {
  const ext = getExtension(file.name)
  const shouldUseWorker = WORKER_SUPPORTED_EXTS.has(ext) && file.size >= WORKER_PARSE_MIN_BYTES
  if (shouldUseWorker) {
    try {
      return await parseWithWorker(file, ext)
    } catch (_err) {
      // Worker 不可用时自动回退主线程解析，保障功能可用。
    }
  }
  if (ext === 'csv' || ext === 'txt') {
    return parseCsvLike(file)
  }
  if (ext === 'json') {
    return parseJson(file)
  }
  if (ext === 'xlsx' || ext === 'xls') {
    return parseExcel(file)
  }
  throw new Error(`暂不支持该文件类型: .${ext || 'unknown'}`)
}
