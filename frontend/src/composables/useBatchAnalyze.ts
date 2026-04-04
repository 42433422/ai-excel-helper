import { ref, computed, type Ref } from 'vue'
import { useBatchAnalyzeStore, type SheetInfo, type SheetGroup } from '../stores/batchAnalyze'
import templatePreviewApi from '../api/templatePreview'
import templateScopeRules from '../shared/templateScopeRules.json'

interface TemplateScopeRule {
  label: string
  templateType: string
  requiredTerms: string[]
}

const SCOPE_CONFIG = templateScopeRules as Record<string, TemplateScopeRule>

const TERM_EQUIVALENTS: Record<string, string[]> = {
  '产品型号': ['产品型号', '产 品 型 号', '型号', '产品编码', '品名'],
  '型号': ['型号', '产品型号', '产 品 型 号', '产品编码', '品名'],
  '规格': ['规格', '规格型号', '规格/kg', '规格型号', '规格/KG'],
  '价格': ['价格', '单价', '单价/元', '售价', '现金价'],
  '单价': ['单价', '价格', '单价/元', '售价', '现金价'],
  '金额': ['金额', '金额/元', '金额合计', '金额总计', '总金额', '合计', '家具厂金额'],
  '数量': ['数量', '数量(kg)', '数量/kg', '数量/件', '数量/桶', '库存数量', '库存'],
  '数量/KG': ['数量/KG', '数量/kg'],
  '数量/件': ['数量/件'],
  '电话': ['电话', '联系电话', '手机号', '手机', '电话号码'],
  '购买单位': ['购买单位', '单位', '单位名称', '客户名称', '厂名', '客户', '客户名'],
  '客户名称': ['客户名称', '购买单位', '单位名称', '厂名', '客户', '客户名'],
  '产品名称': ['产品名称', '产 品 名 称', '名称', '品名', '产品名', '商品名称'],
  '联系人': ['联系人', '收货人', '经手人', '负责人'],
  '地址': ['地址', '收货地址', '送货地址', '单位地址'],
  '日期': ['日期', '订单日期', '出货日期', '送货日期', '开单日期'],
  '单号': ['单号', '订单号', '订单编号', '单据编号', '编号'],
  '备注': ['备注', '备  注', '备 注', '说明', '附注', '备注说明'],
  '规格型号': ['规格型号', '规格', '型号', '规格/KG'],
  '单位': ['单位', '单位名称', '计量单位'],
  '仓库': ['仓库', '仓库名称', '库房'],
  '经手人': ['经手人', '经办人', '操作员'],
  '税前单价': ['税前单价', '不含税单价', '净单价'],
  '税后单价': ['税后单价', '含税单价', '单价'],
  '税率': ['税率', '税点', '税率%'],
  '税额': ['税额', '税额/元'],
  '折扣': ['折扣', '折后价', '折扣率'],
  '包装': ['包装', '包装形式', '件装'],
  '颜色': ['颜色', '色号', '色彩'],
  '等级': ['等级', '品质', '档次'],
  '品牌': ['品牌', '商标', '牌子'],
  '月份': ['月份', '月份'],
  '内': ['内', '内部'],
  '外': ['外', '外部'],
  '销售金额': ['销售金额', '销售额'],
  '实收款': ['实收款', '已收款', '已付款'],
  '下欠款金额': ['下欠款金额', '下欠款', '欠款'],
}

function normalizeTerm(value: string): string {
  if (!value) return ''
  let result = String(value)
  result = result.replace(/\s+/g, '')
  result = result.replace(/[\u200B-\u200F\uFEFF]/g, '')
  result = result.toLowerCase()
  return result.trim()
}

function fullWidthToHalfWidth(text: string): string {
  const halfWidth = text.replace(/[\uff01-\uff5e]/g, (char) => {
    const code = char.charCodeAt(0) - 0xfee0
    return code >= 0x21 && code <= 0x7e ? String.fromCharCode(code) : char
  })
  return halfWidth
}

function getEquivalentTerms(term: string): string[] {
  const key = String(term || '').trim()
  const normalizedKey = normalizeTerm(fullWidthToHalfWidth(key))

  for (const [canonical, aliases] of Object.entries(TERM_EQUIVALENTS)) {
    const normalizedCanonical = normalizeTerm(canonical)
    if (normalizedCanonical === normalizedKey) {
      return [normalizedKey, ...aliases.map(a => normalizeTerm(a))]
    }
    for (const alias of aliases) {
      if (normalizeTerm(alias) === normalizedKey) {
        return [normalizedKey, normalizedCanonical, ...aliases.map(a => normalizeTerm(a))]
      }
    }
  }

  return [normalizedKey]
}

function getAllNormalizedTerms(termSet: Set<string>): Set<string> {
  const result = new Set<string>()
  for (const term of termSet) {
    const equivalents = getEquivalentTerms(term)
    equivalents.forEach(eq => result.add(eq))

    const baseField = extractBaseField(term)
    if (baseField !== term) {
      result.add(baseField)
      const baseEquivalents = getEquivalentTerms(baseField)
      baseEquivalents.forEach(bq => result.add(bq))
    }
  }
  return result
}

