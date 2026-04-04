<template>
  <div class="page-view" id="view-business-docking">
    <div class="page-content">
      <div class="page-header">
        <h2>业务对接</h2>
        <p class="muted">上传旧业务 Excel，先校对 sheet 列表与网格映射效果</p>
      </div>

      <div class="dock-card">
        <div class="dock-card-title">Excel 业务网格映射</div>
        <div class="dock-actions">
          <input type="file" accept=".xlsx,.xls" @change="onFileSelected">
          <button
            type="button"
            class="btn btn-sm btn-primary"
            :disabled="!selectedFile || extracting"
            @click="extractGrid()"
          >
            {{ extracting ? '提取中...' : '上传并提取' }}
          </button>
        </div>

        <div class="sheet-selector-row">
          <label for="sheet-select">Sheet 列表</label>
          <select
            id="sheet-select"
            class="form-control"
            :disabled="!sheetNames.length || extracting"
            v-model="selectedSheetName"
            @change="onSheetChange"
          >
            <option value="" disabled>请选择 Sheet</option>
            <option v-for="sheet in sheetNames" :key="sheet" :value="sheet">{{ sheet }}</option>
          </select>
        </div>

        <div v-if="extractResult" class="dock-meta muted">
          文件：{{ extractResult.template_name || fileDisplayName }} |
          当前 Sheet：{{ currentSheetDisplay }} |
          字段：{{ (extractResult.fields || []).length }} 项
        </div>
      </div>

      <div class="dock-results-stack" data-tutorial-anchor="business-dock-results">
        <div v-if="!extractResult" class="dock-results-placeholder muted">
          上传并提取 Excel 后，此处将出现「字段列表」「网格预览」与「保留模板」区域。
        </div>
        <div v-if="extractResult" class="result-layout">
        <div class="field-panel">
          <div class="panel-title">字段列表</div>
          <div v-if="!extractResult.fields || extractResult.fields.length === 0" class="muted">未识别到字段</div>
          <ul v-else class="field-list">
            <li v-for="(field, index) in extractResult.fields" :key="field.label + '-' + index">
              <span class="field-index">{{ index + 1 }}.</span>
              <span>{{ field.label || field.name || '未命名字段' }}</span>
            </li>
          </ul>
        </div>
        <div class="preview-panel">
          <div class="panel-title">网格预览</div>
          <ExcelPreview
            :fields="extractResult.fields || []"
            :sample-rows="extractResult?.preview_data?.sample_rows || []"
            :title="currentSheetDisplay + ' 真实网格'"
            :grid-data="extractResult?.preview_data?.grid_preview || null"
            :rows="10"
            :columns="8"
          />
        </div>
      </div>

      <div v-if="extractResult" class="save-card">
        <div class="panel-title">保留模板</div>
        <div class="save-mode-row">
          <label>
            <input type="radio" value="create" v-model="saveMode">
            新增模板
          </label>
          <label>
            <input type="radio" value="replace" v-model="saveMode">
            替换同业务范围模板
          </label>
        </div>

        <div class="save-scope muted">
          当前识别业务范围：{{ currentScopeLabel }}（{{ currentScopeKey || '未匹配' }}）
        </div>
        <div v-if="currentScopeKey && currentMissingTerms.length" class="save-warning">
          必填字段未匹配：{{ currentMissingTerms.join('、') }}
        </div>
        <div v-else-if="!currentScopeKey" class="save-warning">
          未识别到完整业务范围，暂不允许保存模板。
        </div>

        <div v-if="saveMode === 'create'" class="save-field-row">
          <label for="save-template-name">模板名称</label>
          <input
            id="save-template-name"
            v-model="saveTemplateName"
            class="form-control"
            type="text"
            placeholder="请输入新模板名称"
          >
        </div>

        <div v-else class="save-field-row">
          <label for="replace-target-select">选择要替换的模板（同业务范围）</label>
          <select
            id="replace-target-select"
            class="form-control"
            v-model="replaceTargetId"
            :disabled="savingTemplate || replaceCandidates.length === 0"
          >
            <option value="" disabled>请选择模板</option>
            <option v-for="item in replaceCandidates" :key="item.id" :value="item.id">
              {{ replaceCandidateLabel(item) }}
            </option>
          </select>
          <div v-if="replaceCandidates.length === 0" class="muted" style="margin-top:6px;font-size:12px;">
            当前范围暂无可替换模板，请先使用“新增模板”创建。
          </div>
        </div>

        <div class="save-actions">
          <button
            type="button"
            class="btn btn-sm btn-primary"
            :disabled="!canSaveTemplate || savingTemplate"
            @click="saveCurrentAsTemplate"
          >
            {{ savingTemplate ? '保存中...' : (saveMode === 'create' ? '新增模板' : '替换模板') }}
          </button>
          <button type="button" class="btn btn-sm btn-secondary" @click="goTemplatePreview">
            前往模板预览
          </button>
        </div>

        <div v-if="saveResultMessage" class="muted" style="margin-top:8px;font-size:12px;">
          {{ saveResultMessage }}
        </div>
      </div>
      </div>

      <div class="dock-card dock-batch-card">
        <div class="dock-card-title">智能批量上传</div>
        <p class="muted batch-upload-lead">
          选择文件夹后，可「批量提取」：按顺序对每个 Excel 调用与单文件相同的网格提取接口，最后一项成功结果会留在下方预览区。
        </p>
        <div class="dock-actions batch-upload-actions">
          <label class="btn btn-sm btn-secondary batch-folder-btn">
            <input
              ref="batchFolderInputRef"
              type="file"
              class="batch-folder-input"
              webkitdirectory
              directory
              multiple
              @change="onBatchFolderSelected"
            >
            选择文件夹
          </label>
          <button
            type="button"
            class="btn btn-sm btn-primary batch-extract-btn"
            :disabled="!batchExcelFiles.length || extracting || batchExtracting"
            @click="runBatchExtract"
          >
            <svg class="folder-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M22 19a2 2 0 01-2 2H4a2 2 0 01-2-2V5a2 2 0 012-2h5l2 3h9a2 2 0 012 2z"/>
            </svg>
            {{ batchExtracting ? '批量提取中…' : '批量提取' }}
          </button>
        </div>

        <div
          class="batch-drop-zone"
          :class="{ 'drop-zone-active': isDragging }"
          @click="openBatchFolderPicker"
          @dragover.prevent="onDragOver"
          @dragleave="onDragLeave"
          @drop.prevent="onDrop"
        >
          <svg class="drop-zone-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M22 19a2 2 0 01-2 2H4a2 2 0 01-2-2V5a2 2 0 012-2h5l2 3h9a2 2 0 012 2z"/>
            <line x1="12" y1="11" x2="12" y2="17"/>
            <line x1="9" y1="14" x2="15" y2="14"/>
          </svg>
          <span class="drop-zone-text">拖拽文件夹到此处</span>
          <span class="drop-zone-hint muted">或点击选择文件夹</span>
        </div>
        <p v-if="batchFolderHint" class="muted batch-upload-hint">{{ batchFolderHint }}</p>
        <ul v-if="batchExcelPreview.length" class="batch-file-preview muted">
          <li v-for="(name, i) in batchExcelPreview" :key="i">{{ name }}</li>
        </ul>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'

