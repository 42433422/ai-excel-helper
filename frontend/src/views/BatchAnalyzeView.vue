<template>
  <div class="batch-analyze-view page-view">
    <div class="page-header">
      <h2>批量分析</h2>
      <p class="muted">自动拆解、分组并匹配模板</p>
    </div>

    <div v-if="store.phase === 'idle' && store.extractedSheets.length === 0" class="empty-state-card">
      <div class="empty-icon">📊</div>
      <div class="empty-title">暂无分析数据</div>
      <div class="empty-desc">请从「业务对接」页面选择文件夹进行批量上传</div>
      <button class="btn btn-primary" @click="goToBusinessDocking">前往业务对接</button>
    </div>

    <template v-else>
      <div class="progress-section">
        <div class="progress-header">
          <span class="progress-phase">{{ store.phaseLabel }}</span>
          <span class="progress-percent">{{ store.progress }}%</span>
        </div>
        <div class="progress-bar">
          <div
            class="progress-fill"
            :class="`phase-${store.phase}`"
            :style="{ width: store.progress + '%' }"
          ></div>
        </div>
        <div class="progress-detail muted">{{ store.progressText }}</div>
      </div>

      <div v-if="store.errorMessage" class="error-card">
        <span class="error-icon">❌</span>
        <span>{{ store.errorMessage }}</span>
        <button class="btn btn-sm btn-secondary" @click="retry">重试</button>
      </div>

      <div class="stats-row">
        <div class="stat-card">
          <div class="stat-value">{{ store.extractedSheets.length }}</div>
          <div class="stat-label">已拆解工作表</div>
        </div>
        <div class="stat-card">
          <div class="stat-value">{{ store.groups.length }}</div>
          <div class="stat-label">分组数量</div>
        </div>
        <div class="stat-card">
          <div class="stat-value">{{ matchedTemplatesCount }}</div>
          <div class="stat-label">已匹配模板</div>
        </div>
        <div v-if="store.failedFiles.length > 0" class="stat-card stat-warning">
          <div class="stat-value">{{ store.failedFiles.length }}</div>
          <div class="stat-label">读取失败</div>
        </div>
      </div>

      <div v-if="store.failedFiles.length > 0" class="failed-files-card">
        <div class="failed-files-header">
          <span class="failed-icon">⚠️</span>
          <span class="failed-title">以下文件读取失败</span>
          <button class="btn btn-xs btn-outline" @click="showFailedFiles = !showFailedFiles">
            {{ showFailedFiles ? '收起' : '展开' }}
          </button>
        </div>
        <div v-if="showFailedFiles" class="failed-files-list">
          <div
            v-for="(file, idx) in store.failedFiles"
            :key="idx"
            class="failed-file-item"
          >
            <span class="failed-file-name">{{ file.fileName }}</span>
            <span class="failed-file-error muted">{{ file.error }}</span>
          </div>
        </div>
      </div>

      <div v-if="store.groups.length > 0" class="groups-section">
        <div class="section-header">
          <h3>分组结果</h3>
          <div class="section-actions">
            <button class="btn btn-sm btn-secondary" @click="showAllGroups = !showAllGroups">
              {{ showAllGroups ? '收起详情' : '展开全部' }}
            </button>
          </div>
        </div>

        <div class="groups-toolbar">
          <label class="select-all-label">
            <input
              type="checkbox"
              v-model="selectAllGroups"
              @change="toggleSelectAll"
            >
            全选
          </label>
          <span class="selected-count muted">{{ selectedGroupIds.length }} 个已选</span>
          <button
            class="btn btn-sm btn-outline"
            :disabled="selectedGroupIds.length < 2"
            @click="mergeSelectedGroups"
          >
            合并所选
          </button>
        </div>

        <div v-if="matchedGroups.length > 0" class="section-sub-header">
          <h4>已匹配分组 <span class="muted">({{ matchedGroups.length }})</span></h4>
        </div>
        <div class="groups-list matched-groups">
          <div
            v-for="group in matchedGroups"
            :key="group.id"
            class="group-card"
            :class="{
              selected: store.selectedGroupId === group.id,
              'group-selected': selectedGroupIds.includes(group.id)
            }"
            @click="selectGroup(group.id)"
          >
            <div class="group-header">
              <div class="group-select" @click.stop>
                <input
                  type="checkbox"
                  :checked="selectedGroupIds.includes(group.id)"
                  @change="toggleGroupSelect(group.id)"
                >
              </div>
              <div class="group-info">
                <span class="group-name" @click.stop="editGroupName(group)">{{ group.name }}</span>
                <span class="group-badge" :class="`category-${group.category}`">
                  {{ group.templateType }}
                </span>
                <span class="match-score" :class="scoreClass(group.matchScore)">
                  {{ group.matchScore }}% 匹配
                </span>
              </div>
              <div class="group-meta muted">
                {{ group.matchedSheets.length }} 个工作表
              </div>
            </div>

            <div v-if="showAllGroups || store.selectedGroupId === group.id" class="group-body">
              <div class="sheet-list">
                <div class="list-title muted">来源工作表：</div>
                <div
                  v-for="(sheet, idx) in group.matchedSheets"
                  :key="idx"
                  class="sheet-item"
                >
                  <span class="sheet-icon">📄</span>
                  <span class="sheet-file">{{ sheet.fileName }}</span>
                  <span class="sheet-arrow">→</span>
                  <span class="sheet-name">{{ sheet.sheetName }}</span>
                  <span class="sheet-rows muted">({{ sheet.rowCount }} 行)</span>
                  <button
                    class="btn btn-xs btn-outline move-btn"
                    title="移动到其他分组"
                    @click.stop="showMoveSheetDialog(group, sheet, idx)"
                  >
                    移动
                  </button>
                </div>
              </div>

              <div class="fields-section">
                <div class="common-fields">
                  <div class="fields-title">共性字段：</div>
                  <div class="field-tags">
                    <span
                      v-for="field in group.commonFields"
                      :key="field"
                      class="field-tag common"
                    >
                      {{ field }}
                    </span>
                  </div>
                </div>

                <div v-if="group.differenceFields.length > 0" class="diff-fields">
                  <div class="fields-title">差异字段：</div>
                  <div class="field-tags">
                    <span
                      v-for="field in group.differenceFields"
                      :key="field"
                      class="field-tag diff"
                    >
                      {{ field }}
                    </span>
                  </div>
                </div>
              </div>

              <div class="template-section">
                <div class="template-select-row">
                  <label>推荐模板：</label>
                  <select
                    v-model="group.recommendedTemplateId"
                    class="form-control"
                    @change="onTemplateChange(group)"
                  >
                    <option value="">-- 选择模板 --</option>
                    <option
                      v-for="tmpl in availableTemplates"
                      :key="tmpl.id"
                      :value="tmpl.id"
                    >
                      {{ tmpl.name }} ({{ tmpl.templateType }})
                    </option>
                  </select>
                  <span v-if="group.recommendedTemplateName" class="template-name">
                    {{ group.recommendedTemplateName }}
                  </span>
                </div>
              </div>

              <div class="group-actions">
                <button class="btn btn-sm btn-primary" @click.stop="previewGroup(group)">
                  提取预览
                </button>
                <button class="btn btn-sm btn-secondary" @click.stop="viewGroupDetail(group)">
                  查看详情
                </button>
              </div>
            </div>
          </div>
        </div>

        <div v-if="unknownGroups.length > 0" class="section-sub-header unknown-section-header">
          <h4>通用分组 <span class="muted">({{ unknownGroups.length }})</span></h4>
        </div>
        <div v-if="unknownGroups.length > 0" class="groups-list unknown-groups">
          <div
            v-for="group in unknownGroups"
            :key="group.id"
            class="group-card unknown-group-card"
            :class="{
              selected: store.selectedGroupId === group.id,
              'group-selected': selectedGroupIds.includes(group.id)
            }"
            @click="selectGroup(group.id)"
          >
            <div class="group-header">
              <div class="group-select" @click.stop>
                <input
                  type="checkbox"
                  :checked="selectedGroupIds.includes(group.id)"
                  @change="toggleGroupSelect(group.id)"
                >
              </div>
              <div class="group-info">
                <span class="group-name" @click.stop="editGroupName(group)">{{ group.name }}</span>
                <span class="group-badge" :class="`category-${group.category}`">
                  {{ group.templateType }}
                </span>
                <span class="match-score" :class="scoreClass(group.matchScore)">
                  {{ group.matchScore }}% 匹配
                </span>
              </div>
              <div class="group-meta muted">
                {{ group.matchedSheets.length }} 个工作表
              </div>
            </div>

            <div v-if="showAllGroups || store.selectedGroupId === group.id" class="group-body">
              <div class="sheet-list">
                <div class="list-title muted">来源工作表：</div>
                <div
                  v-for="(sheet, idx) in group.matchedSheets"
                  :key="idx"
                  class="sheet-item"
                >
                  <span class="sheet-icon">📄</span>
                  <span class="sheet-file">{{ sheet.fileName }}</span>
                  <span class="sheet-arrow">→</span>
                  <span class="sheet-name">{{ sheet.sheetName }}</span>
                  <span class="sheet-rows muted">({{ sheet.rowCount }} 行)</span>
                  <button
                    class="btn btn-xs btn-outline move-btn"
                    title="移动到其他分组"
                    @click.stop="showMoveSheetDialog(group, sheet, idx)"
                  >
                    移动
                  </button>
                </div>
              </div>

              <div class="fields-section">
                <div class="common-fields">
                  <div class="fields-title">共性字段：</div>
                  <div class="field-tags">
                    <span
                      v-for="field in group.commonFields"
                      :key="field"
                      class="field-tag common"
                    >
                      {{ field }}
                    </span>
                  </div>
                </div>

                <div v-if="group.differenceFields.length > 0" class="diff-fields">
                  <div class="fields-title">差异字段：</div>
                  <div class="field-tags">
                    <span
                      v-for="field in group.differenceFields"
                      :key="field"
                      class="field-tag diff"
                    >
                      {{ field }}
                    </span>
                  </div>
                </div>
              </div>

              <div class="template-section">
                <div class="template-select-row">
                  <label>推荐模板：</label>
                  <select
                    v-model="group.recommendedTemplateId"
                    class="form-control"
                    @change="onTemplateChange(group)"
                  >
                    <option value="">-- 选择模板 --</option>
                    <option
                      v-for="tmpl in availableTemplates"
                      :key="tmpl.id"
                      :value="tmpl.id"
                    >
                      {{ tmpl.name }} ({{ tmpl.templateType }})
                    </option>
                  </select>
                  <span v-if="group.recommendedTemplateName" class="template-name">
                    {{ group.recommendedTemplateName }}
                  </span>
                </div>
              </div>

              <div class="group-actions">
                <button class="btn btn-sm btn-primary" @click.stop="previewGroup(group)">
                  提取预览
                </button>
                <button class="btn btn-sm btn-secondary" @click.stop="viewGroupDetail(group)">
                  查看详情
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div v-if="store.phase === 'done'" class="action-section">
        <button class="btn btn-primary btn-lg" @click="saveAllTemplates" :disabled="saveLoading">
          {{ saveLoading ? `保存中 (${saveProgress.current}/${saveProgress.total})` : '全部保存为模板' }}
        </button>
        <button class="btn btn-secondary btn-lg" @click="exportReport">
          导出分析报告
        </button>
        <button class="btn btn-secondary" @click="startNewAnalysis">
          新建分析
        </button>
      </div>
      <div v-if="saveLoading && saveProgress.total > 0" class="save-progress-card">
        <div class="save-progress-label">正在保存：{{ saveProgress.currentGroup }}</div>
        <div class="save-progress-bar">
          <div
            class="save-progress-fill"
            :style="{ width: (saveProgress.current / saveProgress.total * 100) + '%' }"
          ></div>
        </div>
      </div>
    </template>

    <InputDialog
      v-model="showNameInputDialog"
      :title="nameInputDialogConfig.title"
      :message="nameInputDialogConfig.message"
      :placeholder="nameInputDialogConfig.placeholder"
      confirm-text="确定"
      @confirm="handleNameInputConfirm"
    />

    <div v-if="showPreviewModal" class="modal active" @click.self="showPreviewModal = false">
      <div class="modal-content modal-lg">
        <div class="modal-header">
          <h4>模板预览 - {{ previewGroupName }}</h4>
          <span class="close" @click="showPreviewModal = false">×</span>
        </div>
        <div class="modal-body">
          <div v-if="previewLoading" class="loading-state">
            <span class="spinner"></span>
            正在提取网格数据...
          </div>
          <div v-else-if="previewData" class="preview-content">
            <div class="preview-info-card">
              <div class="preview-info-row">
                <span class="preview-info-label">分组名称：</span>
                <span class="preview-info-value">{{ previewData.groupInfo?.name }}</span>
              </div>
              <div class="preview-info-row">
                <span class="preview-info-label">模板类型：</span>
                <span class="preview-info-value">{{ previewData.groupInfo?.templateType }}</span>
              </div>
              <div class="preview-info-row">
                <span class="preview-info-label">匹配度：</span>
                <span class="preview-info-value score-{{ previewData.groupInfo?.matchScore >= 80 ? 'high' : previewData.groupInfo?.matchScore >= 60 ? 'medium' : 'low' }}">
                  {{ previewData.groupInfo?.matchScore }}%
                </span>
              </div>
              <div class="preview-info-row">
                <span class="preview-info-label">工作表数量：</span>
                <span class="preview-info-value">{{ previewData.groupInfo?.sheetCount }} 个</span>
              </div>
              <div class="preview-info-row">
                <span class="preview-info-label">共性字段：</span>
                <span class="preview-info-value">{{ previewData.groupInfo?.commonFieldsCount }} 个</span>
              </div>
              <div class="preview-info-row">
                <span class="preview-info-label">差异字段：</span>
                <span class="preview-info-value diff-count">{{ previewData.groupInfo?.differenceFieldsCount }} 个</span>
              </div>
            </div>

            <div class="preview-source muted">
              来源：{{ previewData.preview_data?.file_name }} / {{ previewData.preview_data?.sheet_name }}
            </div>

            <ExcelPreview
              v-if="previewData.fields?.length"
              :fields="previewData.fields"
              :sample-rows="previewData.preview_data?.sample_rows || []"
              :title="previewGroupName"
              :grid-data="previewData.preview_data?.grid_preview || null"
              :rows="10"
              :columns="8"
            />

            <div v-if="previewData.groupInfo?.diffGridRows?.length > 0" class="diff-preview">
              <div class="diff-preview-title">差异字段预览：</div>
              <div class="diff-table-wrapper">
                <table class="diff-table">
                  <tbody>
                    <tr v-for="(row, i) in previewData.groupInfo.diffGridRows" :key="i">
                      <td v-for="(cell, j) in row" :key="j" :class="{ 'diff-cell': i === 0 }">
                        {{ cell }}
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>

            <div v-else class="no-preview-data muted">
              暂无预览数据
            </div>
          </div>
        </div>
      </div>
    </div>

    <div v-if="showMoveModal" class="modal active" @click.self="closeMoveModal">
      <div class="modal-content modal-sm">
        <div class="modal-header">
          <h4>移动工作表</h4>
          <span class="close" @click="closeMoveModal">×</span>
        </div>
        <div class="modal-body">
          <div class="move-info">
            <p>将 <strong>{{ moveSourceSheet?.sheetName }}</strong> 从 <strong>{{ moveSourceGroup?.name }}</strong> 移动到：</p>
          </div>
          <div class="move-options">
            <div
              v-for="targetGroup in moveTargetGroups"
              :key="targetGroup.id"
              class="move-option-item"
              :class="{ disabled: targetGroup.id === moveSourceGroup?.id }"
              @click="targetGroup.id !== moveSourceGroup?.id && moveSheetToGroup(targetGroup.id)"
            >
              <span class="move-option-name">{{ targetGroup.name }}</span>
              <span class="move-option-count muted">{{ targetGroup.matchedSheets.length }} 个工作表</span>
            </div>
          </div>
          <div class="move-actions">
            <button class="btn btn-secondary btn-sm" @click="closeMoveModal">取消</button>
            <button class="btn btn-outline btn-sm" @click="createNewGroupAndMove">创建新分组</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import { useBatchAnalyzeStore, type SheetGroup, type SheetInfo } from '../stores/batchAnalyze'
