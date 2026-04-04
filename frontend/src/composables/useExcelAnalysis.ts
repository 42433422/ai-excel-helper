import { ref } from 'vue'
import type { ChatMessageExtras } from './useChatMessages'

interface UseChatMessagesReturn {
  addAndSaveMessage: (
    content: string,
    role?: 'user' | 'ai' | 'task',
    extras?: ChatMessageExtras
  ) => Promise<void>
}

interface UseExcelAnalysisOptions {
  onAnalyzed?: (payload: {
    fileName: string
    summary: string
    result: ExcelAnalysisResult
  }) => void
  onAnalyzeStart?: (payload: { fileName: string }) => void
  onAnalyzeProgress?: (payload: { fileName: string; step: string; progress?: number }) => void
  onAnalyzeDone?: (payload: { fileName: string; success: boolean; message?: string }) => void
}

export interface ExcelAnalysisResult {
  fields?: string[]
  sheets?: Array<{
    sheet_index?: number
    sheet_name?: string
    fields?: any[]
    sample_rows?: Record<string, any>[]
    grid_preview?: { rows?: any[][] }
    style_cache?: {
      styles?: Record<string, any>
      cell_style_refs?: Record<string, string>
    }
    tables?: Array<{
      table_index?: number
      header_row?: number
      fields?: any[]
      sample_rows?: Record<string, any>[]
    }>
  }>
  preview_data?: {
    sheet_name?: string
    sheet_names?: string[]
    sample_rows?: Record<string, any>[]
    grid_preview?: {
      rows?: any[][]
    }
    all_sheets?: Array<{
      sheet_index?: number
      sheet_name?: string
      fields?: any[]
      sample_rows?: Record<string, any>[]
      grid_preview?: { rows?: any[][] }
      style_cache?: {
        styles?: Record<string, any>
        cell_style_refs?: Record<string, string>
      }
      tables?: Array<{
        table_index?: number
        header_row?: number
        fields?: any[]
        sample_rows?: Record<string, any>[]
      }>
    }>
    tables?: Array<{
      table_index?: number
      header_row?: number
      fields?: any[]
      sample_rows?: Record<string, any>[]
    }>
    grid_style_cache?: {
      styles?: Record<string, any>
      cell_style_refs?: Record<string, string>
    }
  }
}

async function extractSingleSheetDetail(file: File, sheetName: string): Promise<any | null> {
  try {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('sheet_name', sheetName)
    formData.append('analyze_all_sheets', 'false')
    const controller = new AbortController()
    const timeoutId = window.setTimeout(() => controller.abort(), 20000)
    const response = await fetch('/api/templates/extract-grid', {
      method: 'POST',
      body: formData,
      signal: controller.signal
    })
    window.clearTimeout(timeoutId)
    const data = await response.json().catch(() => ({}))
    if (!response.ok || !data?.success) return null
    return {
      sheet_name: sheetName,
      fields: Array.isArray(data?.fields) ? data.fields : [],
      sample_rows: Array.isArray(data?.preview_data?.sample_rows) ? data.preview_data.sample_rows : [],
      grid_preview: data?.preview_data?.grid_preview || { rows: [] },
      style_cache: data?.preview_data?.grid_style_cache || { styles: {}, cell_style_refs: {} },
      tables: Array.isArray(data?.preview_data?.tables) ? data.preview_data.tables : []
    }
  } catch (_e) {
    return null
  }
}