/** 批量文件夹内视为 Excel 的文件名（供后续逻辑复用） */
function isExcelFileName(name) {
  return /\.xlsx?$/i.test(String(name || ''))
}
import { useRouter } from 'vue-router'
import templatePreviewApi from '../api/templatePreview'
import ExcelPreview from '../components/template/ExcelPreview.vue'
import templateScopeRules from '../shared/templateScopeRules.json'
import { stripGridPreviewData, stripSampleRowsKeepTemplateShape } from '@/shared/templatePreviewSanitize.js'

const selectedFile = ref(null)
const fileDisplayName = ref('')
const extracting = ref(false)
const extractResult = ref(null)
const sheetNames = ref([])
const selectedSheetName = ref('')
const saveMode = ref('create')
const saveTemplateName = ref('')
const replaceTargetId = ref('')
const replaceCandidates = ref([])
const savingTemplate = ref(false)
const saveResultMessage = ref('')
const router = useRouter()

const batchFolderInputRef = ref(null)
const batchFolderHint = ref('')
const batchExcelPreview = ref([])
/** @type {import('vue').Ref<File[]>} */
const batchExcelFiles = ref([])
const batchExtracting = ref(false)
const isDragging = ref(false)

function onDragOver(e) {
  isDragging.value = true
}

function onDragLeave(e) {
  isDragging.value = false
}

function openBatchFolderPicker() {
  batchFolderInputRef.value?.click()
}

function onDrop(e) {
  isDragging.value = false
  const items = e?.dataTransfer?.items
  if (!items?.length) return

  const files = []
  const promises = []

  for (const item of items) {
    if (item.kind === 'file') {
      const entry = item.webkitGetAsEntry?.()
      if (entry) {
        promises.push(traverseEntry(entry, files))
      } else {
        const file = item.getAsFile()
        if (file) files.push(file)
      }
    }
  }

  Promise.all(promises).then(() => {
    if (files.length > 0) {
      processDroppedFiles(files)
    }
  })
}