import { useBatchAnalyze } from '../composables/useBatchAnalyze'
import templatePreviewApi from '../api/templatePreview'
import ExcelPreview from '../components/template/ExcelPreview.vue'
import InputDialog from '../components/InputDialog.vue'

const router = useRouter()
const store = useBatchAnalyzeStore()
const { phase, groups, extractedSheets } = storeToRefs(store)

const { startBatchAnalyze, analyzeAndGroup, extractGridForSheet } = useBatchAnalyze()

const showNameInputDialog = ref(false)
const nameInputDialogConfig = ref({
  title: '重命名分组',
  message: '请输入新的分组名称：',
  placeholder: '分组名称'
})
const nameInputTargetGroup = ref<SheetGroup | null>(null)

const showAllGroups = ref(false)
const showPreviewModal = ref(false)
const showFailedFiles = ref(false)
const previewGroupName = ref('')
const previewData = ref<any>(null)
const previewLoading = ref(false)
const availableTemplates = ref<Array<{ id: string; name: string; templateType: string }>>([])
const fileMap = ref<Map<string, File>>(new Map())

const showMoveModal = ref(false)
const moveSourceSheet = ref<any>(null)
const moveSourceGroup = ref<any>(null)
const moveSourceIndex = ref(-1)

const selectedGroupIds = ref<string[]>([])
const selectAllGroups = ref(false)

