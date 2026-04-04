import { defineStore } from 'pinia'
import { ref, computed, type Ref } from 'vue'

export interface SheetInfo {
  fileName: string
  sheetName: string
  sheetIndex: number
  fields: string[]
  rowCount: number
  sampleRows: Record<string, any>[]
  gridPreview?: { rows: any[][] }
  rawSheet?: any
  gridData?: any
}

export interface SheetGroup {
  id: string
  name: string
  category: string
  matchedSheets: SheetInfo[]
  commonFields: string[]
  differenceFields: string[]
  recommendedTemplateId: string
  recommendedTemplateName: string
  matchScore: number
  templateType: string
  extractStatus?: 'pending' | 'extracting' | 'done' | 'failed'
  extractError?: string
}

export interface BatchAnalyzeState {
  phase: 'idle' | 'extracting' | 'grouping' | 'matching' | 'done' | 'error'
  totalFiles: number
  processedFiles: number
  totalSheets: number
  currentFileName: string
  currentSheetName: string
  progress: number
  errorMessage: string
  extractedSheets: SheetInfo[]
  groups: SheetGroup[]
  selectedGroupId: string | null
  sessionId: string
  failedFiles: Array<{ fileName: string; error: string }>
}

export const useBatchAnalyzeStore = defineStore('batchAnalyze', () => {
  const phase = ref<BatchAnalyzeState['phase']>('idle')
  const totalFiles = ref(0)
  const processedFiles = ref(0)
  const totalSheets = ref(0)
  const currentFileName = ref('')
  const currentSheetName = ref('')
  const progress = ref(0)
  const errorMessage = ref('')
  const extractedSheets = ref<SheetInfo[]>([])
  const groups = ref<SheetGroup[]>([])
  const selectedGroupId = ref<string | null>(null)
  const sessionId = ref('')
  const failedFiles = ref<Array<{ fileName: string; error: string }>>([])

  const phaseLabel = computed(() => {
    switch (phase.value) {
      case 'idle': return '等待开始'
      case 'extracting': return '正在拆解文档'
      case 'grouping': return '正在分组'
      case 'matching': return '正在匹配模板'
      case 'done': return '分析完成'
      case 'error': return '发生错误'
      default: return ''
    }
  })

  const progressText = computed(() => {
    if (phase.value === 'extracting') {
      return `拆解中 (${processedFiles.value}/${totalFiles.value})：${currentFileName.value}`
    }
    if (phase.value === 'grouping') {
      return `分组中，共 ${totalSheets.value} 个工作表...`
    }
    if (phase.value === 'matching') {
      return '匹配模板中...'
    }
    if (phase.value === 'done') {
      return `完成！共 ${groups.value.length} 个分组`
    }
    return ''
  })

  const canStartAnalyze = computed(() => {
    return extractedSheets.value.length > 0 && phase.value === 'idle'
  })

  const selectedGroup = computed(() => {
    if (!selectedGroupId.value) return null
    return groups.value.find(g => g.id === selectedGroupId.value) || null
  })

  function reset() {
    phase.value = 'idle'
    totalFiles.value = 0
    processedFiles.value = 0
    totalSheets.value = 0
    currentFileName.value = ''
    currentSheetName.value = ''
    progress.value = 0
    errorMessage.value = ''
    extractedSheets.value = []
    groups.value = []
    selectedGroupId.value = null
    sessionId.value = ''
    failedFiles.value = []
  }

  function startNewSession() {
    reset()
    sessionId.value = Date.now().toString(36) + Math.random().toString(36).substr(2)
  }

  function addFailedFile(fileName: string, error: string) {
    failedFiles.value.push({ fileName, error })
  }

  function setPhase(newPhase: BatchAnalyzeState['phase']) {
    phase.value = newPhase
  }

  function updateProgress(update: Partial<{
    totalFiles: number
    processedFiles: number
    totalSheets: number
    currentFileName: string
    currentSheetName: string
    progress: number
  }>) {
    if (update.totalFiles !== undefined) totalFiles.value = update.totalFiles
    if (update.processedFiles !== undefined) processedFiles.value = update.processedFiles
    if (update.totalSheets !== undefined) totalSheets.value = update.totalSheets
    if (update.currentFileName !== undefined) currentFileName.value = update.currentFileName
    if (update.currentSheetName !== undefined) currentSheetName.value = update.currentSheetName
    if (update.progress !== undefined) progress.value = update.progress
  }

  function addExtractedSheets(sheets: SheetInfo[]) {
    extractedSheets.value.push(...sheets)
  }

  function setGroups(newGroups: SheetGroup[]) {
    groups.value = newGroups
  }

  function setError(message: string) {
    errorMessage.value = message
    phase.value = 'error'
  }

  function selectGroup(groupId: string | null) {
    selectedGroupId.value = groupId
  }

  function updateGroupTemplate(groupId: string, templateId: string, templateName: string, matchScore: number) {
    const group = groups.value.find(g => g.id === groupId)
    if (group) {
      group.recommendedTemplateId = templateId
      group.recommendedTemplateName = templateName
      group.matchScore = matchScore
    }
  }

  function updateSheetGridData(fileName: string, sheetName: string, gridData: any) {
    const sheet = extractedSheets.value.find(s => s.fileName === fileName && s.sheetName === sheetName)
    if (sheet) {
      sheet.gridData = gridData
    }
  }

  function updateGroupExtractStatus(groupId: string, status: SheetGroup['extractStatus'], error?: string) {
    const group = groups.value.find(g => g.id === groupId)
    if (group) {
      group.extractStatus = status
      if (error) group.extractError = error
    }
  }

  function updateGroupSheets(groupId: string, sheets: SheetInfo[]) {
    const group = groups.value.find(g => g.id === groupId)
    if (group) {
      group.matchedSheets = sheets
    }
  }

  return {
    phase,
    totalFiles,
    processedFiles,
    totalSheets,
    currentFileName,
    currentSheetName,
    progress,
    errorMessage,
    extractedSheets,
    groups,
    selectedGroupId,
    sessionId,
    failedFiles,
    phaseLabel,
    progressText,
    canStartAnalyze,
    selectedGroup,
    reset,
    startNewSession,
    setPhase,
    updateProgress,
    addExtractedSheets,
    setGroups,
    setError,
    selectGroup,
    updateGroupTemplate,
    updateSheetGridData,
    updateGroupExtractStatus,
    updateGroupSheets,
    addFailedFile
  }
})