function traverseEntry(entry, files) {
  return new Promise((resolve) => {
    if (entry.isFile) {
      entry.file((file) => {
        files.push(file)
        resolve()
      })
    } else if (entry.isDirectory) {
      const reader = entry.createReader()
      const readEntries = () => {
        reader.readEntries(async (entries) => {
          if (entries.length === 0) {
            resolve()
            return
          }
          const subPromises = entries.map((e) => traverseEntry(e, files))
          await Promise.all(subPromises)
          resolve()
        })
      }
      readEntries()
    } else {
      resolve()
    }
  })
}

function processDroppedFiles(files) {
  const excels = files.filter((f) => isExcelFileName(f.name))
  if (!excels.length) {
    batchFolderHint.value = '未找到 Excel 文件，请拖入包含 .xls 或 .xlsx 文件的文件夹'
    batchExcelPreview.value = []
    batchExcelFiles.value = []
    return
  }
  batchExcelFiles.value = excels
  batchFolderHint.value = `已拖入 ${files.length} 个文件，其中 ${excels.length} 个为 .xls / .xlsx。可点击「批量提取」依次解析。`
  batchExcelPreview.value = excels.slice(0, 12).map((f) => f.name)
  if (excels.length > 12) {
    batchFolderHint.value += ` 以下仅展示前 12 个文件名。`
  }
}

/**
 * 智能批量上传：文件夹选择，保留 File 列表供批量提取
 * @param {Event} e
 */
function onBatchFolderSelected(e) {
  const input = e?.target
  const files = input?.files
  if (!files?.length) {
    batchFolderHint.value = ''
    batchExcelPreview.value = []
    batchExcelFiles.value = []
    return
  }
  const list = Array.from(files)
  const excels = list.filter((f) => isExcelFileName(f.name))
  batchExcelFiles.value = excels
  batchFolderHint.value = `已选择 ${list.length} 个文件，其中 ${excels.length} 个为 .xls / .xlsx。可点击「批量提取」依次解析。`
  batchExcelPreview.value = excels.slice(0, 12).map((f) => f.name)
  if (excels.length > 12) {
    batchFolderHint.value += ` 以下仅展示前 12 个文件名。`
  }
  if (input) input.value = ''
}

/**
 * 智能批量上传：读取所有 Excel 的 Sheet 信息，然后跳转到批量分析页面
 */
async function runBatchExtract() {
  const files = batchExcelFiles.value
  if (!files.length || batchExtracting.value) return

  batchExtracting.value = true
  batchFolderHint.value = '正在读取文件信息...'

  try {
    const { useBatchAnalyzeStore } = await import('../stores/batchAnalyze')
    const { useBatchAnalyze } = await import('../composables/useBatchAnalyze')
    const { readWorkbookSheets } = useBatchAnalyze()
    const batchStore = useBatchAnalyzeStore()
    batchStore.reset()
    batchStore.updateProgress({ totalFiles: files.length })

    for (let i = 0; i < files.length; i++) {
      const file = files[i]
      batchStore.updateProgress({
        processedFiles: i + 1,
        currentFileName: file.name,
        progress: Math.round(((i + 1) / files.length) * 100)
      })

      try {
        const { sheetsData } = await readWorkbookSheets(file)
        batchStore.addExtractedSheets(sheetsData)
        batchStore.updateProgress({ totalSheets: batchStore.extractedSheets.length })
      } catch (e) {
        console.error(`读取文件 ${file.name} 失败:`, e)
      }
    }

    batchFolderHint.value = `读取完成，共 ${batchStore.extractedSheets.length} 个工作表`

    setTimeout(() => {
      router.push({ name: 'batch-analyze' })
    }, 500)
  } finally {
    batchExtracting.value = false
  }
}

let xlsxLibPromise = null
const loadXlsx = async () => {
  if (!xlsxLibPromise) {
    xlsxLibPromise = import('xlsx')
  }
  return xlsxLibPromise
}

const scopeConfig = templateScopeRules
const TERM_EQUIVALENTS = {
  '产品型号': ['产品型号', '型号', '产品编码'],
  '型号': ['型号', '产品型号', '产品编码'],
  '规格': ['规格', '规格型号', '规格/kg'],
  '规格型号': ['规格型号', '规格', '规格/kg'],
  '价格': ['价格', '单价', '单价/元'],
  '单价': ['单价', '价格', '单价/元'],
  '金额': ['金额', '金额/元', '金额合计', '总金额'],
  '数量': ['数量', '数量(kg)', '数量/kg', '数量/件', '数量/桶', '库存数量'],
  '电话': ['电话', '联系电话', '手机号'],
  '购买单位': ['购买单位', '单位', '单位名称', '客户名称', '厂名'],
  '客户名称': ['客户名称', '购买单位', '单位名称', '厂名']
}

const currentSheetDisplay = computed(() => {
  return (
    selectedSheetName.value ||
    extractResult.value?.preview_data?.selected_sheet_name ||
    extractResult.value?.preview_data?.sheet_name ||
    'Sheet'
  )
})