const moveTargetGroups = computed(() => {
  if (!moveSourceGroup.value) return groups.value
  return groups.value.filter(g => g.id !== moveSourceGroup.value.id)
})

const matchedTemplatesCount = computed(() => {
  return groups.value.filter(g => g.recommendedTemplateId).length
})

const matchedGroups = computed(() => {
  return groups.value.filter(g => g.category !== 'unknown')
})

const unknownGroups = computed(() => {
  return groups.value.filter(g => g.category === 'unknown')
})

const scoreClass = (score: number) => {
  if (score >= 80) return 'score-high'
  if (score >= 60) return 'score-medium'
  return 'score-low'
}

onMounted(async () => {
  await loadTemplates()

  if (extractedSheets.value.length > 0 && groups.value.length === 0 && phase.value === 'idle') {
    store.setPhase('extracting')
    store.updateProgress({ progress: 50 })
    await analyzeAndGroup()
  }
})

async function loadTemplates() {
  try {
    const res = await templatePreviewApi.listTemplates()
    if (res?.success && Array.isArray(res.templates)) {
      availableTemplates.value = res.templates
        .filter((t: any) => t?.category === 'excel')
        .map((t: any) => ({
          id: t.id,
          name: t.name || t.template_name || '未命名模板',
          templateType: t.template_type || ''
        }))
    }
  } catch (e) {
    console.error('加载模板失败:', e)
  }
}