function extractBaseField(term: string): string {
  const unitPatterns = [
    /\/(kg|件|元|桶|米|厘米|mm|cm|m|个|箱|包|箱|张|份|批|t|吨|g|克|mg)/i,
    /_kg$/i,
    /_piece$/i,
    /_unit$/i
  ]

  for (const pattern of unitPatterns) {
    if (pattern.test(term)) {
      return term.replace(pattern, '')
    }
  }
  return term
}

function calculateFieldSimilarity(fields1: string[], fields2: string[]): number {
  if (fields1.length === 0 && fields2.length === 0) return 1
  if (fields1.length === 0 || fields2.length === 0) return 0

  const set1 = new Set(fields1.map(normalizeTerm))
  const set2 = new Set(fields2.map(normalizeTerm))

  const all1 = getAllNormalizedTerms(set1)
  const all2 = getAllNormalizedTerms(set2)

  let intersection = 0
  for (const term of all1) {
    if (all2.has(term)) {
      intersection++
    }
  }

  const union = new Set([...all1, ...all2]).size
  return union > 0 ? intersection / union : 0
}

function inferTemplateTypeByFields(fields: string[]): { templateType: string; scopeKey: string; matchScore: number } {
  const fieldSet = new Set(fields.map(normalizeTerm))
  const allFieldTerms = getAllNormalizedTerms(fieldSet)

  let bestMatch: { scopeKey: string; matchScore: number } = { scopeKey: '', matchScore: 0 }

  for (const [scopeKey, meta] of Object.entries(SCOPE_CONFIG)) {
    const requiredTerms = meta.requiredTerms || []
    if (requiredTerms.length === 0) continue

    let matchedRequired = 0
    for (const term of requiredTerms) {
      const equivalents = getEquivalentTerms(term)
      if (equivalents.some(eq => allFieldTerms.has(eq))) {
        matchedRequired++
      }
    }

    const matchScore = matchedRequired / requiredTerms.length

    if (matchScore > bestMatch.matchScore) {
      bestMatch = { scopeKey, matchScore }
    }
  }

  const scopeKey = bestMatch.scopeKey || 'unknown'
  const templateType = SCOPE_CONFIG[scopeKey]?.templateType || '通用'
  return { templateType, scopeKey, matchScore: bestMatch.matchScore }
}

let groupCounter = 0

function generateGroupId(): string {
  return `group_${Date.now()}_${++groupCounter}`
}

function groupSheetsBySimilarity(sheets: SheetInfo[]): SheetGroup[] {
  if (sheets.length === 0) return []

  groupCounter = 0
  const groups: SheetGroup[] = []
  const usedIndices = new Set<number>()

  const sortedSheets = [...sheets].sort((a, b) => {
    const aRows = a.rowCount || 0
    const bRows = b.rowCount || 0
    return bRows - aRows
  })

  for (let i = 0; i < sortedSheets.length; i++) {
    if (usedIndices.has(i)) continue

    const currentSheet = sortedSheets[i]
    const groupSheets: SheetInfo[] = [currentSheet]
    usedIndices.add(i)

    const currentFields = currentSheet.fields.map(normalizeTerm)

    for (let j = i + 1; j < sortedSheets.length; j++) {
      if (usedIndices.has(j)) continue

      const compareSheet = sortedSheets[j]
      const similarity = calculateFieldSimilarity(currentFields, compareSheet.fields.map(normalizeTerm))

      if (similarity >= 0.5) {
        groupSheets.push(compareSheet)
        usedIndices.add(j)
      }
    }

    const allFields = new Set<string>()
    for (const sheet of groupSheets) {
      sheet.fields.forEach(f => allFields.add(normalizeTerm(f)))
    }

    const commonFields: string[] = []
    const differenceFields: string[] = []

    for (const field of allFields) {
      const appearsInAll = groupSheets.every(sheet =>
        sheet.fields.map(normalizeTerm).includes(field)
      )
      if (appearsInAll) {
        const originalField = groupSheets[0].fields.find(f => normalizeTerm(f) === field) || field
        commonFields.push(originalField)
      } else {
        differenceFields.push(field)
      }
    }

    const { templateType, scopeKey, matchScore } = inferTemplateTypeByFields(Array.from(allFields))

    const groupId = generateGroupId()
    const groupName = `${SCOPE_CONFIG[scopeKey]?.label || templateType || '通用'}-${groups.length + 1}`

    groups.push({
      id: groupId,
      name: groupName,
      category: scopeKey,
      matchedSheets: groupSheets,
      commonFields,
      differenceFields,
      recommendedTemplateId: '',
      recommendedTemplateName: SCOPE_CONFIG[scopeKey]?.label || templateType,
      matchScore: Math.round(matchScore * 100),
      templateType
    })
  }

  return groups
}