const matchedScopeKeys = computed(() => inferMatchedScopesFromCurrentResult().map(item => item.scopeKey))
const currentScopeKey = computed(() => matchedScopeKeys.value[0] || '')

const currentScopeLabel = computed(() => {
  const key = currentScopeKey.value
  if (!key || !scopeConfig[key]) return '未匹配'
  return scopeConfig[key].label || key
})

const currentRequiredTerms = computed(() => {
  const key = currentScopeKey.value
  if (!key || !scopeConfig[key]) return []
  return Array.isArray(scopeConfig[key].requiredTerms) ? scopeConfig[key].requiredTerms : []
})

const currentMissingTerms = computed(() => {
  if (!currentScopeKey.value) return []
  const termSet = collectCurrentTerms()
  return currentRequiredTerms.value.filter(term => !hasEquivalentTerm(termSet, term))
})

const canSaveTemplate = computed(() => {
  if (!extractResult.value) return false
  if (saveMode.value === 'create') {
    return Boolean(saveTemplateName.value.trim())
  }
  if (!currentScopeKey.value || currentMissingTerms.value.length > 0) return false
  return Boolean(replaceTargetId.value)
})

async function onFileSelected(event) {
  const file = event?.target?.files?.[0] || null
  selectedFile.value = file
  fileDisplayName.value = file?.name || ''
  extractResult.value = null
  sheetNames.value = []
  selectedSheetName.value = ''
  saveMode.value = 'create'
  saveTemplateName.value = ''
  replaceTargetId.value = ''
  replaceCandidates.value = []
  saveResultMessage.value = ''

  if (file) {
    const localSheetNames = await readWorkbookSheetNames(file)
    if (localSheetNames.length > 0) {
      sheetNames.value = localSheetNames
      selectedSheetName.value = localSheetNames[0]
    }
  }
}

function normalizeSheetNames(result) {
  const names = result?.preview_data?.sheet_names
  if (Array.isArray(names) && names.length > 0) {
    return names
  }
  const fallback = result?.preview_data?.sheet_name
  return fallback ? [fallback] : []
}

function mergeSheetNames(primary, secondary) {
  const merged = []
  for (const name of [...(primary || []), ...(secondary || [])]) {
    const text = String(name || '').trim()
    if (!text) continue
    if (!merged.includes(text)) {
      merged.push(text)
    }
  }
  return merged
}

async function readWorkbookSheetNames(file) {
  try {
    const buffer = await file.arrayBuffer()
    const XLSX = await loadXlsx()
    const workbook = XLSX.read(buffer, { type: 'array' })
    return Array.isArray(workbook.SheetNames) ? workbook.SheetNames : []
  } catch (_err) {
    return []
  }
}

/**
 * @param {File} file
 * @param {string} preferredSheetName
 * @param {{ showAlert?: boolean, updateUi?: boolean }} opts
 */
async function runExtractGrid(file, preferredSheetName = '', opts = {}) {
  const { showAlert = true, updateUi = true } = opts
  if (!file) {
    if (showAlert) alert('请先选择 Excel 文件')
    throw new Error('未选择文件')
  }

  extracting.value = true
  try {
    const formData = new FormData()
    formData.append('file', file)
    if (preferredSheetName) {
      formData.append('sheet_name', preferredSheetName)
    }

    const res = await templatePreviewApi.extractGrid(formData)
    if (!res?.success) {
      throw new Error(res?.message || '提取失败')
    }

    if (updateUi) {
      extractResult.value = res
      const namesFromApi = normalizeSheetNames(res)
      const mergedNames = mergeSheetNames(sheetNames.value, namesFromApi)
      sheetNames.value = mergedNames

      const responseSelectedSheet =
        res?.preview_data?.selected_sheet_name ||
        res?.preview_data?.sheet_name ||
        ''
      if (responseSelectedSheet) {
        selectedSheetName.value = responseSelectedSheet
      } else if (mergedNames.length > 0) {
        selectedSheetName.value = mergedNames[0]
      } else {
        selectedSheetName.value = ''
      }

      initializeTemplateSaveState()
      await loadReplaceCandidates()
    }
    return res
  } catch (err) {
    if (showAlert) {
      alert('网格提取失败：' + (err?.message || '未知错误'))
    }
    throw err
  } finally {
    extracting.value = false
  }
}

async function extractGrid(preferredSheetName = '') {
  if (!selectedFile.value) {
    alert('请先选择 Excel 文件')
    return
  }
  await runExtractGrid(selectedFile.value, preferredSheetName, {
    showAlert: true,
    updateUi: true,
  })
}

function onSheetChange() {
  if (!selectedSheetName.value) return
  extractGrid(selectedSheetName.value)
}