function goToBusinessDocking() {
  router.push({ name: 'business-docking' })
}

function selectGroup(groupId: string) {
  store.selectGroup(store.selectedGroupId === groupId ? null : groupId)
}

function onTemplateChange(group: SheetGroup) {
  const tmpl = availableTemplates.value.find(t => t.id === group.recommendedTemplateId)
  if (tmpl) {
    group.recommendedTemplateName = tmpl.name
    store.updateGroupTemplate(group.id, tmpl.id, tmpl.name, group.matchScore)
  }
}

async function previewGroup(group: SheetGroup) {
  if (group.matchedSheets.length === 0) {
    alert('该分组没有工作表')
    return
  }

  previewGroupName.value = group.name
  showPreviewModal.value = true
  previewLoading.value = true
  previewData.value = null

  try {
    const firstSheet = group.matchedSheets[0]
    const fields = group.commonFields.map((f) => ({
      label: f,
      name: f,
      type: 'dynamic'
    }))

    const sampleRows = firstSheet?.sampleRows || []

    const gridRows: any[][] = []
    if (sampleRows.length > 0) {
      const headers = Object.keys(sampleRows[0])
      gridRows.push(headers)
      for (const row of sampleRows.slice(0, 10)) {
        gridRows.push(headers.map(h => row[h] ?? ''))
      }
    }

    const diffGridRows: any[][] = []
    if (group.differenceFields.length > 0 && firstSheet?.sampleRows) {
      const diffHeaders = group.differenceFields
      const firstSheetFields = new Set(firstSheet.fields.map(f => f.toLowerCase()))
      const diffDataRows = firstSheet.sampleRows.slice(0, 5).map((row: Record<string, any>) => {
        const result: any[] = []
        for (const field of group.differenceFields) {
          const fieldLower = field.toLowerCase()
          if (firstSheetFields.has(fieldLower)) {
            result.push(row[field] ?? '')
          } else {
            result.push('-')
          }
        }
        return result
      })
      if (diffDataRows.length > 0) {
        diffGridRows.push(diffHeaders)
        diffGridRows.push(...diffDataRows)
      }
    }

    previewData.value = {
      fields,
      preview_data: {
        sample_rows: sampleRows,
        grid_preview: { rows: gridRows },
        sheet_name: firstSheet?.sheetName || '',
        file_name: firstSheet?.fileName || ''
      },
      groupInfo: {
        name: group.name,
        templateType: group.templateType,
        matchScore: group.matchScore,
        sheetCount: group.matchedSheets.length,
        commonFieldsCount: group.commonFields.length,
        differenceFieldsCount: group.differenceFields.length,
        diffGridRows
      }
    }
  } catch (e) {
    console.error('预览失败:', e)
    previewData.value = null
  } finally {
    previewLoading.value = false
  }
}