async function loadTemplates(): Promise<Array<{ id: string; name: string; templateType: string; businessScope: string }>> {
  try {
    const res = await templatePreviewApi.listTemplates()
    if (res?.success && Array.isArray(res.templates)) {
      return res.templates
        .filter((t: any) => t?.category === 'excel')
        .map((t: any) => ({
          id: t.id,
          name: t.name || t.template_name || '未命名模板',
          templateType: t.template_type || '',
          businessScope: t.business_scope || ''
        }))
    }
  } catch (e) {
    console.error('加载模板列表失败:', e)
  }
  return []
}

export function useBatchAnalyze() {
  const store = useBatchAnalyzeStore()
  const xlsxLibPromise = ref<Promise<any> | null>(null)

  const loadXlsx = async () => {
    if (!xlsxLibPromise.value) {
      xlsxLibPromise.value = import('xlsx')
    }
    return xlsxLibPromise.value
  }

  async function readWorkbookSheets(file: File): Promise<{ sheetNames: string[]; sheetsData: SheetInfo[] }> {
    const XLSX = await loadXlsx()
    const buffer = await file.arrayBuffer()
    const workbook = XLSX.read(buffer, { type: 'array' })

    const sheetNames = Array.isArray(workbook.SheetNames) ? workbook.SheetNames : []
    const sheetsData: SheetInfo[] = []

    for (let i = 0; i < sheetNames.length; i++) {
      const sheetName = sheetNames[i]
      const sheet = workbook.Sheets[sheetName]

      if (!sheet || sheet['!ref'] == null) continue

      const jsonData = XLSX.utils.sheet_to_json(sheet, { header: 1 }) as any[][]
      if (!jsonData || jsonData.length === 0) continue

      const headerRow = jsonData[0] || []
      const fields: string[] = headerRow
        .map((cell: any) => String(cell ?? '').trim())
        .filter((cell: string) => cell.length > 0)

      const rowCount = Math.max(0, jsonData.length - 1)

      const sampleRows: Record<string, any>[] = []
      for (let r = 1; r < Math.min(jsonData.length, 4); r++) {
        const row: Record<string, any> = {}
        for (let c = 0; c < headerRow.length; c++) {
          row[headerRow[c]] = jsonData[r][c] ?? ''
        }
        sampleRows.push(row)
      }

      sheetsData.push({
        fileName: file.name,
        sheetName,
        sheetIndex: i + 1,
        fields,
        rowCount,
        sampleRows
      })
    }

    return { sheetNames, sheetsData }
  }

  async function extractAllSheets(files: File[]): Promise<SheetInfo[]> {
    store.setPhase('extracting')
    store.updateProgress({ totalFiles: files.length, processedFiles: 0, totalSheets: 0 })

    const allSheets: SheetInfo[] = []

    for (let i = 0; i < files.length; i++) {
      const file = files[i]
      store.updateProgress({
        processedFiles: i + 1,
        currentFileName: file.name,
        progress: Math.round(((i + 1) / files.length) * 50)
      })

      try {
        const { sheetsData } = await readWorkbookSheets(file)
        store.updateProgress({ totalSheets: allSheets.length + sheetsData.length })
        allSheets.push(...sheetsData)
      } catch (e) {
        console.error(`读取文件 ${file.name} 失败:`, e)
      }
    }

    store.addExtractedSheets(allSheets)
    return allSheets
  }

  async function analyzeAndGroup(): Promise<SheetGroup[]> {
    store.setPhase('grouping')
    store.updateProgress({ progress: 60 })

    const sheets = store.extractedSheets
    const groups = groupSheetsBySimilarity(sheets)

    store.updateProgress({ progress: 75 })
    store.setGroups(groups)

    store.setPhase('matching')
    store.updateProgress({ progress: 80 })

    const templates = await loadTemplates()

    for (const group of groups) {
      const matchingTemplates = templates.filter(t =>
        t.businessScope === group.category || t.templateType === group.templateType
      )

      if (matchingTemplates.length > 0) {
        group.recommendedTemplateId = matchingTemplates[0].id
        group.recommendedTemplateName = matchingTemplates[0].name
      }
    }

    store.updateProgress({ progress: 100 })
    store.setPhase('done')

    return groups
  }

  async function startBatchAnalyze(fileList: File[]): Promise<SheetGroup[]> {
    store.startNewSession()

    const excelFiles = fileList.filter(f => /\.(xlsx?)$/i.test(f.name))
    if (excelFiles.length === 0) {
      store.setError('没有找到 Excel 文件')
      return []
    }

    await extractAllSheets(excelFiles)
    const groups = await analyzeAndGroup()

    return groups
  }

  async function extractGridForSheet(file: File, sheetName: string): Promise<any> {
    try {
      const formData = new FormData()
      formData.append('file', file)
      formData.append('sheet_name', sheetName)

      const res = await templatePreviewApi.extractGrid(formData)
      return res
    } catch (e) {
      console.error('提取网格失败:', e)
      return null
    }
  }

  return {
    store,
    startBatchAnalyze,
    extractAllSheets,
    analyzeAndGroup,
    extractGridForSheet,
    calculateFieldSimilarity,
    groupSheetsBySimilarity,
    inferTemplateTypeByFields,
    readWorkbookSheets
  }
}