function normalizeTerm(value) {
  return String(value || '').replace(/\s+/g, '').trim().toLowerCase()
}

function getEquivalentNormalizedTerms(term) {
  const key = String(term || '').trim()
  const aliases = TERM_EQUIVALENTS[key] || [key]
  const normalized = aliases
    .map(item => normalizeTerm(item))
    .filter(Boolean)
  const targetNormalized = normalizeTerm(key)
  if (targetNormalized && !normalized.includes(targetNormalized)) {
    normalized.push(targetNormalized)
  }
  return normalized
}

function hasEquivalentTerm(termSet, requiredTerm) {
  if (!(termSet instanceof Set)) return false
  const candidates = getEquivalentNormalizedTerms(requiredTerm)
  return candidates.some(candidate => termSet.has(candidate))
}

function collectCurrentTerms() {
  const termSet = new Set()
  const fields = extractResult.value?.fields || []
  for (const field of fields) {
    termSet.add(normalizeTerm(field?.label))
    termSet.add(normalizeTerm(field?.name))
  }
  const sampleRows = extractResult.value?.preview_data?.sample_rows || []
  for (const row of sampleRows) {
    for (const key of Object.keys(row || {})) {
      termSet.add(normalizeTerm(key))
      termSet.add(normalizeTerm(row?.[key]))
    }
  }
  return termSet
}

function collectTermsFromFieldsAndSampleRows(fields, sampleRows) {
  const termSet = new Set()
  for (const field of fields || []) {
    termSet.add(normalizeTerm(field?.label))
    termSet.add(normalizeTerm(field?.name))
    termSet.add(normalizeTerm(field?.value))
  }
  for (const row of sampleRows || []) {
    for (const key of Object.keys(row || {})) {
      termSet.add(normalizeTerm(key))
      termSet.add(normalizeTerm(row?.[key]))
    }
  }
  return termSet
}

function inferMatchedScopesFromCurrentResult() {
  const termSet = collectCurrentTerms()
  const matchedScopes = []

  for (const [scopeKey, meta] of Object.entries(scopeConfig || {})) {
    const requiredTerms = Array.isArray(meta?.requiredTerms) ? meta.requiredTerms : []
    const matched = requiredTerms.length > 0 && requiredTerms.every(term => hasEquivalentTerm(termSet, term))
    if (matched) {
      matchedScopes.push({ scopeKey, requiredCount: requiredTerms.length })
    }
  }

  if (!matchedScopes.length) return []
  // 命中多个范围时优先选择“必备词条更多”的范围（通常更具体）。
  matchedScopes.sort((a, b) => b.requiredCount - a.requiredCount)
  return matchedScopes
}

function getTemplateTypeByScope(scopeKey) {
  return scopeConfig?.[scopeKey]?.templateType || 'Excel'
}

function inferScopeByTemplateType(templateType) {
  const text = String(templateType || '').trim()
  if (!text) return ''
  for (const [scopeKey, meta] of Object.entries(scopeConfig || {})) {
    if (String(meta?.templateType || '').trim() === text) {
      return scopeKey
    }
  }
  return ''
}

function enrichFieldsForScope(fields, sampleRows, scopeKey) {
  const safeFields = Array.isArray(fields) ? [...fields] : []
  const requiredTerms = Array.isArray(scopeConfig?.[scopeKey]?.requiredTerms) ? scopeConfig[scopeKey].requiredTerms : []
  if (!requiredTerms.length) return safeFields

  const termSet = collectTermsFromFieldsAndSampleRows(safeFields, sampleRows)
  for (const term of requiredTerms) {
    const normalized = normalizeTerm(term)
    if (!normalized) continue
    if (termSet.has(normalized)) continue
    if (!hasEquivalentTerm(termSet, term)) continue
    // 补齐规范词条，兼容后端严格“字面匹配”校验。
    safeFields.push({ label: term, value: '', type: 'dynamic' })
    termSet.add(normalized)
  }
  return safeFields
}

function initializeTemplateSaveState() {
  const scopeKey = currentScopeKey.value || 'orders'
  const prefix = scopeConfig?.[scopeKey]?.label || '业务'
  saveTemplateName.value = `${prefix}模板`
  replaceTargetId.value = ''
  saveResultMessage.value = ''
}