function viewGroupDetail(group: SheetGroup) {
  store.selectGroup(group.id)
  showAllGroups.value = true
}

const saveLoading = ref(false)
const saveProgress = ref({ current: 0, total: 0, currentGroup: '' })

async function saveAllTemplates() {
  if (groups.value.length === 0) {
    alert('没有可保存的分组')
    return
  }

  const confirmed = confirm(`确定要保存 ${groups.value.length} 个分组为模板吗？`)
  if (!confirmed) return

  saveLoading.value = true
  saveProgress.value = { current: 0, total: groups.value.length, currentGroup: '' }

  const results: { name: string; success: boolean; message: string }[] = []

  try {
    for (let i = 0; i < groups.value.length; i++) {
      const group = groups.value[i]
      saveProgress.value = { current: i + 1, total: groups.value.length, currentGroup: group.name }

      const templateName = group.recommendedTemplateName || `${group.templateType}模板_${i + 1}`
      const fields = group.commonFields.map((f) => ({
        label: f,
        name: f,
        type: 'dynamic'
      }))

      const firstSheet = group.matchedSheets[0]
      const sampleRows = firstSheet?.sampleRows || []

      const payload = {
        category: 'excel',
        template_type: group.templateType || 'Excel',
        business_scope: group.category || '',
        name: templateName,
        fields,
        preview_data: {
          sample_rows: sampleRows.slice(0, 10),
          grid_preview: { rows: [] },
          sheet_name: firstSheet?.sheetName || '',
          sheet_names: group.matchedSheets.map(s => s.sheetName),
          file_path: firstSheet?.fileName || ''
        },
        source: 'batch-analyze'
      }

      try {
        const res = await templatePreviewApi.createTemplateFromGrid(payload)
        if (res?.success) {
          results.push({ name: templateName, success: true, message: '保存成功' })
          if (group.recommendedTemplateId) {
            store.updateGroupTemplate(group.id, res.id || group.recommendedTemplateId, templateName, group.matchScore)
          }
        } else {
          results.push({ name: templateName, success: false, message: res?.message || '保存失败' })
        }
      } catch (e) {
        results.push({ name: templateName, success: false, message: e?.message || '未知错误' })
      }
    }

    const successCount = results.filter(r => r.success).length
    const failCount = results.filter(r => !r.success).length
    const message = `保存完成：成功 ${successCount} 个${failCount > 0 ? `，失败 ${failCount} 个` : ''}`
    alert(message)

  } finally {
    saveLoading.value = false
    saveProgress.value = { current: 0, total: 0, currentGroup: '' }
  }
}

function exportReport() {
  const report = {
    totalSheets: extractedSheets.value.length,
    totalGroups: groups.value.length,
    groups: groups.value.map(g => ({
      name: g.name,
      template: g.recommendedTemplateName,
      matchScore: g.matchScore,
      sheetCount: g.matchedSheets.length,
      sources: g.matchedSheets.map(s => `${s.fileName} > ${s.sheetName}`),
      commonFields: g.commonFields,
      differenceFields: g.differenceFields
    })),
    generatedAt: new Date().toISOString()
  }

  const blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `batch-analyze-report-${Date.now()}.json`
  a.click()
  URL.revokeObjectURL(url)
}

function startNewAnalysis() {
  store.reset()
  sessionStorage.removeItem('batch_analyze_pending_files')
  router.push({ name: 'business-docking' })
}

function retry() {
  store.setError('')
  store.setPhase('idle')
}

function showMoveSheetDialog(group: SheetGroup, sheet: any, index: number) {
  moveSourceGroup.value = group
  moveSourceSheet.value = sheet
  moveSourceIndex.value = index
  showMoveModal.value = true
}

function closeMoveModal() {
  showMoveModal.value = false
  moveSourceSheet.value = null
  moveSourceGroup.value = null
  moveSourceIndex.value = -1
}

function moveSheetToGroup(targetGroupId: string) {
  if (!moveSourceSheet.value || !moveSourceGroup.value) return

  const sourceGroupIndex = groups.value.findIndex(g => g.id === moveSourceGroup.value.id)
  const targetGroupIndex = groups.value.findIndex(g => g.id === targetGroupId)
  if (sourceGroupIndex === -1 || targetGroupIndex === -1) return

  const sheet = moveSourceSheet.value
  const updatedGroups = [...groups.value]

  updatedGroups[sourceGroupIndex] = recalculateGroupFields({
    ...updatedGroups[sourceGroupIndex],
    matchedSheets: updatedGroups[sourceGroupIndex].matchedSheets.filter((_: any, i: number) => i !== moveSourceIndex.value)
  })

  updatedGroups[targetGroupIndex] = recalculateGroupFields({
    ...updatedGroups[targetGroupIndex],
    matchedSheets: [...updatedGroups[targetGroupIndex].matchedSheets, sheet]
  })

  store.setGroups(updatedGroups)
  closeMoveModal()
}