export function useExcelAnalysis(messages: UseChatMessagesReturn, options: UseExcelAnalysisOptions = {}) {
  const excelAnalyzeUploading = ref(false)
  const excelAnalyzeInputRef = ref<HTMLInputElement | null>(null)

  function triggerExcelAnalyzeUpload() {
    if (excelAnalyzeUploading.value) return
    excelAnalyzeInputRef.value?.click()
  }

  function summarizeExcelAnalysisResult(result: ExcelAnalysisResult): string {
    const sheetList = Array.isArray(result?.sheets)
      ? result.sheets
      : (Array.isArray(result?.preview_data?.all_sheets) ? result.preview_data?.all_sheets : [])
    const sheetNames = Array.isArray((result as any)?.preview_data?.sheet_names)
      ? ((result as any).preview_data.sheet_names as any[])
          .map((x) => String(x || '').trim())
          .filter(Boolean)
      : []

    const fields = Array.isArray(result?.fields) ? result.fields : []
    const sampleRows = Array.isArray(result?.preview_data?.sample_rows) ? result.preview_data.sample_rows : []
    const sheetName = result?.preview_data?.sheet_name || 'Sheet1'
    const gridRows = Array.isArray(result?.preview_data?.grid_preview?.rows)
      ? result.preview_data.grid_preview.rows.length
      : 0

    const fieldNames = fields
      .map((f) => String((f as any)?.label || (f as any)?.name || '').trim())
      .filter(Boolean)
      .slice(0, 40)

    const sheetSummaryLines = sheetList
      .slice(0, 12)
      .map((sheet: any, idx: number) => {
        const no = Number(sheet?.sheet_index) || idx + 1
        const name = String(sheet?.sheet_name || `Sheet${no}`)
        const rowCount = Array.isArray(sheet?.grid_preview?.rows) ? sheet.grid_preview.rows.length : 0
        const fieldCount = Array.isArray(sheet?.fields) ? sheet.fields.length : 0
        return `Sheet ${no}（${name}）：词条${fieldCount}，网格行${rowCount}`
      })

    const totalStyleCellsFromSheets = sheetList.reduce((acc: number, sheet: any) => {
      const refs = sheet?.style_cache?.cell_style_refs
      return acc + (refs ? Object.keys(refs).length : 0)
    }, 0)
    const fallbackStyleRefs = result?.preview_data?.grid_style_cache?.cell_style_refs
    const totalStyleCells = totalStyleCellsFromSheets || (fallbackStyleRefs ? Object.keys(fallbackStyleRefs).length : 0)
    const totalLogicalTables = sheetList.reduce((acc: number, sheet: any) => {
      const tables = Array.isArray(sheet?.tables) ? sheet.tables.length : 0
      return acc + tables
    }, Array.isArray(result?.preview_data?.tables) ? result.preview_data.tables.length : 0)

    const tableSummaryLines = sheetList
      .flatMap((sheet: any, idx: number) => {
        const no = Number(sheet?.sheet_index) || idx + 1
        const name = String(sheet?.sheet_name || `Sheet${no}`)
        const tables = Array.isArray(sheet?.tables) ? sheet.tables : []
        return tables.slice(0, 5).map((tb: any) => {
          const tbNo = Number(tb?.table_index) || 1
          const tbFields = Array.isArray(tb?.fields) ? tb.fields.length : 0
          const tbSamples = Array.isArray(tb?.sample_rows) ? tb.sample_rows.length : 0
          return `Sheet ${no}（${name}）- 表${tbNo}：词条${tbFields}，样例${tbSamples}`
        })
      })
      .slice(0, 12)

    const detailSheets = (sheetList.length ? sheetList : [{
      sheet_index: 1,
      sheet_name: sheetName,
      fields,
      sample_rows: sampleRows,
      grid_preview: { rows: Array.isArray(result?.preview_data?.grid_preview?.rows) ? result.preview_data?.grid_preview?.rows : [] }
    }]).slice(0, 8)

    const sheetDetailLines = detailSheets.flatMap((sheet: any, idx: number) => {
      const no = Number(sheet?.sheet_index) || idx + 1
      const name = String(sheet?.sheet_name || `Sheet${no}`)
      const sheetFields = (Array.isArray(sheet?.fields) ? sheet.fields : [])
        .map((f: any) => String(f?.label || f?.name || '').trim())
        .filter(Boolean)
        .slice(0, 30)
      const sheetRows = Array.isArray(sheet?.grid_preview?.rows) ? sheet.grid_preview.rows.length : 0
      const sheetSamples = (Array.isArray(sheet?.sample_rows) ? sheet.sample_rows : [])
        .slice(0, 2)
        .map((row: any, sIdx: number) => {
          const pairs = Object.entries(row || {})
            .slice(0, 5)
            .map(([k, v]) => `${k}:${String(v ?? '').slice(0, 30)}`)
            .join('；')
          return `  ${sIdx + 1}. ${pairs || '无'}`
        })
      return [
        `Sheet ${no}（${name}）`,
        `- 词条数量：${sheetFields.length}`,
        `- 词条：${sheetFields.length ? sheetFields.join('、') : '无'}`,
        `- 网格行数：${sheetRows}`,
        `- 样例数据：`,
        ...(sheetSamples.length ? sheetSamples : ['  无样例行'])
      ]
    })

    return [
      `Excel 分析完成`,
      `工作表总数：${Math.max(sheetList.length, sheetNames.length, 1)}`,
      `工作表：${sheetName}`,
      `词条数量：${fieldNames.length}`,
      `词条：${fieldNames.length ? fieldNames.join('、') : '无'}`,
      `网格行数：${gridRows}`,
      `识别表块：${totalLogicalTables}`,
      `样式缓存单元格：${totalStyleCells}`,
      ...(sheetSummaryLines.length ? ['分表摘要：', ...sheetSummaryLines] : []),
      ...(tableSummaryLines.length ? ['逻辑表块分类：', ...tableSummaryLines] : []),
      `分表详细分析：`,
      ...sheetDetailLines,
      ...(sheetList.length > 8 ? [`（仅展示前8个工作表，剩余 ${sheetList.length - 8} 个）`] : [])
    ].join('\n')
  }

  async function onExcelAnalyzeFileChange(e: Event): Promise<void> {
    const file = (e?.target as any)?.files?.[0] as File | undefined
    ;(e.target as HTMLInputElement).value = ''
    if (!file) return

    if (!/\.(xlsx|xls)$/i.test(file.name)) {
      await messages.addAndSaveMessage('仅支持上传 .xlsx 或 .xls 文件进行分析。', 'ai')
      return
    }

    excelAnalyzeUploading.value = true
    await messages.addAndSaveMessage(`开始分析 Excel：${file.name}`, 'user')
    options.onAnalyzeStart?.({ fileName: file.name })

    try {
      const formData = new FormData()
      formData.append('file', file)
      formData.append('analyze_all_sheets', 'true')
      const controller = new AbortController()
      const timeoutId = window.setTimeout(() => controller.abort(), 30000)
      const response = await fetch('/api/templates/extract-grid', {
        method: 'POST',
        body: formData,
        signal: controller.signal
      })
      window.clearTimeout(timeoutId)
      const data = await response.json().catch(() => ({}))

      if (!response.ok || !data?.success) {
        throw new Error(data?.message || `HTTP ${response.status}`)
      }

      // 兼容旧后端：若只返回 sheet_names 而没有 all_sheets 明细，则前端逐 sheet 兜底补齐。
      const hasMultiSheetDetails =
        Array.isArray(data?.sheets) && data.sheets.length > 0
          || (Array.isArray(data?.preview_data?.all_sheets) && data.preview_data.all_sheets.length > 0)
      const sheetNames = Array.isArray(data?.preview_data?.sheet_names) ? data.preview_data.sheet_names : []
      if (!hasMultiSheetDetails && sheetNames.length > 1) {
        const detailedSheets: any[] = []
        for (let i = 0; i < sheetNames.length; i += 1) {
          const name = String(sheetNames[i] || '').trim()
          if (!name) continue
          options.onAnalyzeProgress?.({
            fileName: file.name,
            step: `补全分表详情 ${i + 1}/${sheetNames.length}`,
            progress: Math.floor(((i + 1) / sheetNames.length) * 100)
          })
          const detail = await extractSingleSheetDetail(file, name)
          if (detail) {
            detailedSheets.push({
              sheet_index: i + 1,
              ...detail
            })
          }
        }
        if (detailedSheets.length) {
          data.sheets = detailedSheets
          if (!data.preview_data) data.preview_data = {}
          data.preview_data.all_sheets = detailedSheets
        }
      }

      const summary = summarizeExcelAnalysisResult(data)
      await messages.addAndSaveMessage(summary, 'ai')
      options.onAnalyzed?.({
        fileName: file.name,
        summary,
        result: data
      })
      options.onAnalyzeDone?.({ fileName: file.name, success: true })
    } catch (err: any) {
      const isAbort = err?.name === 'AbortError'
      const msg = isAbort
        ? 'Excel 分析超时（30秒），请尝试更小文件或减少工作表复杂度。'
        : `Excel 分析失败：${err?.message || '未知错误'}`
      await messages.addAndSaveMessage(msg, 'ai')
      options.onAnalyzeDone?.({ fileName: file.name, success: false, message: msg })
    } finally {
      excelAnalyzeUploading.value = false
    }
  }

  return {
    excelAnalyzeUploading,
    excelAnalyzeInputRef,
    triggerExcelAnalyzeUpload,
    onExcelAnalyzeFileChange
  }
}