async function loadReplaceCandidates() {
  const scopeKey = String(currentScopeKey.value || '').trim()
  if (!scopeKey) {
    replaceCandidates.value = []
    return
  }
  try {
    const res = await templatePreviewApi.listTemplates()
    if (!res?.success || !Array.isArray(res.templates)) {
      replaceCandidates.value = []
      return
    }
    const scoped = res.templates
      .filter(item => {
        if (item?.category !== 'excel' || item?.virtual) return false
        const id = String(item?.id || '').trim()
        const source = String(item?.source || '').trim()
        return id.startsWith('db:') || source === 'system-default'
      })
      .map(item => {
        const scope = String(item?.business_scope || '').trim() || inferScopeByTemplateType(item?.template_type)
        const source = String(item?.source || '').trim()
        const hasFilePath = !!String(item?.file_path || item?.path || '').trim()
        return {
          id: item.id,
          name: item.name || item.template_name || '未命名模板',
          templateType: item.template_type || '',
          businessScope: scope,
          source,
          hasFilePath,
          fields: Array.isArray(item?.fields) ? item.fields : [],
          previewData: item?.preview_data || {}
        }
      })
      .filter(item => item.businessScope === scopeKey)
    const validated = []
    for (const item of scoped) {
      let fields = Array.isArray(item.fields) ? item.fields : []
      let sampleRows = Array.isArray(item?.previewData?.sample_rows) ? item.previewData.sample_rows : []
      const requiredTerms = Array.isArray(scopeConfig?.[item.businessScope]?.requiredTerms) ? scopeConfig[item.businessScope].requiredTerms : []
      try {
        // system-default 模板无 detail 文件路径，直接使用 list 返回的数据。
        if (item.source !== 'system-default') {
          const detailRes = await templatePreviewApi.getTemplateDetail(item.id)
          const detail = detailRes?.template || {}
          fields = Array.isArray(detail.fields) ? detail.fields : fields
          sampleRows = Array.isArray(detail?.preview_data?.sample_rows) ? detail.preview_data.sample_rows : sampleRows
        }
        const termSet = new Set()
        for (const field of fields) {
          termSet.add(normalizeTerm(field?.label))
          termSet.add(normalizeTerm(field?.name))
        }
        for (const row of sampleRows) {
          for (const key of Object.keys(row || {})) {
            termSet.add(normalizeTerm(key))
          }
        }
        const ok = requiredTerms.length > 0 && requiredTerms.every(term => hasEquivalentTerm(termSet, term))
        if (ok) validated.push(item)
      } catch (_e) {
        // 详情异常时兜底使用 list 数据再校验一次，避免系统默认模板被误过滤。
        try {
          const termSet = new Set()
          for (const field of fields) {
            termSet.add(normalizeTerm(field?.label))
            termSet.add(normalizeTerm(field?.name))
          }
          for (const row of sampleRows) {
            for (const key of Object.keys(row || {})) {
              termSet.add(normalizeTerm(key))
            }
          }
          const ok = requiredTerms.length > 0 && requiredTerms.every(term => hasEquivalentTerm(termSet, term))
          if (ok) validated.push(item)
        } catch (_ignore) {
          // ignore
        }
      }
    }
    // 候选去重：同名同类型同范围只保留一条，优先有文件路径且可直接更新(db:*)的模板。
    const normalizedValidated = validated
      .map(item => {
        const id = String(item?.id || '').trim()
        const source = String(item?.source || '').trim()
        const hasFilePath = !!item?.hasFilePath
        const priority = (
          (id.startsWith('db:') ? 200 : 0)
          + (hasFilePath ? 20 : 0)
          + (source === 'system-default' ? 0 : 5)
        )
        return {
          ...item,
          id,
          source,
          hasFilePath,
          dedupKey: `${String(item?.name || '').trim()}__${String(item?.templateType || '').trim()}__${String(item?.businessScope || '').trim()}`,
          priority
        }
      })
      .sort((a, b) => {
        if (a.priority !== b.priority) return b.priority - a.priority
        return b.id.localeCompare(a.id)
      })

    const deduped = []
    const seen = new Set()
    for (const item of normalizedValidated) {
      if (seen.has(item.dedupKey)) continue
      seen.add(item.dedupKey)
      deduped.push(item)
    }

    replaceCandidates.value = deduped
    replaceTargetId.value = replaceCandidates.value.length ? replaceCandidates.value[0].id : ''
  } catch (_err) {
    replaceCandidates.value = []
  }
}

function replaceCandidateLabel(item) {
  const name = String(item?.name || '未命名模板').trim()
  const templateType = String(item?.templateType || 'Excel').trim() || 'Excel'
  const source = String(item?.source || '').trim()
  if (source === 'system-default') {
    return `${name}（${templateType}）[系统默认]`
  }
  if (item?.hasFilePath) {
    return `${name}（${templateType}）[已绑定文件]`
  }
  return `${name}（${templateType}）[未绑定文件]`
}