function createNewGroupAndMove() {
  if (!moveSourceSheet.value) return

  const newGroupName = prompt('请输入新分组名称：')
  if (!newGroupName) return

  const sourceGroupIndex = groups.value.findIndex(g => g.id === moveSourceGroup.value?.id)

  const newGroup: SheetGroup = {
    id: `group_${Date.now()}`,
    name: newGroupName,
    category: '',
    matchedSheets: [moveSourceSheet.value],
    commonFields: moveSourceSheet.value.fields,
    differenceFields: [],
    recommendedTemplateId: '',
    recommendedTemplateName: '',
    matchScore: 100,
    templateType: '通用'
  }

  const updatedGroups = [...groups.value]

  if (sourceGroupIndex !== -1) {
    updatedGroups[sourceGroupIndex] = recalculateGroupFields({
      ...updatedGroups[sourceGroupIndex],
      matchedSheets: updatedGroups[sourceGroupIndex].matchedSheets.filter((_: any, i: number) => i !== moveSourceIndex.value)
    })
  }

  updatedGroups.push(newGroup)
  store.setGroups(updatedGroups)
  closeMoveModal()
}

function recalculateGroupFields(group: SheetGroup): SheetGroup {
  if (group.matchedSheets.length === 0) {
    return { ...group, commonFields: [], differenceFields: [] }
  }

  const allFields = new Set<string>()
  for (const sheet of group.matchedSheets) {
    sheet.fields.forEach((f: string) => allFields.add(f))
  }

  const commonFields: string[] = []
  const differenceFields: string[] = []

  for (const field of allFields) {
    const appearsInAll = group.matchedSheets.every((sheet: any) =>
      sheet.fields.includes(field)
    )
    if (appearsInAll) {
      commonFields.push(field)
    } else {
      differenceFields.push(field)
    }
  }

  return { ...group, commonFields, differenceFields }
}

function toggleGroupSelect(groupId: string) {
  const idx = selectedGroupIds.value.indexOf(groupId)
  if (idx === -1) {
    selectedGroupIds.value.push(groupId)
  } else {
    selectedGroupIds.value.splice(idx, 1)
  }
  selectAllGroups.value = selectedGroupIds.value.length === groups.value.length
}

function toggleSelectAll() {
  if (selectAllGroups.value) {
    selectedGroupIds.value = groups.value.map(g => g.id)
  } else {
    selectedGroupIds.value = []
  }
}

function mergeSelectedGroups() {
  if (selectedGroupIds.value.length < 2) return

  const groupsToMerge = groups.value.filter(g => selectedGroupIds.value.includes(g.id))
  if (groupsToMerge.length < 2) return

  const newName = prompt('请输入合并后的分组名称：', `合并分组_${groupsToMerge.length}`)
  if (!newName) return

  const allSheets: any[] = []
  for (const g of groupsToMerge) {
    allSheets.push(...g.matchedSheets)
  }

  const allFields = new Set<string>()
  for (const sheet of allSheets) {
    sheet.fields.forEach((f: string) => allFields.add(f))
  }

  const commonFields: string[] = []
  const differenceFields: string[] = []

  for (const field of allFields) {
    const appearsInAll = allSheets.every((sheet: any) =>
      sheet.fields.includes(field)
    )
    if (appearsInAll) {
      commonFields.push(field)
    } else {
      differenceFields.push(field)
    }
  }

  const { inferTemplateTypeByFields } = useBatchAnalyze()
  const { templateType, scopeKey, matchScore } = inferTemplateTypeByFields(Array.from(allFields))

  const mergedGroup: SheetGroup = {
    id: `group_${Date.now()}`,
    name: newName,
    category: scopeKey,
    matchedSheets: allSheets,
    commonFields,
    differenceFields,
    recommendedTemplateId: '',
    recommendedTemplateName: '',
    matchScore: Math.round(matchScore * 100),
    templateType
  }

  const updatedGroups = groups.value.filter(g => !selectedGroupIds.value.includes(g.id))
  updatedGroups.push(mergedGroup)

  store.setGroups(updatedGroups)
  selectedGroupIds.value = []
  selectAllGroups.value = false
}

function editGroupName(group: SheetGroup) {
  nameInputTargetGroup.value = group
  nameInputDialogConfig.value = {
    title: '重命名分组',
    message: '请输入新的分组名称：',
    placeholder: '分组名称'
  }
  showNameInputDialog.value = true
}

function handleNameInputConfirm(newName: string) {
  if (!newName || !nameInputTargetGroup.value) return
  if (newName === nameInputTargetGroup.value.name) return

  const updatedGroups = groups.value.map(g => {
    if (g.id === nameInputTargetGroup.value!.id) {
      return { ...g, name: newName }
    }
    return g
  })

  store.setGroups(updatedGroups)
  nameInputTargetGroup.value = null
}
</script>

<style scoped>
.batch-analyze-view {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
}

.page-header {
  margin-bottom: 24px;
}

.page-header h2 {
  margin: 0 0 8px;
  font-size: 24px;
  color: #1a1a2e;
}

.empty-state-card {
  text-align: center;
  padding: 60px 20px;
  background: #f8f9fa;
  border-radius: 12px;
  border: 1px dashed #dee2e6;
}