function buildTemplatePayload(scopeOverride = '') {
  const scopeKey = String(scopeOverride || currentScopeKey.value || '').trim()
  const sampleRowsRaw = extractResult.value?.preview_data?.sample_rows || []
  const gridPreviewRaw = extractResult.value?.preview_data?.grid_preview || null
  const normalizedFields = scopeKey
    ? enrichFieldsForScope(extractResult.value?.fields || [], sampleRowsRaw, scopeKey)
    : (Array.isArray(extractResult.value?.fields) ? [...extractResult.value.fields] : [])
  const strippedSampleRows = stripSampleRowsKeepTemplateShape(sampleRowsRaw, normalizedFields)
  const strippedGridPreview = stripGridPreviewData(gridPreviewRaw, sampleRowsRaw)
  const resolvedTemplateType = scopeKey
    ? getTemplateTypeByScope(scopeKey)
    : 'Excel'
  const templateFilePath = String(
    extractResult.value?.file_path
    || extractResult.value?.preview_data?.file_path
    || ''
  ).trim()
  return {
    category: 'excel',
    template_type: resolvedTemplateType,
    business_scope: scopeKey || '',
    file_path: templateFilePath || undefined,
    fields: normalizedFields,
    preview_data: {
      sample_rows: strippedSampleRows,
      grid_preview: strippedGridPreview,
      sheet_name: extractResult.value?.preview_data?.sheet_name || selectedSheetName.value || '',
      selected_sheet_name: selectedSheetName.value || extractResult.value?.preview_data?.selected_sheet_name || '',
      sheet_names: sheetNames.value || [],
      file_path: templateFilePath || ''
    },
    source: 'business-docking'
  }
}

function hasBoundTemplateFile() {
  const path = String(
    extractResult.value?.file_path
    || extractResult.value?.preview_data?.file_path
    || ''
  ).trim()
  return !!path
}

async function saveCurrentAsTemplate() {
  if (!canSaveTemplate.value || savingTemplate.value) return
  if (saveMode.value === 'replace' && (!currentScopeKey.value || currentMissingTerms.value.length > 0)) {
    saveResultMessage.value = `保存失败：必填字段未匹配（${currentMissingTerms.value.join('、') || '业务范围未识别'}）`
    return
  }
  if (!hasBoundTemplateFile()) {
    saveResultMessage.value = '保存失败：未获取到上传模板文件路径，请重新上传并提取后再保存'
    return
  }
  savingTemplate.value = true
  saveResultMessage.value = ''
  try {
    let res
    if (saveMode.value === 'create') {
      const createScope = currentScopeKey.value && currentMissingTerms.value.length === 0
        ? String(currentScopeKey.value).trim()
        : ''
      const basePayload = buildTemplatePayload(createScope)
      res = await templatePreviewApi.createTemplateFromGrid({
        ...basePayload,
        name: saveTemplateName.value.trim()
      })
    } else {
      const targetId = String(replaceTargetId.value || '').trim()
      const target = replaceCandidates.value.find(item => String(item?.id || '').trim() === targetId)
      const targetName = String(target?.name || '').trim()
      const targetScope = String(target?.businessScope || currentScopeKey.value || '').trim()
      const replacePayload = buildTemplatePayload(targetScope || currentScopeKey.value)
      if (targetId.startsWith('db:')) {
        res = await templatePreviewApi.replaceTemplateById({
          ...replacePayload,
          id: targetId,
          enforce_scope_match: true,
          replace_mode: true
        })
      } else if (targetId.startsWith('system-default:')) {
        // 系统默认模板不可直接 update，改为创建同范围替代模板。
        res = await templatePreviewApi.createTemplateFromGrid({
          ...replacePayload,
          name: targetName || saveTemplateName.value.trim() || `${currentScopeLabel.value}模板`,
          source: 'template-preview-replace'
        })
      } else {
        throw new Error('替换目标无效')
      }
    }
    if (!res?.success) {
      throw new Error(res?.message || '保存失败')
    }
    if (saveMode.value === 'create') {
      const hasScopedBusiness = currentScopeKey.value && currentMissingTerms.value.length === 0
      saveResultMessage.value = hasScopedBusiness
        ? '新增模板成功'
        : '新增模板成功（按通用 Excel 模板保存，未绑定业务范围）'
    } else {
      saveResultMessage.value = '替换模板成功'
    }
    await loadReplaceCandidates()
  } catch (err) {
    saveResultMessage.value = `保存失败：${err?.message || '未知错误'}`
  } finally {
    savingTemplate.value = false
  }
}

function goTemplatePreview() {
  const scope = String(currentScopeKey.value || '').trim()
  if (scope) {
    router.push({ path: '/template-preview', query: { scope } })
    return
  }
  router.push({ path: '/template-preview', query: { scope: 'orders' } })
}
</script>

<style scoped>
.dock-card {
  margin: 12px 0 16px;
  padding: 12px;
  border: 1px solid #d8e3ea;
  border-radius: 8px;
  background: #fbfdff;
}

.dock-card-title {
  font-size: 13px;
  font-weight: 600;
  color: #2f4f63;
  margin-bottom: 10px;
}

.dock-results-stack {
  margin-top: 4px;
}

.dock-results-placeholder {
  padding: 16px;
  min-height: 72px;
  border: 1px dashed #c5d4dc;
  border-radius: 8px;
  font-size: 13px;
  line-height: 1.5;
}

.dock-actions {
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
}

.sheet-selector-row {
  margin-top: 10px;
  max-width: 340px;
}

.sheet-selector-row label {
  display: block;
  margin-bottom: 6px;
  font-size: 12px;
  color: #445868;
}

.dock-meta {
  margin-top: 8px;
  font-size: 12px;
}

.result-layout {
  display: grid;
  grid-template-columns: 280px 1fr;
  gap: 14px;
  align-items: start;
}

.field-panel,
.preview-panel {
  border: 1px solid #e1e4e8;
  border-radius: 8px;
  background: #fff;
  padding: 12px;
}

.panel-title {
  font-size: 13px;
  font-weight: 600;
  color: #2f4f63;
  margin-bottom: 10px;
}

.field-list {
  margin: 0;
  padding: 0;
  list-style: none;
  display: grid;
  gap: 6px;
  max-height: 420px;
  overflow-y: auto;
}

.field-list li {
  font-size: 12px;
  color: #334155;
  line-height: 1.4;
}

.field-index {
  color: #64748b;
  margin-right: 4px;
}

.form-control {
  width: 100%;
  padding: 8px 10px;
  border: 1px solid #cfd8df;
  border-radius: 6px;
  font-size: 13px;
}

.btn {
  padding: 8px 16px;
  border: none;
  border-radius: 4px;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-sm {
  padding: 6px 12px;
  font-size: 13px;
}

.btn-primary {
  background: #42b983;
  color: white;
}

.btn-primary:hover {
  background: #359469;
}

.btn-primary:disabled {
  background: #a8d5c2;
  cursor: not-allowed;
}

.muted {
  color: #6c757d;
}

.save-card {
  margin-top: 14px;
  border: 1px solid #d8e3ea;
  border-radius: 8px;
  background: #fdfefe;
  padding: 12px;
}

.save-mode-row {
  display: flex;
  gap: 16px;
  margin-bottom: 10px;
  font-size: 13px;
  color: #334155;
}

.save-scope {
  margin-bottom: 10px;
  font-size: 12px;
}

.save-field-row {
  margin-bottom: 10px;
  max-width: 420px;
}

.save-field-row label {
  display: block;
  margin-bottom: 6px;
  font-size: 12px;
  color: #445868;
}

.save-actions {
  display: flex;
  gap: 8px;
  align-items: center;
}

.save-warning {
  margin-bottom: 10px;
  padding: 8px 10px;
  border: 1px solid #f5c6cb;
  border-radius: 6px;
  background: #fff5f5;
  color: #a94442;
  font-size: 12px;
}

.btn-secondary {
  background: #6c757d;
  color: white;
}

.btn-secondary:hover {
  background: #5a6268;
}

.dock-batch-card {
  margin-top: 20px;
  border-style: dashed;
  background: #fafcff;
}

.batch-upload-lead {
  margin: 0 0 12px;
  font-size: 13px;
  line-height: 1.5;
}

.batch-upload-actions {
  align-items: flex-start;
}

.batch-folder-btn {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  margin: 0;
  overflow: hidden;
}

.batch-folder-input {
  position: absolute;
  inset: 0;
  opacity: 0;
  cursor: pointer;
  font-size: 0;
  width: 100%;
  height: 100%;
}

.batch-upload-hint {
  margin: 10px 0 0;
  font-size: 12px;
  line-height: 1.5;
}

.batch-extract-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.folder-icon {
  width: 16px;
  height: 16px;
  flex-shrink: 0;
}

.batch-drop-zone {
  margin-top: 12px;
  padding: 24px 16px;
  border: 2px dashed #c5d4dc;
  border-radius: 8px;
  background: #fafcff;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.batch-drop-zone:hover {
  border-color: #42b983;
  background: #f0fdf7;
}

.batch-drop-zone.drop-zone-active {
  border-color: #42b983;
  background: #e8f8f0;
  box-shadow: 0 0 0 3px rgba(66, 185, 131, 0.15);
}

.drop-zone-icon {
  width: 32px;
  height: 32px;
  color: #6c757d;
}

.drop-zone-active .drop-zone-icon {
  color: #42b983;
}

.drop-zone-text {
  font-size: 13px;
  font-weight: 500;
  color: #495057;
}

.drop-zone-hint {
  font-size: 12px;
}

.batch-file-preview {
  margin: 8px 0 0;
  padding-left: 18px;
  font-size: 12px;
  line-height: 1.45;
  max-height: 160px;
  overflow-y: auto;
}
</style>