.empty-icon {
  font-size: 64px;
  margin-bottom: 16px;
}

.empty-title {
  font-size: 20px;
  font-weight: 600;
  color: #495057;
  margin-bottom: 8px;
}

.empty-desc {
  color: #6c757d;
  margin-bottom: 24px;
}

.progress-section {
  background: #fff;
  border-radius: 12px;
  padding: 20px;
  margin-bottom: 20px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
}

.progress-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
}

.progress-phase {
  font-weight: 600;
  color: #495057;
}

.progress-percent {
  color: #42b983;
  font-weight: 600;
}

.progress-bar {
  height: 8px;
  background: #e9ecef;
  border-radius: 4px;
  overflow: hidden;
  margin-bottom: 8px;
}

.progress-fill {
  height: 100%;
  border-radius: 4px;
  transition: width 0.3s ease;
  background: #42b983;
}

.progress-fill.phase-extracting { background: #3b82f6; }
.progress-fill.phase-grouping { background: #8b5cf6; }
.progress-fill.phase-matching { background: #f59e0b; }
.progress-fill.phase-done { background: #10b981; }
.progress-fill.phase-error { background: #ef4444; }

.progress-detail {
  font-size: 13px;
}

.error-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px;
  background: #fef2f2;
  border: 1px solid #fecaca;
  border-radius: 8px;
  margin-bottom: 20px;
  color: #dc2626;
}

.error-icon {
  font-size: 20px;
}

.stats-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 16px;
  margin-bottom: 24px;
}

.stat-card {
  background: #fff;
  border-radius: 12px;
  padding: 20px;
  text-align: center;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
}

.stat-card.stat-warning {
  background: #fef2f2;
}

.stat-card.stat-warning .stat-value {
  color: #dc2626;
}

.stat-value {
  font-size: 32px;
  font-weight: 700;
  color: #42b983;
}

.stat-label {
  font-size: 14px;
  color: #6c757d;
  margin-top: 4px;
}

.failed-files-card {
  background: #fff;
  border-radius: 12px;
  padding: 16px;
  margin-bottom: 24px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
  border-left: 4px solid #f59e0b;
}

.failed-files-header {
  display: flex;
  align-items: center;
  gap: 10px;
}

.failed-icon {
  font-size: 18px;
}

.failed-title {
  font-weight: 600;
  color: #92400e;
  flex: 1;
}

.failed-files-list {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px dashed #e9ecef;
}

.failed-file-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 0;
  border-bottom: 1px solid #f3f4f6;
}

.failed-file-item:last-child {
  border-bottom: none;
}

.failed-file-name {
  font-weight: 500;
  color: #1a1a2e;
}

.failed-file-error {
  font-size: 12px;
  color: #dc2626;
}

.groups-section {
  background: #fff;
  border-radius: 12px;
  padding: 20px;
  margin-bottom: 24px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
  max-height: 500px;
  overflow-y: auto;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.section-header h3 {
  margin: 0;
  font-size: 18px;
  color: #1a1a2e;
}

.groups-list {
  display: flex;
  flex-direction: row;
  gap: 12px;
  overflow-x: auto;
  padding-bottom: 12px;
  scroll-behavior: smooth;
}

.groups-list::-webkit-scrollbar {
  height: 6px;
}

.groups-list::-webkit-scrollbar-track {
  background: #f1f1f1;
  border-radius: 3px;
}

.groups-list::-webkit-scrollbar-thumb {
  background: #c1c1c1;
  border-radius: 3px;
}

.groups-list::-webkit-scrollbar-thumb:hover {
  background: #a1a1a1;
}

.groups-toolbar {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 12px 16px;
  background: #f8f9fa;
  border-radius: 8px;
  margin-bottom: 12px;
  flex-shrink: 0;
}

.select-all-label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  color: #495057;
  cursor: pointer;
}

.selected-count {
  font-size: 13px;
}

.group-card {
  border: 1px solid #e9ecef;
  border-radius: 10px;
  padding: 16px;
  cursor: pointer;
  transition: all 0.2s;
  flex-shrink: 0;
  min-width: 200px;
  max-width: 200px;
}

.group-card:hover {
  border-color: #42b983;
  box-shadow: 0 2px 8px rgba(66,185,131,0.15);
}

.group-card.selected {
  border-color: #42b983;
  background: #f8fdf9;
}

.group-card.group-selected {
  border-color: #3b82f6;
  background: #eff6ff;
}

.section-sub-header {
  margin: 16px 0 12px 0;
}

.section-sub-header h4 {
  margin: 0;
  font-size: 16px;
  color: #1a1a2e;
}

.unknown-section-header h4 {
  color: #6c757d;
}

.unknown-groups {
  margin-top: 0;
}

.unknown-group-card {
  border: 2px dashed #d1d5db;
  background: #fafafa;
}

.unknown-group-card:hover {
  border-color: #9ca3af;
  box-shadow: 0 2px 8px rgba(0,0,0,0.08);
}

.unknown-group-card.selected {
  border-color: #9ca3af;
  background: #f5f5f5;
}

.group-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.group-info {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.group-name {
  font-weight: 600;
  font-size: 15px;
  color: #1a1a2e;
  cursor: text;
}

.group-name:hover {
  color: #42b983;
  text-decoration: underline;
}

.group-select {
  display: flex;
  align-items: center;
  margin-right: 10px;
}

.group-badge {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 4px;
  background: #e8f4f0;
  color: #42b983;
}

.group-badge.category-orders { background: #dbeafe; color: #2563eb; }
.group-badge.category-products { background: #dcfce7; color: #16a34a; }
.group-badge.category-customers { background: #fef3c7; color: #d97706; }
.group-badge.category-materials { background: #f3e8ff; color: #9333ea; }

.match-score {
  font-size: 12px;
  font-weight: 500;
}

.match-score.score-high { color: #10b981; }
.match-score.score-medium { color: #f59e0b; }
.match-score.score-low { color: #ef4444; }

.group-meta {
  font-size: 13px;
}

.group-body {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px dashed #e9ecef;
}

.sheet-list {
  margin-bottom: 16px;
}

.list-title {
  font-size: 13px;
  margin-bottom: 8px;
}

.sheet-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 0;
  font-size: 13px;
}

.sheet-icon {
  font-size: 14px;
}

.sheet-file {
  color: #495057;
}

.sheet-arrow {
  color: #adb5bd;
}

.sheet-name {
  color: #42b983;
  font-weight: 500;
}

.sheet-rows {
  font-size: 12px;
}

.fields-section {
  margin-bottom: 16px;
}

.common-fields, .diff-fields {
  margin-bottom: 10px;
}

.fields-title {
  font-size: 13px;
  color: #495057;
  margin-bottom: 6px;
}

.field-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.field-tag {
  font-size: 12px;
  padding: 3px 10px;
  border-radius: 4px;
}

.field-tag.common {
  background: #e8f4f0;
  color: #16a34a;
}

.field-tag.diff {
  background: #fef3c7;
  color: #d97706;
}

.template-section {
  margin-bottom: 16px;
}

.template-select-row {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.template-select-row label {
  font-size: 13px;
  color: #495057;
  min-width: 80px;
}

.template-select-row .form-control {
  flex: 1;
  max-width: 300px;
}

.template-name {
  font-size: 13px;
  color: #42b983;
  font-weight: 500;
}

.group-actions {
  display: flex;
  gap: 10px;
}

.action-section {
  display: flex;
  gap: 12px;
  justify-content: center;
  flex-wrap: wrap;
}

.btn-lg {
  padding: 12px 24px;
  font-size: 16px;
}

.loading-state {
  text-align: center;
  padding: 40px;
  color: #6c757d;
}

.spinner {
  display: inline-block;
  width: 24px;
  height: 24px;
  border: 3px solid #e9ecef;
  border-top-color: #42b983;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin-right: 10px;
  vertical-align: middle;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.preview-content {
  max-height: 500px;
  overflow-y: auto;
}

.no-preview-data {
  text-align: center;
  padding: 40px;
}

.preview-info-card {
  background: #f8f9fa;
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 16px;
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}

.preview-info-row {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.preview-info-label {
  font-size: 12px;
  color: #6c757d;
}

.preview-info-value {
  font-size: 14px;
  font-weight: 500;
  color: #1a1a2e;
}

.preview-info-value.score-high { color: #10b981; }
.preview-info-value.score-medium { color: #f59e0b; }
.preview-info-value.score-low { color: #ef4444; }
.preview-info-value.diff-count { color: #d97706; }

.preview-source {
  font-size: 12px;
  margin-bottom: 12px;
}

.diff-preview {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px dashed #e9ecef;
}

.diff-preview-title {
  font-size: 13px;
  color: #d97706;
  margin-bottom: 8px;
}

.diff-table-wrapper {
  overflow-x: auto;
}

.diff-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}

.diff-table td {
  padding: 6px 10px;
  border: 1px solid #e9ecef;
  white-space: nowrap;
}

.diff-table td.diff-cell {
  background: #fef3c7;
  font-weight: 500;
}

.modal-lg {
  max-width: 900px;
}

.save-progress-card {
  margin-top: 16px;
  padding: 16px;
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
  border-radius: 8px;
}

.save-progress-label {
  font-size: 13px;
  color: #15803d;
  margin-bottom: 8px;
}

.save-progress-bar {
  height: 6px;
  background: #e9ecef;
  border-radius: 3px;
  overflow: hidden;
}

.save-progress-fill {
  height: 100%;
  background: #42b983;
  border-radius: 3px;
  transition: width 0.3s ease;
}

.modal-sm {
  max-width: 400px;
}

.move-info {
  margin-bottom: 16px;
}

.move-info p {
  margin: 0;
  font-size: 14px;
  color: #495057;
}

.move-options {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 16px;
  max-height: 300px;
  overflow-y: auto;
}

.move-option-item {
  padding: 12px;
  border: 1px solid #e9ecef;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.move-option-item:hover:not(.disabled) {
  border-color: #42b983;
  background: #f8fdf9;
}

.move-option-item.disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.move-option-name {
  font-weight: 500;
  color: #1a1a2e;
}

.move-option-count {
  font-size: 12px;
}

.move-actions {
  display: flex;
  gap: 10px;
  justify-content: flex-end;
}

.btn-outline {
  background: transparent;
  border: 1px solid #dee2e6;
  color: #495057;
}

.btn-outline:hover:not(:disabled) {
  background: #f8f9fa;
  border-color: #adb5bd;
}

.btn-xs {
  padding: 2px 6px;
  font-size: 11px;
}

.move-btn {
  margin-left: auto;
  flex-shrink: 0;
}
</style>
