<template>
  <div class="page-view tp-page-view" id="view-template-preview">
    <div class="page-content tp-page">
      <header class="tp-hero">
        <div class="tp-hero-main">
          <h2 class="tp-title">模板库</h2>
          <p class="tp-lead muted">
            管理办公五类导出模板（Excel / Word / CSV / PPT / PDF），按业务筛选；替换 Excel 模板时会校验必备词条。
          </p>
        </div>
        <div class="tp-hero-actions">
          <button type="button" class="btn btn-secondary btn-sm" @click="refreshTemplates">刷新</button>
          <button type="button" class="btn btn-primary btn-sm" @click="openCreateModal()">
            <i class="fa fa-plus" aria-hidden="true"></i> 新建模板
          </button>
        </div>
      </header>

      <div class="tp-toolbar">
        <div class="tp-filter-pills" role="tablist" aria-label="业务筛选">
          <button
            v-for="tab in scopeTabs"
            :key="tab.key"
            type="button"
            role="tab"
            class="tp-pill"
            :class="{ 'tp-pill--active': activeScopeTab === tab.key }"
            :aria-selected="activeScopeTab === tab.key"
            @click="activeScopeTab = tab.key"
          >
            {{ tab.label }}
          </button>
        </div>
        <div v-if="!loading && !error" class="tp-toolbar__right">
          <span class="tp-count muted">
            {{ configuredTemplates.length }} 项已配置
            <template v-if="virtualPlaceholders.length">
              · {{ virtualPlaceholders.length }} 待创建
            </template>
          </span>
          <label v-if="virtualPlaceholders.length" class="tp-toggle">
            <input v-model="showVirtualPlaceholders" type="checkbox" />
            <span>显示待创建</span>
          </label>
        </div>
      </div>

      <div v-if="!loading && !error" class="tp-format-bar" role="tablist" aria-label="文件类型筛选">
        <button
          v-for="tab in formatTabs"
          :key="tab.key"
          type="button"
          role="tab"
          class="tp-format-pill"
          :class="{ 'tp-format-pill--active': activeFormatTab === tab.key }"
          :aria-selected="activeFormatTab === tab.key"
          @click="activeFormatTab = tab.key"
        >
          {{ tab.label }}
        </button>
      </div>

      <details class="tp-advanced">
        <summary class="tp-advanced-summary">Excel 网格映射（高级工具）</summary>
        <div class="tp-advanced-body">
          <div class="tp-file-field">
            <input
              ref="gridToolFileInput"
              class="tp-file-field__input"
              type="file"
              accept=".xlsx,.xls"
              @change="onGridToolFileSelected"
            />
            <button
              type="button"
              class="btn btn-sm btn-secondary tp-file-field__pick"
              @click="triggerGridToolFilePick"
            >
              <i class="fa fa-folder-open-o" aria-hidden="true"></i>
              选择 Excel
            </button>
            <span
              class="tp-file-field__name"
              :class="{ 'tp-file-field__name--empty': !gridToolFile }"
              :title="gridToolFileName"
            >
              {{ gridToolFileName }}
            </span>
            <button
              v-if="gridToolFile"
              type="button"
              class="btn btn-sm btn-secondary tp-file-field__clear"
              title="清除已选文件"
              @click="clearGridToolFile"
            >
              清除
            </button>
          </div>
          <button
            type="button"
            class="btn btn-sm btn-primary"
            :disabled="!gridToolFile || extractingGrid"
            @click="extractGridFromExcel"
          >
            {{ extractingGrid ? '提取中…' : '上传并提取' }}
          </button>
          <button
            v-if="gridToolResult"
            type="button"
            class="btn btn-sm btn-secondary"
            @click="openGridToolPreview"
          >
            查看结果
          </button>
          <p v-if="gridToolResult" class="muted tp-advanced-meta">
            {{ gridToolResult.template_name || 'Excel 模板' }} · {{ (gridToolResult.fields || []).length }} 个字段
          </p>
        </div>
      </details>

      <div v-if="loading" class="tp-state muted">模板加载中…</div>
      <div v-else-if="error" class="tp-state tp-state--error">{{ error }}</div>
      <div v-else-if="configuredDisplayTemplates.length === 0 && virtualPlaceholders.length === 0" class="tp-state muted">
        当前筛选下暂无模板
      </div>
      <div v-else-if="configuredDisplayTemplates.length === 0" class="tp-state muted">
        当前筛选下暂无已配置模板，可打开「显示待创建」在下方上传业务占位模板。
      </div>

      <div v-else-if="configuredDisplayTemplates.length" class="tp-grid">
        <article
          v-for="tpl in configuredDisplayTemplates"
          :key="tpl.id"
          class="tp-card"
          :class="getCardSurfaceClass(tpl)"
          :data-template-id="tpl.id"
        >
          <div class="tp-card-head">
            <span class="tp-card-type">{{ getCardTypeLabel(tpl) }}</span>
            <span class="tp-scope">{{ getTemplateScopeLabel(tpl) }}</span>
          </div>

          <h3 class="tp-card-name" :title="tpl.name">{{ tpl.name }}</h3>
          <p class="tp-card-meta muted">{{ getCardMetaLine(tpl) }}</p>
          <p v-if="getCardStatusLine(tpl)" class="tp-card-status">{{ getCardStatusLine(tpl) }}</p>

          <div class="tp-card-preview">
            <TemplateMediaPreview v-bind="buildTemplatePreviewBind(tpl)" />
          </div>

          <div class="tp-card-actions">
            <button
              v-if="tpl.virtual"
              type="button"
              class="btn btn-primary btn-sm"
              @click="startCreateForScope(tpl.business_scope)"
            >
              上传创建
            </button>
            <template v-else>
              <button
                type="button"
                class="btn btn-primary btn-sm"
                :data-template-id="tpl.id"
                @click="previewTemplate(tpl)"
              >
                查看
              </button>
              <button type="button" class="btn btn-secondary btn-sm" @click="openTemplateTarget(tpl)">打开</button>
              <button type="button" class="btn btn-secondary btn-sm" @click="editTemplate(tpl)">编辑</button>
              <button
                v-if="tpl.category === 'excel'"
                type="button"
                class="btn btn-secondary btn-sm"
                @click="openReplaceTemplateDialog(tpl)"
              >
                替换
              </button>
              <button
                v-if="canDeleteTemplate(tpl)"
                type="button"
                class="btn btn-secondary btn-sm tp-btn-danger"
                @click="confirmDeleteTemplate(tpl)"
              >
                删除
              </button>
            </template>
          </div>
        </article>
      </div>

      <details
        v-if="showVirtualPlaceholders && virtualPlaceholders.length"
        class="tp-stash"
      >
        <summary class="tp-stash-summary">
          待创建占位（{{ virtualPlaceholders.length }}）
        </summary>
        <ul class="tp-stash-list">
          <li
            v-for="tpl in virtualPlaceholders"
            :key="tpl.id"
            class="tp-stash-row"
          >
            <div class="tp-stash-row__main">
              <span class="tp-stash-row__title">{{ tpl.name }}</span>
              <span class="tp-stash-row__meta muted">
                必备词条：{{ getRequiredTermsByScope(tpl.business_scope).join('、') }}
              </span>
            </div>
            <button
              type="button"
              class="btn btn-primary btn-sm"
              @click="startCreateForScope(tpl.business_scope)"
            >
              上传创建
            </button>
          </li>
        </ul>
      </details>
    </div>

    <div v-if="showCreateModal" class="modal-overlay" @click.self="closeCreateModal">
        <div class="modal-content" style="max-width:900px;">
          <div class="modal-header">
            <h3><i class="fa fa-folder-open-o" aria-hidden="true"></i> 创建新模板</h3>
            <button type="button" class="modal-close" @click="closeCreateModal">&times;</button>
          </div>
          <div class="modal-body">
            <div v-if="createStep === 1" class="create-step">
              <div class="scope-selector-row">
                <label>适用业务</label>
                <select v-model="templateScope" class="form-control">
                  <option v-for="option in scopeOptions" :key="option.value" :value="option.value">
                    {{ option.label }}
                  </option>
                </select>
                <div class="muted scope-required-terms">
                  必备词条：{{ selectedScopeRequiredTerms.join('、') }}
                </div>
              </div>
              <FileUploadStep
                ref="uploadStep"
                :template-name="templateName"
                :selected-file="selectedFile"
                @update:template-name="templateName = $event"
                @update:selected-file="selectedFile = $event"
                @file-selected="onFileSelected"
              />
              <div v-if="uploadValidationResult && !uploadValidationResult.valid" class="validation-warning">
                当前模板缺少词条：{{ uploadValidationResult.missing.join('、') }}
              </div>
            </div>

            <div v-else-if="createStep === 2" class="create-step" style="min-height: 650px;">
              <FieldEditor
                ref="fieldEditor"
                :fields="editorFields"
                :template-type="editorTemplateType"
                @update-field="onUpdateField"
                @delete-field="onDeleteField"
                @add-field="onAddField"
                @fields-change="onFieldsChange"
              />
            </div>
          </div>
          
          <!-- 分析进度条 -->
          <div v-if="analyzing" class="analyzing-progress">
            <div class="progress-info">
              <span>{{ progressMessage }}</span>
              <span>{{ progressPercent }}%</span>
            </div>
            <div class="progress-bar">
              <div class="progress-fill" :style="{ width: progressPercent + '%' }"></div>
            </div>
            <div class="progress-steps">
              <div :class="['step', { active: progressStep >= 1 }]">
                <span class="step-icon" aria-hidden="true"><i class="fa fa-upload"></i></span>
                <span class="step-label">上传</span>
              </div>
              <div :class="['step', { active: progressStep >= 2 }]">
                <span class="step-icon" aria-hidden="true"><i class="fa fa-search"></i></span>
                <span class="step-label">分析结构</span>
              </div>
              <div :class="['step', { active: progressStep >= 3 }]">
                <span class="step-icon" aria-hidden="true"><i class="fa fa-th"></i></span>
                <span class="step-label">生成预览</span>
              </div>
              <div :class="['step', { active: progressStep >= 4 }]">
                <span class="step-icon" aria-hidden="true"><i class="fa fa-check-circle-o"></i></span>
                <span class="step-label">完成</span>
              </div>
            </div>
          </div>
          
          <div class="modal-footer">
            <button v-if="createStep > 1" type="button" class="btn btn-secondary" @click="prevStep">
              <i class="fa fa-arrow-left" aria-hidden="true"></i> 上一步
            </button>
            <button type="button" class="btn btn-secondary" @click="closeCreateModal">取消</button>
            <button v-if="createStep === 1" type="button" class="btn btn-primary" @click="nextStep" :disabled="!canProceedStep1 || analyzing">
              <span v-if="analyzing">分析中...</span>
              <span v-else>下一步 <i class="fa fa-arrow-right" aria-hidden="true"></i></span>
            </button>
            <button v-else-if="createStep === 2" type="button" class="btn btn-success" @click="saveTemplate">
              <i class="fa fa-check" aria-hidden="true"></i> 保存模板
            </button>
          </div>
        </div>
      </div>

    <div v-if="showPreviewModal" class="modal-overlay" @click.self="closePreviewModal">
      <div class="modal-content" style="max-width:800px;">
        <div class="modal-header">
          <h3><i class="fa fa-file-text-o" aria-hidden="true"></i> 模板预览 - {{ previewingTemplate?.name }}</h3>
          <button type="button" class="modal-close" @click="closePreviewModal">&times;</button>
        </div>
        <div class="modal-body">
          <div class="preview-modal-content">
            <TemplateMediaPreview
              v-if="previewingTemplate"
              v-bind="buildTemplatePreviewBind(previewingTemplate, { rows: 8, columns: 6, labelWidth: 400, labelHeight: 280 })"
            />
          </div>
        </div>
        <div class="modal-footer">
          <button type="button" class="btn btn-secondary" @click="closePreviewModal">关闭</button>
        </div>
      </div>
    </div>

    <div v-if="showEditModal" class="modal-overlay" @click.self="closeEditModal">
      <div class="modal-content">
        <div class="modal-header">
          <h3>编辑模板</h3>
          <button type="button" class="modal-close" @click="closeEditModal">&times;</button>
        </div>
        <div class="modal-body">
          <div class="form-group">
            <label>模板名称</label>
            <input type="text" v-model="editingTemplate.name" class="form-control" />
          </div>
          <div class="form-group">
            <label>分类</label>
            <select v-model="editingTemplate.category" class="form-control">
              <option v-for="kind in templateMediaKindOptions" :key="kind.value" :value="kind.value">
                {{ kind.label }}
              </option>
              <option value="label">标签打印</option>
            </select>
          </div>
        </div>
        <div class="modal-footer">
          <button type="button" class="btn btn-secondary" @click="closeEditModal">取消</button>
          <button type="button" class="btn btn-primary" @click="saveTemplateEdit">保存</button>
        </div>
      </div>
    </div>
    <div v-if="showReplaceModal" class="modal-overlay" @click.self="closeReplaceModal">
      <div class="modal-content" style="max-width:680px;">
        <div class="modal-header">
          <h3>基础模板替代</h3>
          <button type="button" class="modal-close" @click="closeReplaceModal">&times;</button>
        </div>
        <div class="modal-body">
          <div class="muted" style="font-size:13px;margin-bottom:12px;">
            源模板：{{ replaceSourceTemplate?.name }}<br>
            仅可选择同业务范围模板作为替代目标。
          </div>
          <div class="form-group">
            <label>目标模板</label>
            <select v-model="replaceTargetTemplateId" class="form-control">
              <option value="" disabled>请选择目标模板</option>
              <option v-for="tpl in replaceCandidates" :key="tpl.id" :value="tpl.id">
                {{ tpl.name }}（{{ getTemplateTypeLabel(tpl) }}）
              </option>
            </select>
          </div>
        </div>
        <div class="modal-footer">
          <button type="button" class="btn btn-secondary" @click="closeReplaceModal">取消</button>
          <button type="button" class="btn btn-primary" :disabled="!replaceTargetTemplateId || replacingTemplate" @click="confirmReplaceTemplate">
            {{ replacingTemplate ? '替代中...' : '确认替代' }}
          </button>
        </div>
      </div>
    </div>
    <div v-if="showGridToolModal" class="modal-overlay" @click.self="showGridToolModal = false">
      <div class="modal-content" style="max-width:920px;">
        <div class="modal-header">
          <h3><i class="fa fa-th" aria-hidden="true"></i> 网格提取结果 - {{ gridToolResult?.template_name }}</h3>
          <button type="button" class="modal-close" @click="showGridToolModal = false">&times;</button>
        </div>
        <div class="modal-body">
          <ExcelPreview
            v-if="gridToolResult"
            :fields="gridToolResult.fields || []"
            :sample-rows="gridToolResult?.preview_data?.sample_rows || []"
            :title="(gridToolResult?.preview_data?.sheet_name || 'Sheet') + ' 真实网格'"
            :grid-data="gridToolResult?.preview_data?.grid_preview || null"
            :rows="10"
            :columns="8"
          />
        </div>
        <div class="modal-footer">
          <button type="button" class="btn btn-secondary" @click="showGridToolModal = false">关闭</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import templatePreviewApi from '@/api/templatePreview'
import FileUploadStep from '@/components/template/FileUploadStep.vue'
import FieldEditor from '@/components/template/FieldEditor.vue'
import ExcelPreview from '@/components/template/ExcelPreview.vue'
import TemplateMediaPreview from '@/components/template/TemplateMediaPreview.vue'
import {
  TEMPLATE_MEDIA_KINDS,
  TEMPLATE_MEDIA_LABELS,
  TEMPLATE_MEDIA_ORDER,
  isTemplateMediaKind,
  normalizeTemplateMediaKind,
  templateMediaCardClass,
  templateMediaKindFromFilename,
} from '@/constants/templateMediaKinds'
import templateScopeRules from '@/shared/templateScopeRules.json'
import { stripGridPreviewData, stripSampleRowsKeepTemplateShape } from '@/shared/templatePreviewSanitize.js'
import { appAlert, appConfirm } from '@/utils/appDialog'
import { pushErpPage } from '@/utils/erpPagePaths'

const TEMPLATE_SCOPE_CONFIG = templateScopeRules
const TP_SHOW_VIRTUAL_STORAGE_KEY = 'xcagi_tp_show_virtual'
const EXPORT_TEMPLATE_SOURCES = new Set([
  'db',
  'generated',
  'business-docking',
  'template-preview-replace',
  'system-default',
  'fs_scan'
])
const EXCEL_ANALYSIS_STORAGE_PREFIX = 'xcagi_excel_analysis_ctx_'
const TERM_EQUIVALENTS = {
  '产品型号': ['产品型号', '型号', '产品编码'],
  '型号': ['型号', '产品型号', '产品编码'],
  '规格': ['规格', '规格型号', '规格/kg'],
  '规格型号': ['规格型号', '规格', '规格/kg'],
  '价格': ['价格', '单价', '单价/元'],
  '单价': ['单价', '价格', '单价/元'],
  '金额': ['金额', '金额/元', '金额合计', '总金额', '金额总计'],
  '数量': ['数量', '数量(kg)', '数量/kg', '数量/件', '数量/桶', '库存数量'],
  '电话': ['电话', '联系电话', '手机号'],
  '购买单位': ['购买单位', '单位', '单位名称', '客户名称', '厂名'],
  '客户名称': ['客户名称', '购买单位', '单位名称', '厂名'],
  '金额总计': ['金额总计', '金额合计', '总金额', '金额', '合计金额'],
  '金额合计': ['金额合计', '金额总计', '总金额', '金额', '合计金额'],
  '销售金额': ['销售金额', '销售额', '销售总额', '营业额'],
  '实收款': ['实收款', '实收', '已收款', '实收金额'],
  '下欠款金额': ['下欠款金额', '下欠款', '欠款', '应收余额', '欠款金额']
}

function normalizeTerm(value) {
  return String(value || '').replace(/\s+/g, '').trim().toLowerCase()
}

export default {
  name: 'TemplatePreviewView',
  components: {
    FileUploadStep,
    FieldEditor,
    ExcelPreview,
    TemplateMediaPreview,
  },
  data() {
    return {
      activeTab: 'all',
      activeScopeTab: 'all',
      activeFormatTab: 'all',
      showVirtualPlaceholders: false,
      templates: [],
      loading: false,
      error: null,
      showCreateModal: false,
      createStep: 1,
      selectedFile: null,
      templateName: '',
      templateScope: 'orders',
      recognizedType: null,
      editorFields: [],
      editorTemplateType: 'excel',
      /** 分析接口返回的完整 preview_data（保存时做脱敏后写入） */
      analyzedPreviewData: null,
      analyzedFilePath: '',
      analyzedOriginalFilename: '',
      uploadValidationResult: null,
      showPreviewModal: false,
      previewingTemplate: null,
      showEditModal: false,
      editingTemplate: null,
      showReplaceModal: false,
      replaceSourceTemplate: null,
      replaceTargetTemplateId: '',
      replacingTemplate: false,
      gridToolFile: null,
      gridToolResult: null,
      extractingGrid: false,
      showGridToolModal: false,
      /** 用于忽略过期的后台词条补全（快速连续点「刷新」时） */
      templateListRefreshGen: 0,
      // 分析进度
      analyzing: false,
      progressStep: 1,
      progressPercent: 0,
      progressMessage: '准备上传...',
      progressTimer: null
    }
  },
  computed: {
    scopeTabs() {
      return [
        { key: 'all', label: '全部' },
        ...Object.entries(TEMPLATE_SCOPE_CONFIG).map(([scopeKey, meta]) => ({
          key: scopeKey,
          label: meta?.label || scopeKey
        }))
      ]
    },
    exportScopedTemplates() {
      const realTemplates = Array.isArray(this.templates) ? this.templates.filter(t => this.isExportTemplate(t)) : []
      const scopedExcelTemplates = realTemplates.filter(t => t.category === 'excel')
      const existingScopes = new Set(
        scopedExcelTemplates
          .map(t => this.getTemplateScopeKey(t))
          .filter(Boolean)
      )

      for (const scopeKey of Object.keys(TEMPLATE_SCOPE_CONFIG)) {
        if (!existingScopes.has(scopeKey)) {
          realTemplates.push(this.createVirtualTemplate(scopeKey))
        }
      }
      return realTemplates
    },
    filteredTemplates() {
      if (this.activeScopeTab === 'all') return this.exportScopedTemplates
      const tab = this.activeScopeTab
      return this.exportScopedTemplates.filter((t) => {
        const scopeKey = this.getTemplateScopeKey(t)
        if (t.category === 'word' && !scopeKey) {
          // 未配置 business_scope 且无法推断：与「全部」一致，在各业务分组中均可看到
          return true
        }
        return scopeKey === tab
      })
    },
    configuredTemplates() {
      return this.filteredTemplates.filter((t) => !t.virtual)
    },
    virtualPlaceholders() {
      return this.filteredTemplates.filter((t) => t.virtual)
    },
    configuredDisplayTemplates() {
      return this.configuredTemplates.filter((t) => this.matchesFormatFilter(t))
    },
    formatTabs() {
      return [
        { key: 'all', label: '全部类型' },
        ...TEMPLATE_MEDIA_ORDER.map((key) => ({
          key,
          label: TEMPLATE_MEDIA_LABELS[key],
        })),
      ]
    },
    templateMediaKindOptions() {
      return TEMPLATE_MEDIA_KINDS.map((value) => ({
        value,
        label: TEMPLATE_MEDIA_LABELS[value],
      }))
    },
    scopeOptions() {
      return Object.entries(TEMPLATE_SCOPE_CONFIG).map(([value, meta]) => ({
        value,
        label: meta.label
      }))
    },
    selectedScopeRequiredTerms() {
      return this.getRequiredTermsByScope(this.templateScope)
    },
    canProceedStep1() {
      return this.selectedFile && this.templateName.trim()
    },
    gridToolFileName() {
      if (!this.gridToolFile) return '未选择文件'
      return String(this.gridToolFile.name || '已选择文件')
    },
  },
  watch: {
    '$route.query.scope': {
      immediate: true,
      handler() {
        this.applyRouteScope()
      },
    },
    showVirtualPlaceholders(val) {
      try {
        localStorage.setItem(TP_SHOW_VIRTUAL_STORAGE_KEY, val ? '1' : '0')
      } catch (_) {
        /* ignore */
      }
    },
  },
  mounted() {
    try {
      const stored = localStorage.getItem(TP_SHOW_VIRTUAL_STORAGE_KEY)
      if (stored === '1') this.showVirtualPlaceholders = true
    } catch (_) {
      /* ignore */
    }
    this.refreshTemplates()
  },
  beforeUnmount() {
    if (this.progressTimer) {
      clearInterval(this.progressTimer)
      this.progressTimer = null
    }
  },
  methods: {
    getLatestExcelAnalysisContext() {
      try {
        const activeSessionId = String(localStorage.getItem('ai_session_id') || '').trim()
        const sessionKey = activeSessionId || 'default'
        const raw = sessionStorage.getItem(EXCEL_ANALYSIS_STORAGE_PREFIX + sessionKey)
        if (!raw) return null
        const parsed = JSON.parse(raw)
        if (!parsed || typeof parsed !== 'object') return null
        return parsed
      } catch (e) {
        console.warn('读取 Excel 分析上下文失败:', e)
        return null
      }
    },

    normalizeExcelAnalysisFields(rawFields) {
      const fields = Array.isArray(rawFields) ? rawFields : []
      return fields
        .map((field) => {
          const label = String(field?.label || field?.name || '').trim()
          if (!label) return null
          return {
            label,
            value: '',
            type: field?.type || 'dynamic'
          }
        })
        .filter(Boolean)
    },

    buildTemplatePayloadFromExcelAnalysis() {
      const ctx = this.getLatestExcelAnalysisContext()
      if (!ctx) return null
      const rawFields = Array.isArray(ctx?.fields) ? ctx.fields : []
      const previewData = ctx?.preview_data || {}
      const normalizedFields = this.normalizeExcelAnalysisFields(rawFields)
      if (!normalizedFields.length) return null

      const strippedSampleRows = stripSampleRowsKeepTemplateShape(previewData?.sample_rows, normalizedFields)
      const strippedGridPreview = stripGridPreviewData(previewData?.grid_preview, previewData?.sample_rows)
      return {
        fields: normalizedFields,
        preview_data: {
          ...previewData,
          sample_rows: strippedSampleRows,
          grid_preview: strippedGridPreview
        }
      }
    },

    sanitizeFieldsKeepTemplateShape(rawFields) {
      const normalized = this.normalizeExcelAnalysisFields(rawFields)
      if (normalized.length) return normalized
      const fallback = Array.isArray(rawFields) ? rawFields : []
      return fallback
        .map((field) => {
          const label = String(field?.label || field?.name || '').trim()
          if (!label) return null
          return {
            label,
            value: '',
            type: field?.type || 'dynamic'
          }
        })
        .filter(Boolean)
    },

    buildTemplatePayloadFromSourceTemplate(tpl) {
      if (!tpl || tpl.category !== 'excel') return null
      const sourceFields = Array.isArray(tpl.fields) ? tpl.fields : []
      const sourcePreview = tpl.preview_data && typeof tpl.preview_data === 'object'
        ? tpl.preview_data
        : {}
      const sanitizedFields = this.sanitizeFieldsKeepTemplateShape(sourceFields)
      if (!sanitizedFields.length) return null

      const strippedSampleRows = stripSampleRowsKeepTemplateShape(
        sourcePreview.sample_rows,
        sanitizedFields
      )
      const strippedGridPreview = stripGridPreviewData(
        sourcePreview.grid_preview,
        sourcePreview.sample_rows
      )
      return {
        fields: sanitizedFields,
        preview_data: {
          ...sourcePreview,
          sample_rows: strippedSampleRows,
          grid_preview: strippedGridPreview
        }
      }
    },

    applyRouteScope() {
      const queryScope = String(this.$route?.query?.scope || '').trim()
      if (queryScope && Object.prototype.hasOwnProperty.call(TEMPLATE_SCOPE_CONFIG, queryScope)) {
        this.activeScopeTab = queryScope
      } else if (!this.activeScopeTab) {
        this.activeScopeTab = 'all'
      }
    },

    async refreshTemplates() {
      this.loading = true
      this.error = null
      const refreshGen = ++this.templateListRefreshGen
      const listSignal =
        typeof AbortSignal !== 'undefined' && typeof AbortSignal.timeout === 'function'
          ? AbortSignal.timeout(120000)
          : undefined
      try {
        const res = await templatePreviewApi.listTemplates(listSignal ? { signal: listSignal } : undefined)
        if (refreshGen !== this.templateListRefreshGen) return
        if (res && res.success) {
          const templates = (res.templates || []).filter(t => {
            // 兼容后端旧版本：前端主动隐藏已软删除模板。
            return !(t && (t.is_active === 0 || t.is_active === false))
          })

          this.templates = templates
          // 列表已就绪即结束全页 loading；词条/分解在后台补全（避免 detail/decompose 慢或挂起导致一直「模板加载中」）
          this.loading = false
          void this.hydrateExcelTemplatesInBackground(refreshGen)
        } else {
          this.error = (res && res.message) || '加载失败'
        }
      } catch (err) {
        console.error('加载模板列表失败:', err)
        const msg = err && err.name === 'TimeoutError' ? '请求超时，请检查网络或后端服务' : (err.message || '未知错误')
        this.error = '加载模板列表失败：' + msg
      } finally {
        this.loading = false
      }
    },

    async hydrateExcelTemplatesInBackground(refreshGen) {
      const list = Array.isArray(this.templates) ? this.templates : []
      for (const tpl of list) {
        if (refreshGen !== this.templateListRefreshGen) return
        if (tpl.category === 'excel' && !tpl.virtual) {
          try {
            await this.hydrateTemplateTerms(tpl)
          } catch (e) {
            console.warn('后台补全模板词条失败:', e)
          }
        }
      }
    },

    async hydrateTemplateTerms(tpl) {
      if (String(tpl?.source || '').trim() === 'system-default' && Array.isArray(tpl?.fields) && tpl.fields.length > 0) {
        return
      }
      let hydratedByDetail = false
      try {
        const detailRes = await templatePreviewApi.getTemplateDetail(tpl.id)
        if (detailRes && detailRes.success && detailRes.template) {
          Object.assign(tpl, detailRes.template)
          hydratedByDetail = true
        }
      } catch (e) {
        console.warn(`获取模板 ${tpl.id} 详情失败:`, e)
      }

      const hasFields = Array.isArray(tpl.fields) && tpl.fields.length > 0
      if (hydratedByDetail && hasFields) return

      // 兜底：按“真实模板文件”分解，确保每个模板都按实际内容匹配。
      try {
        const filePath = String(tpl.file_path || tpl.path || '').trim()
        const fileName = String(tpl.filename || '').trim()
        if (!filePath && !fileName) return

        const decomposePayload = {
          sample_rows: 8
        }
        if (filePath) {
          decomposePayload.file_path = filePath
        } else {
          decomposePayload.filename = fileName
        }

        const decomposeRes = await templatePreviewApi.decomposeTemplate(decomposePayload)
        if (!decomposeRes?.success) return

        const entries = Array.isArray(decomposeRes?.decomposition?.editable_entries)
          ? decomposeRes.decomposition.editable_entries
          : []
        const sampleRows = Array.isArray(decomposeRes?.decomposition?.sample_rows)
          ? decomposeRes.decomposition.sample_rows
          : []

        let fields = entries
          .map(item => ({
            label: String(item?.name || '').trim(),
            value: '',
            type: 'dynamic'
          }))
          .filter(item => item.label)

        if (!fields.length && sampleRows.length) {
          const keys = Array.from(
            new Set(
              sampleRows.flatMap(row => Object.keys(row || {}))
            )
          )
          fields = keys.map(k => ({ label: String(k || '').trim(), value: '', type: 'dynamic' })).filter(f => f.label)
        }

        if (fields.length) {
          tpl.fields = fields
        }
        tpl.preview_data = {
          ...(tpl.preview_data || {}),
          sample_rows: sampleRows
        }
      } catch (e) {
        console.warn(`分解模板 ${tpl.id} 失败:`, e)
      }
    },

    onFileSelected(data) {
      this.selectedFile = data.selectedFile
      this.templateName = data.templateName
      this.recognizedType = data.recognizedType
    },

    closeCreateModal() {
      if (this.progressTimer) {
        clearInterval(this.progressTimer)
        this.progressTimer = null
      }
      this.showCreateModal = false
      this.resetCreateState()
    },

    resetCreateState() {
      this.createStep = 1
      this.selectedFile = null
      this.templateName = ''
      this.templateScope = 'orders'
      this.recognizedType = null
      this.editorFields = []
      this.editorTemplateType = 'excel'
      this.analyzedPreviewData = null
      this.analyzedFilePath = ''
      this.analyzedOriginalFilename = ''
      this.uploadValidationResult = null
    },

    prevStep() {
      if (this.createStep > 1) {
        this.createStep--
      }
    },

    async nextStep() {
      if (this.createStep === 1 && this.canProceedStep1) {
        const passed = await this.analyzeFile()
        if (passed) {
          this.createStep = 2
        }
      }
    },

    async analyzeFile() {
      try {
        if (!this.selectedFile) {
          await appAlert('请先选择文件')
          return false
        }

        const name = String(this.selectedFile.name || '')
        const ext = name.split('.').pop().toLowerCase()
        const uploadKind = templateMediaKindFromFilename(name)
        if (!uploadKind) {
          await appAlert('请上传办公五类模板文件：.xlsx / .xls / .docx / .csv / .pptx / .pdf')
          return false
        }
        if (uploadKind !== 'excel' && uploadKind !== 'word') {
          await appAlert(
            `${TEMPLATE_MEDIA_LABELS[uploadKind]} 模板的自动分析即将支持，当前请先用 Excel 或 Word 创建业务导出模板。`
          )
          return false
        }

        this.analyzing = true
        this.progressStep = 1
        this.progressPercent = 0
        this.progressMessage = '准备上传文件...'
        this.analyzedPreviewData = null
        this.analyzedFilePath = ''
        this.analyzedOriginalFilename = ''

        const formData = new FormData()
        formData.append('file', this.selectedFile)
        formData.append('template_name', this.templateName)
        formData.append('template_scope', this.templateScope)

        const res = await templatePreviewApi.analyzeTemplate(formData)

        if (res && res.success) {
          const kind = String(res.template_type || '').toLowerCase()
          if (kind !== 'excel' && kind !== 'word') {
            this.analyzing = false
            await appAlert('本页仅支持创建 Excel 或 Word 导出模板')
            return false
          }

          const validation = this.validateUploadedTemplate(res)
          this.uploadValidationResult = validation
          if (!validation.valid) {
            this.analyzing = false
            await appAlert(`模板词条校验未通过，缺少：${validation.missing.join('、')}`)
            return false
          }

          const taskId = res.task_id
          if (taskId) {
            await this.pollProgress(taskId)
          } else {
            this.analyzing = false
          }

          const preview = res.preview_data && typeof res.preview_data === 'object' ? { ...res.preview_data } : {}
          this.analyzedPreviewData = preview
          this.analyzedFilePath = String(preview.file_path || '').trim()
          this.analyzedOriginalFilename = String(preview.original_filename || this.selectedFile.name || '').trim()

          this.editorFields = Array.isArray(res.fields) ? [...res.fields] : []
          this.editorTemplateType = kind === 'word' ? 'word' : 'excel'

          await new Promise(resolve => setTimeout(resolve, 300))
          return true
        }

        this.analyzing = false
        await appAlert((res && res.message) || '分析失败')
        return false
      } catch (err) {
        this.analyzing = false
        await appAlert('分析失败：' + (err && err.message ? err.message : String(err)))
        return false
      }
    },

    async pollProgress(taskId) {
      if (this.progressTimer) {
        clearInterval(this.progressTimer)
        this.progressTimer = null
      }
      return new Promise((resolve) => {
        const pollInterval = setInterval(async () => {
          try {
            const data = await templatePreviewApi.getAnalysisProgress(taskId)

            if (data.success) {
              this.progressPercent = data.progress
              this.progressStep = data.step
              this.progressMessage = data.message || '分析中...'

              if (data.completed) {
                clearInterval(pollInterval)
                this.progressTimer = null
                this.analyzing = false
                resolve()
              }
            }
          } catch (err) {
            console.error('轮询进度失败:', err)
          }
        }, 1000)

        this.progressTimer = pollInterval
      })
    },

    onUpdateField(index, field) {
      this.editorFields.splice(index, 1, field)
    },

    onDeleteField(index) {
      this.editorFields.splice(index, 1)
    },

    onAddField(field) {
      this.editorFields.push(field)
    },

    onFieldsChange(fields) {
      this.editorFields = [...fields]
    },
    
    onFieldChange() {},

    onFieldsUpdate(fields) {
      this.editorFields = fields
    },

    async saveTemplate() {
      try {
        const fields = Array.isArray(this.editorFields) ? [...this.editorFields] : []
        const scopeMeta = TEMPLATE_SCOPE_CONFIG[this.templateScope] || TEMPLATE_SCOPE_CONFIG.orders
        const category = normalizeTemplateMediaKind(this.editorTemplateType, 'excel')
        const isWord = category === 'word'

        const basePreview =
          this.analyzedPreviewData && typeof this.analyzedPreviewData === 'object'
            ? { ...this.analyzedPreviewData }
            : {}

        let preview_data
        if (isWord) {
          preview_data = {
            ...basePreview,
            placeholders: Array.isArray(basePreview.placeholders) ? [...basePreview.placeholders] : []
          }
        } else {
          const strippedSampleRows = stripSampleRowsKeepTemplateShape(
            basePreview.sample_rows,
            fields
          )
          const strippedGrid = stripGridPreviewData(basePreview.grid_preview, basePreview.sample_rows)
          preview_data = {
            ...basePreview,
            sample_rows: strippedSampleRows,
            grid_preview: strippedGrid
          }
        }

        const file_path =
          String(this.analyzedFilePath || preview_data.file_path || '').trim() || undefined

        const saveData = {
          name: this.templateName,
          category,
          template_type: scopeMeta.templateType,
          business_scope: this.templateScope,
          fields,
          preview_data,
          file_path,
          original_filename:
            this.analyzedOriginalFilename ||
            String(this.selectedFile?.name || preview_data.original_filename || '').trim() ||
            undefined,
          source: 'generated'
        }

        const res = await templatePreviewApi.createTemplate(saveData)

        if (res && res.success) {
          await appAlert('模板保存成功！')
          this.closeCreateModal()
          this.refreshTemplates()
          window.dispatchEvent(new CustomEvent('xcagi:templates-updated', { detail: { source: 'template-preview' } }))
        } else {
          throw new Error((res && res.message) || '保存失败')
        }
      } catch (err) {
        await appAlert('保存失败：' + (err.message || '未知错误'))
      }
    },

    previewTemplate(tpl) {
      this.previewingTemplate = tpl
      this.showPreviewModal = true
    },

    closePreviewModal() {
      this.showPreviewModal = false
      this.previewingTemplate = null
    },

    async openTemplateTarget(tpl) {
      if (tpl.category === 'label') {
        await appAlert('打印功能开发中...')
      } else if (tpl.category === 'word') {
        const p = String(tpl.file_path || tpl.path || '').trim()
        await appAlert(p ? `请在资源管理器中打开：\n${p}` : '未记录 Word 模板文件路径')
      } else {
        const p = String(tpl.file_path || tpl.path || '').trim()
        await appAlert(
          p
            ? `Excel 模板文件路径（请在资源管理器中打开）：\n${p}`
            : '未记录 Excel 模板文件路径；可在「编辑」中核对元数据或重新上传分析。'
        )
      }
    },

    editTemplate(tpl) {
      this.editingTemplate = { ...tpl }
      this.showEditModal = true
    },

    closeEditModal() {
      this.showEditModal = false
      this.editingTemplate = null
    },

    async openReplaceTemplateDialog(sourceTemplate) {
      const candidates = this.getReplaceCandidates(sourceTemplate)
      if (!candidates.length) {
        await appAlert('暂无同业务范围可替代模板')
        return
      }
      this.replaceSourceTemplate = sourceTemplate
      this.replaceTargetTemplateId = candidates[0].id
      this.showReplaceModal = true
    },

    closeReplaceModal() {
      this.showReplaceModal = false
      this.replaceSourceTemplate = null
      this.replaceTargetTemplateId = ''
      this.replacingTemplate = false
    },

    getReplaceCandidates(sourceTemplate) {
      if (!sourceTemplate || sourceTemplate.category !== 'excel') return []
      const sourceScopes = this.getMatchedScopeKeys(sourceTemplate)
      if (!sourceScopes.length) return []
      return this.exportScopedTemplates.filter((tpl) => {
        if (!tpl || tpl.virtual || tpl.category !== 'excel') return false
        if (String(tpl.id) === String(sourceTemplate.id)) return false
        if (!String(tpl.id || '').startsWith('db:')) return false
        const targetScopes = this.getMatchedScopeKeys(tpl)
        return targetScopes.some(scope => sourceScopes.includes(scope))
      })
    },

    isExportTemplate(tpl) {
      if (!tpl || tpl.virtual) return false
      if (tpl.category === 'label') return false
      const kind = this.getTemplateMediaKind(tpl)
      if (!isTemplateMediaKind(kind)) return false
      const source = String(tpl.source || '').trim()
      if (EXPORT_TEMPLATE_SOURCES.has(source)) return true
      if (String(tpl.id || '').startsWith('db:')) return true
      return false
    },

    getTemplateMediaKind(tpl) {
      if (!tpl) return 'excel'
      if (tpl.category === 'label') return 'label'
      if (isTemplateMediaKind(tpl.category)) return tpl.category
      const inferred = templateMediaKindFromFilename(
        tpl.filename || tpl.original_filename || tpl.name
      )
      if (inferred) return inferred
      return normalizeTemplateMediaKind(tpl.category, 'excel')
    },

    matchesFormatFilter(tpl) {
      if (this.activeFormatTab === 'all') return true
      return this.getTemplateMediaKind(tpl) === this.activeFormatTab
    },

    buildTemplatePreviewBind(tpl, overrides = {}) {
      if (!tpl) return {}
      const kind = this.getTemplateMediaKind(tpl)
      const isLabel = kind === 'label'
      const showExcelGrid =
        kind === 'excel' && (!tpl.virtual || this.canPreviewVirtualTemplate(tpl))
      const requiredTerms =
        tpl.virtual && tpl.business_scope
          ? this.getRequiredTermsByScope(tpl.business_scope)
          : []
      let statusHint = ''
      if (kind !== 'excel' && kind !== 'label' && !tpl.virtual) {
        statusHint = '预览占位 · 完整渲染待接入'
        if (tpl.file_path || tpl.path) {
          statusHint += ` · ${tpl.file_path || tpl.path}`
        }
      }
      return {
        template: tpl,
        mediaKind: kind,
        virtual: Boolean(tpl.virtual),
        showExcelGrid,
        fields: this.getTemplateFields(tpl, isLabel ? 'label' : kind),
        sampleRows: this.getTemplateSampleRows(tpl),
        gridData: this.getTemplateGridData(tpl),
        excelTitle: this.getExcelPreviewTitle(tpl),
        requiredTerms,
        displayName: String(tpl.filename || tpl.name || '').trim(),
        statusHint,
        rows: overrides.rows || 5,
        columns: overrides.columns || 5,
        labelWidth: overrides.labelWidth || 280,
        labelHeight: overrides.labelHeight || 180,
        compact: Boolean(overrides.compact),
      }
    },

    getTemplateSourceLabel(tpl) {
      const source = String(tpl?.source || 'db').trim()
      const sourceLabelMap = {
        db: '数据库',
        generated: '生成',
        'business-docking': '业务对接',
        'template-preview-replace': '模板替代',
        'system-default': '系统默认',
        fs_scan: '本地扫描（项目目录）'
      }
      return sourceLabelMap[source] || source
    },

    async confirmReplaceTemplate() {
      if (!this.replaceSourceTemplate || !this.replaceTargetTemplateId) return
      this.replacingTemplate = true
      try {
        // 优先使用“分析Excel”工具上下文；无上下文时对源模板执行同套去数据清洗逻辑。
        const excelAnalysisPayload = this.buildTemplatePayloadFromExcelAnalysis()
        const sourceSanitizedPayload = this.buildTemplatePayloadFromSourceTemplate(this.replaceSourceTemplate)
        const replacementPayload = excelAnalysisPayload || sourceSanitizedPayload
        const replacementFields = replacementPayload?.fields || this.getTemplateFields(this.replaceSourceTemplate, 'excel')
        const replacementPreviewData = replacementPayload?.preview_data || { ...(this.replaceSourceTemplate.preview_data || {}) }
        const sourceScopes = this.getMatchedScopeKeys(this.replaceSourceTemplate)
        const businessScope = sourceScopes[0] || this.replaceSourceTemplate.business_scope || ''
        const payload = {
          id: this.replaceTargetTemplateId,
          name: this.replaceSourceTemplate.name,
          template_type: this.replaceSourceTemplate.template_type || this.getTemplateTypeLabel(this.replaceSourceTemplate),
          business_scope: businessScope,
          fields: replacementFields,
          preview_data: replacementPreviewData,
          source: 'template-preview-replace',
          enforce_scope_match: true,
          replace_mode: true
        }
        const res = await templatePreviewApi.replaceTemplateById(payload)
        if (!res?.success) {
          throw new Error(res?.message || '替代失败')
        }
        if (replacementPayload) {
          await appAlert('模板替代成功（已执行模板/数据分离：去除数据，仅保留模板结构）')
        } else {
          await appAlert('模板替代成功')
        }
        this.closeReplaceModal()
        this.refreshTemplates()
        window.dispatchEvent(new CustomEvent('xcagi:templates-updated', { detail: { source: 'template-replace' } }))
      } catch (err) {
        await appAlert('模板替代失败：' + (err?.message || '未知错误'))
      } finally {
        this.replacingTemplate = false
      }
    },

    async saveTemplateEdit() {
      if (!this.editingTemplate) return

      try {
        const res = await templatePreviewApi.updateTemplate({
          id: this.editingTemplate.id,
          name: this.editingTemplate.name,
          category: this.editingTemplate.category
        })

        if (res && res.success) {
          await appAlert('更新成功！')
          this.closeEditModal()
          this.refreshTemplates()
          window.dispatchEvent(new CustomEvent('xcagi:templates-updated', { detail: { source: 'template-edit' } }))
        } else {
          throw new Error((res && res.message) || '更新失败')
        }
      } catch (err) {
        await appAlert('更新失败：' + (err.message || '未知错误'))
      }
    },

    openLabelEditor() {
      pushErpPage(this.$router, {
        path: '/label-editor',
        query: {
          mode: 'create',
          autoUpload: '1'
        }
      })
    },

    async confirmDeleteTemplate(tpl) {
      if (!this.canDeleteTemplate(tpl)) {
        await appAlert('当前模板不支持删除');
        return;
      }
      if (await appConfirm(`确定要删除模板 "${tpl.name}" 吗？`, { danger: true })) {
        this.deleteTemplate(tpl)
      }
    },

    async deleteTemplate(tpl) {
      try {
        const res = await templatePreviewApi.deleteTemplate({ id: tpl.id })

        if (res && res.success) {
          this.templates = (this.templates || []).filter(item => String(item?.id || '') !== String(tpl?.id || ''))
          await appAlert('删除成功！')
          this.refreshTemplates()
        } else {
          throw new Error((res && res.message) || '删除失败')
        }
      } catch (err) {
        await appAlert('删除失败：' + (err.message || '未知错误'))
      }
    },

    canDeleteTemplate(tpl) {
      if (!tpl || tpl.virtual) return false
      const id = String(tpl.id || '').trim()
      return id.startsWith('db:') || id.startsWith('fs:')
    },

    getTemplateFields(tpl, type) {
      if (tpl.fields && tpl.fields.length > 0) {
        return tpl.fields
      }

      if (type === 'label') {
        return [
          { label: '品名', value: 'XX运动鞋', type: 'fixed' },
          { label: '货号', value: '1635', type: 'dynamic' },
          { label: '颜色', value: '白色', type: 'dynamic' },
          { label: '码段', value: '00001', type: 'dynamic' },
          { label: '等级', value: '合格品', type: 'fixed' },
          { label: '统一零售价', value: '¥199', type: 'dynamic' }
        ]
      }

      return [
        { label: '产品型号', value: '' },
        { label: '产品名称', value: '' },
        { label: '数量', value: '' },
        { label: '单价', value: '' },
        { label: '金额', value: '' }
      ]
    },

    getTemplateSampleRows(tpl) {
      if (tpl.preview_data && tpl.preview_data.sample_rows) {
        return tpl.preview_data.sample_rows
      }
      return []
    },

    getTemplateGridData(tpl) {
      return tpl?.preview_data?.grid_preview || null
    },

    getExcelPreviewTitle(tpl) {
      if (!tpl) return 'Excel 模板预览'
      const text = tpl.template_type || tpl.name || 'Excel 模板'
      return `${text}预览`
    },

    getScopeMeta(scopeKey) {
      return TEMPLATE_SCOPE_CONFIG[scopeKey] || null
    },

    getRequiredTermsByScope(scopeKey) {
      const meta = this.getScopeMeta(scopeKey)
      return meta ? meta.requiredTerms : []
    },

    getEquivalentNormalizedTerms(term) {
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
    },

    hasEquivalentTerm(termSet, requiredTerm) {
      if (!(termSet instanceof Set)) return false
      const candidates = this.getEquivalentNormalizedTerms(requiredTerm)
      return candidates.some(candidate => termSet.has(candidate))
    },

    inferWordTemplateScopeKey(tpl) {
      const id = String(tpl?.id || '').toLowerCase()
      const name = String(tpl?.name || '').toLowerCase()
      const fn = String(tpl?.filename || '').toLowerCase()
      const blob = `${id} ${name} ${fn}`
      if (/price_list|pricelist|价目|价格表|产品目录/.test(blob)) return 'products'
      if (/sales_cn|contract|合同|报价/.test(blob)) return 'orders'
      if (/出货记录|shipment.?record|delivery.?record/.test(blob)) return 'shipmentRecords'
      if (/customer|客户名录|客户管理/.test(blob)) return 'customers'
      if (/material|原材料|库存/.test(blob)) return 'materials'
      if (/summary|汇总统计|合计汇总/.test(blob)) return 'shipmentSummary'
      if (/sales.?report|销售报表|营收/.test(blob)) return 'salesReport'
      return ''
    },

    getTemplateScopeKey(tpl) {
      if (tpl?.category === 'word') {
        const explicitScope = String(tpl?.business_scope || '').trim()
        if (explicitScope && Object.prototype.hasOwnProperty.call(TEMPLATE_SCOPE_CONFIG, explicitScope)) {
          return explicitScope
        }
        const inferred = this.inferWordTemplateScopeKey(tpl)
        if (inferred && Object.prototype.hasOwnProperty.call(TEMPLATE_SCOPE_CONFIG, inferred)) {
          return inferred
        }
        return ''
      }
      const explicitScope = String(tpl?.business_scope || '').trim()
      if (explicitScope && Object.prototype.hasOwnProperty.call(TEMPLATE_SCOPE_CONFIG, explicitScope)) {
        return explicitScope
      }
      const matched = this.getMatchedScopeKeys(tpl)
      return matched[0] || ''
    },

    getTemplateScopeLabel(tpl) {
      const scopeKey = this.getTemplateScopeKey(tpl)
      const meta = this.getScopeMeta(scopeKey)
      return (meta?.label || scopeKey || '未分类')
    },

    getCardTypeLabel(tpl) {
      if (!tpl) return '模板'
      const kind = this.getTemplateMediaKind(tpl)
      if (kind === 'label') return '标签'
      if (isTemplateMediaKind(kind)) return TEMPLATE_MEDIA_LABELS[kind]
      return '模板'
    },

    getCardSurfaceClass(tpl) {
      if (!tpl) return ''
      if (tpl.virtual) return 'tp-card--virtual'
      const kind = this.getTemplateMediaKind(tpl)
      if (kind === 'label') return 'tp-card--label'
      return templateMediaCardClass(kind)
    },

    getCardMetaLine(tpl) {
      if (!tpl) return ''
      if (tpl.virtual) return '未配置 · 可上传办公五类模板'
      const parts = [this.getTemplateSourceLabel(tpl)]
      if (tpl.template_type) parts.push(this.getTemplateTypeLabel(tpl))
      return parts.filter(Boolean).join(' · ')
    },

    getCardStatusLine(tpl) {
      if (!tpl || tpl.virtual) return ''
      if (this.getTemplateMediaKind(tpl) === 'excel') {
        const coverage = this.getTemplateCoverage(tpl)
        if (coverage) {
          const ok = coverage.matchedCount >= coverage.requiredCount
          if (!ok && coverage.missing?.length) {
            return `词条 ${coverage.matchedCount}/${coverage.requiredCount} · 缺：${coverage.missing.slice(0, 4).join('、')}${coverage.missing.length > 4 ? '…' : ''}`
          }
          const matched = this.getMatchedScopeLabels(tpl)
          if (matched.length) return `词条完整 · 适用：${matched.join('、')}`
          return '词条未匹配当前业务'
        }
      }
      const kind = this.getTemplateMediaKind(tpl)
      if (kind !== 'excel' && kind !== 'label') {
        if (tpl.filename) return String(tpl.filename)
        return `${TEMPLATE_MEDIA_LABELS[kind] || kind} 文档`
      }
      return ''
    },

    getScopeIconClass(scopeKey) {
      const iconMap = {
        orders: 'fa-file-text-o',
        shipmentRecords: 'fa-list-alt',
        products: 'fa-cubes',
        materials: 'fa-flask',
        customers: 'fa-address-book-o'
      }
      return iconMap[String(scopeKey || '')] || 'fa-file-text-o'
    },

    canPreviewVirtualTemplate(tpl) {
      if (!tpl || tpl.category !== 'excel') return false
      const fields = this.getTemplateFields(tpl, 'excel')
      const sampleRows = this.getTemplateSampleRows(tpl)
      const gridData = this.getTemplateGridData(tpl)
      return (Array.isArray(fields) && fields.length > 0) && (
        (Array.isArray(sampleRows) && sampleRows.length > 0) ||
        (gridData && Array.isArray(gridData.rows) && gridData.rows.length > 0)
      )
    },

    createVirtualTemplate(scopeKey) {
      const meta = this.getScopeMeta(scopeKey) || { label: '业务模板', templateType: '发货单', requiredTerms: [] }
      const requiredTerms = Array.isArray(meta.requiredTerms) ? meta.requiredTerms : []
      // 未上传真实模板时只保留"必备词条骨架"，不再塞入 sample_rows/grid_preview 这些假样例数据，
      // 这样 `canPreviewVirtualTemplate` 会判为 false，前端会展示"待上传 Excel 模板 + 必备词条"的占位卡片，
      // 而不是误导性的 M001/示例产品 预览网格。
      return {
        id: `virtual:${scopeKey}`,
        name: `${meta.label}模板`,
        category: 'excel',
        template_type: meta.templateType,
        business_scope: scopeKey,
        source: 'virtual',
        virtual: true,
        fields: requiredTerms.map(term => ({ label: term, value: '', type: 'dynamic' })),
        preview_data: {
          sample_rows: [],
          sheet_name: String(meta.templateType || '导出模板'),
          grid_preview: null
        }
      }
    },

    extractTemplateTermSet(fields, previewData) {
      const terms = new Set()
      for (const field of fields || []) {
        terms.add(normalizeTerm(field?.label))
        terms.add(normalizeTerm(field?.name))
        terms.add(normalizeTerm(field?.value))
      }
      const cells = previewData?.cells || {}
      for (const key of Object.keys(cells)) {
        const cellValue = cells[key]?.value
        terms.add(normalizeTerm(cellValue))
      }
      const sampleRows = Array.isArray(previewData?.sample_rows) ? previewData.sample_rows : []
      for (const row of sampleRows) {
        for (const key of Object.keys(row || {})) {
          terms.add(normalizeTerm(key))
          terms.add(normalizeTerm(row?.[key]))
        }
      }
      const ph = previewData?.placeholders
      if (Array.isArray(ph)) {
        for (const item of ph) {
          terms.add(normalizeTerm(item))
        }
      }
      return terms
    },

    extractTemplateDisplayTerms(fields, previewData) {
      const displayTerms = []
      const pushTerm = (v) => {
        const text = String(v || '').trim()
        if (!text) return
        if (!displayTerms.includes(text)) {
          displayTerms.push(text)
        }
      }
      for (const field of fields || []) {
        pushTerm(field?.label)
        pushTerm(field?.name)
      }
      const cells = previewData?.cells || {}
      for (const key of Object.keys(cells)) {
        pushTerm(cells[key]?.value)
      }
      const sampleRows = Array.isArray(previewData?.sample_rows) ? previewData.sample_rows : []
      for (const row of sampleRows) {
        for (const key of Object.keys(row || {})) {
          pushTerm(key)
        }
      }
      const ph = previewData?.placeholders
      if (Array.isArray(ph)) {
        for (const item of ph) {
          pushTerm(item)
        }
      }
      return displayTerms
    },

    getTemplateDisplayTermsText(tpl) {
      const terms = this.extractTemplateDisplayTerms(tpl?.fields, tpl?.preview_data)
      if (!terms.length) return '无'
      const maxShow = 8
      if (terms.length <= maxShow) return terms.join('、')
      return `${terms.slice(0, maxShow).join('、')} 等 ${terms.length} 项`
    },

    getTemplateTypeLabel(tpl) {
      if (tpl?.category === 'word') {
        const scopeKey = this.getTemplateScopeKey(tpl)
        const meta = this.getScopeMeta(scopeKey)
        const suffix = meta?.label || scopeKey || '业务'
        const tt = String(tpl?.template_type || '').trim()
        if (tt && tt.toLowerCase() !== 'excel') {
          return `Word · ${tt}`
        }
        return `Word · ${suffix}`
      }
      const originalType = String(tpl?.template_type || '').trim()
      if (originalType && originalType.toLowerCase() !== 'excel') {
        return originalType
      }

      const matchedScopeKeys = this.getMatchedScopeKeys(tpl)
      if (!matchedScopeKeys.length) {
        return originalType || 'Excel'
      }

      const scopeMeta = this.getScopeMeta(matchedScopeKeys[0])
      return scopeMeta?.templateType || scopeMeta?.label || originalType || 'Excel'
    },

    getMatchedScopeKeys(tpl) {
      if (tpl?.virtual) return []
      const explicitScope = String(tpl?.business_scope || '').trim()
      if (explicitScope && Object.prototype.hasOwnProperty.call(TEMPLATE_SCOPE_CONFIG, explicitScope)) {
        return [explicitScope]
      }
      if (tpl?.category !== 'excel' && tpl?.category !== 'word') return []
      const termSet = this.extractTemplateTermSet(tpl?.fields, tpl?.preview_data)
      const matched = []
      for (const scopeKey of Object.keys(TEMPLATE_SCOPE_CONFIG)) {
        const required = this.getRequiredTermsByScope(scopeKey)
        if (required.length && required.every(term => this.hasEquivalentTerm(termSet, term))) {
          matched.push(scopeKey)
        }
      }
      return matched
    },

    getMatchedScopeLabels(tpl) {
      return this.getMatchedScopeKeys(tpl)
        .map(scopeKey => this.getScopeMeta(scopeKey)?.label)
        .filter(Boolean)
    },

    getTemplateCoverage(tpl) {
      if (tpl?.category !== 'excel' && tpl?.category !== 'word') return null
      const matchedScopeKeys = this.getMatchedScopeKeys(tpl)
      if (!matchedScopeKeys.length) return null
      const scope = matchedScopeKeys[0]
      const required = this.getRequiredTermsByScope(scope)
      const termSet = this.extractTemplateTermSet(tpl?.fields, tpl?.preview_data)
      const missing = required.filter(term => !this.hasEquivalentTerm(termSet, term))
      return {
        scope,
        requiredCount: required.length,
        missing,
        matchedCount: required.length - missing.length
      }
    },

    validateUploadedTemplate(analyzeResult) {
      const kind = String(analyzeResult?.template_type || '').toLowerCase()
      if (kind !== 'excel' && kind !== 'word') {
        return { valid: false, missing: ['仅支持 Excel 或 Word 模板'] }
      }
      const required = this.getRequiredTermsByScope(this.templateScope)
      if (!required.length) {
        return { valid: true, missing: [] }
      }
      const termSet = this.extractTemplateTermSet(analyzeResult?.fields, analyzeResult?.preview_data)
      const missing = required.filter(term => !this.hasEquivalentTerm(termSet, term))
      return {
        valid: missing.length === 0,
        missing
      }
    },

    openCreateModal() {
      this.resetCreateState()
      this.showCreateModal = true
    },

    startCreateForScope(scopeKey) {
      const meta = this.getScopeMeta(scopeKey)
      this.resetCreateState()
      this.templateScope = scopeKey || 'orders'
      if (meta && !this.templateName) {
        this.templateName = `${meta.label}模板`
      }
      this.showCreateModal = true
    },

    triggerGridToolFilePick() {
      this.$refs.gridToolFileInput?.click()
    },

    onGridToolFileSelected(event) {
      this.gridToolFile = event?.target?.files?.[0] || null
    },

    clearGridToolFile() {
      this.gridToolFile = null
      const input = this.$refs.gridToolFileInput
      if (input) input.value = ''
    },

    async extractGridFromExcel() {
      if (!this.gridToolFile) {
        await appAlert('请先选择 Excel 文件')
        return
      }
      this.extractingGrid = true
      try {
        const formData = new FormData()
        formData.append('file', this.gridToolFile)
        const res = await templatePreviewApi.extractGrid(formData)
        if (!res?.success) {
          throw new Error(res?.message || '提取失败')
        }
        this.gridToolResult = res
        this.showGridToolModal = true
      } catch (err) {
        await appAlert('网格提取失败：' + (err?.message || '未知错误'))
      } finally {
        this.extractingGrid = false
      }
    },

    openGridToolPreview() {
      if (!this.gridToolResult) return
      this.showGridToolModal = true
    }
  }
}
</script>

<style scoped>
.tp-page-view {
  width: 100%;
  max-width: 100%;
  box-sizing: border-box;
}

.tp-page {
  width: 100%;
  max-width: 100%;
  margin: 0;
  box-sizing: border-box;
}

.tp-hero {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px 16px;
  margin-bottom: 16px;
}

.tp-title {
  margin: 0;
  font-size: 22px;
  font-weight: 700;
  color: #0f172a;
  letter-spacing: -0.02em;
}

.tp-lead {
  margin: 6px 0 0;
  max-width: 40rem;
  font-size: 13px;
  line-height: 1.55;
}

.tp-hero-actions {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
}

.tp-toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px 12px;
  margin-bottom: 12px;
}

.tp-filter-pills {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  flex: 1 1 280px;
  min-width: 0;
}

.tp-pill {
  border: 1px solid rgba(203, 213, 225, 0.9);
  background: #fff;
  color: #475569;
  font-size: 12px;
  font-weight: 600;
  padding: 6px 12px;
  border-radius: 999px;
  cursor: pointer;
  transition: background 0.15s ease, border-color 0.15s ease, color 0.15s ease;
}

.tp-pill:hover {
  border-color: rgba(11, 114, 217, 0.35);
  color: #0b3e73;
}

.tp-pill--active {
  background: linear-gradient(135deg, rgba(219, 234, 254, 0.96), rgba(224, 242, 254, 0.88));
  border-color: rgba(11, 114, 217, 0.45);
  color: #0b3e73;
}

.tp-toolbar__right {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: flex-end;
  gap: 10px 14px;
  flex: 0 1 auto;
  margin-left: auto;
}

.tp-count {
  font-size: 12px;
  white-space: nowrap;
}

.tp-toggle {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #475569;
  cursor: pointer;
  user-select: none;
}

.tp-toggle input {
  margin: 0;
}

.tp-format-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 12px;
  width: 100%;
}

.tp-format-pill {
  border: 1px dashed rgba(203, 213, 225, 0.95);
  background: #fff;
  color: #64748b;
  font-size: 11px;
  font-weight: 600;
  padding: 4px 10px;
  border-radius: 8px;
  cursor: pointer;
}

.tp-format-pill--active {
  border-style: solid;
  border-color: rgba(11, 114, 217, 0.4);
  color: #0b3e73;
  background: #f8fafc;
}

.tp-stash {
  margin-top: 18px;
  width: 100%;
  border: 1px solid rgba(203, 213, 225, 0.85);
  border-radius: 10px;
  background: #f8fafc;
}

.tp-stash-summary {
  padding: 10px 14px;
  font-size: 13px;
  font-weight: 600;
  color: #475569;
  cursor: pointer;
  list-style: none;
}

.tp-stash-summary::-webkit-details-marker {
  display: none;
}

.tp-stash-list {
  list-style: none;
  margin: 0;
  padding: 0 10px 10px;
}

.tp-stash-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 8px;
  border-top: 1px solid #e2e8f0;
}

.tp-stash-row:first-child {
  border-top: none;
}

.tp-stash-row__main {
  min-width: 0;
  flex: 1;
}

.tp-stash-row__title {
  display: block;
  font-size: 13px;
  font-weight: 600;
  color: #0f172a;
}

.tp-stash-row__meta {
  display: block;
  margin-top: 4px;
  font-size: 11px;
  line-height: 1.45;
}

.tp-advanced {
  width: 100%;
  margin-bottom: 16px;
  border: 1px solid rgba(203, 213, 225, 0.85);
  border-radius: 10px;
  background: #f8fafc;
}

.tp-advanced-summary {
  padding: 10px 14px;
  font-size: 13px;
  font-weight: 600;
  color: #475569;
  cursor: pointer;
  list-style: none;
}

.tp-advanced-summary::-webkit-details-marker {
  display: none;
}

.tp-advanced-body {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px 10px;
  padding: 0 14px 12px;
}

.tp-file-field {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  flex: 1 1 280px;
  min-width: 0;
  max-width: 100%;
  padding: 6px 10px;
  border-radius: 8px;
  border: 1px solid rgba(203, 213, 225, 0.9);
  background: #fff;
}

.tp-file-field__input {
  position: absolute;
  width: 0.1px;
  height: 0.1px;
  opacity: 0;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
}

.tp-file-field__pick {
  flex-shrink: 0;
}

.tp-file-field__pick .fa {
  margin-right: 4px;
}

.tp-file-field__name {
  flex: 1 1 120px;
  min-width: 0;
  font-size: 12px;
  line-height: 1.4;
  color: #334155;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.tp-file-field__name--empty {
  color: #94a3b8;
}

.tp-file-field__clear {
  flex-shrink: 0;
  color: #64748b;
}

.tp-advanced-meta {
  width: 100%;
  margin: 0;
  font-size: 12px;
}

.tp-state {
  padding: 32px 16px;
  text-align: center;
  font-size: 14px;
}

.tp-state--error {
  color: #b42318;
}

.tp-grid {
  display: grid;
  width: 100%;
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 300px), 1fr));
  gap: clamp(12px, 1.2vw, 18px);
  align-items: stretch;
}

.tp-card {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-width: 0;
  height: 100%;
  padding: 14px;
  border-radius: 12px;
  border: 1px solid rgba(203, 213, 225, 0.85);
  background: #fff;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
  transition: box-shadow 0.15s ease, border-color 0.15s ease;
}

.tp-card:hover {
  border-color: rgba(11, 114, 217, 0.28);
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.06);
}

.tp-card--word {
  border-color: rgba(43, 87, 154, 0.22);
  background: linear-gradient(180deg, #f8fbff 0%, #fff 55%);
}

.tp-card--virtual {
  border-style: dashed;
  background: #fafbfc;
}

.tp-card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.tp-card-type {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: #0b72d9;
}

.tp-card--word .tp-card-type {
  color: #2b579a;
}

.tp-card--csv {
  border-color: rgba(3, 105, 161, 0.22);
  background: linear-gradient(180deg, #f0f9ff 0%, #fff 55%);
}

.tp-card--csv .tp-card-type {
  color: #0369a1;
}

.tp-card--ppt {
  border-color: rgba(194, 65, 12, 0.22);
  background: linear-gradient(180deg, #fff7ed 0%, #fff 55%);
}

.tp-card--ppt .tp-card-type {
  color: #c2410c;
}

.tp-card--pdf {
  border-color: rgba(185, 28, 28, 0.22);
  background: linear-gradient(180deg, #fef2f2 0%, #fff 55%);
}

.tp-card--pdf .tp-card-type {
  color: #b91c1c;
}

.tp-card--virtual .tp-card-type {
  color: #64748b;
}

.tp-scope {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 999px;
  background: #f1f5f9;
  color: #475569;
  border: 1px solid #e2e8f0;
  white-space: nowrap;
}

.tp-card-name {
  margin: 0;
  font-size: 15px;
  font-weight: 650;
  color: #0f172a;
  line-height: 1.35;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.tp-card-meta {
  margin: 0;
  font-size: 12px;
  line-height: 1.4;
}

.tp-card-status {
  margin: 0;
  font-size: 12px;
  line-height: 1.45;
  color: #b45309;
}

.tp-card-preview {
  flex: 1 1 auto;
  min-height: 108px;
  border-radius: 8px;
  background: #f8fafc;
  border: 1px solid #eef2f7;
  padding: 6px;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
}

.tp-card-preview :deep(.template-media-preview),
.tp-card-preview :deep(.excel-preview) {
  width: 100%;
  max-width: 100%;
}

.tp-card-placeholder {
  width: 100%;
  min-height: 96px;
  padding: 12px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 6px;
  text-align: center;
  color: #64748b;
  font-size: 12px;
}

.tp-card-placeholder--word {
  gap: 8px;
  color: #2b579a;
}

.tp-card-placeholder--word .fa {
  font-size: 28px;
  opacity: 0.85;
}

.tp-placeholder-title {
  font-weight: 600;
  color: #334155;
}

.tp-placeholder-terms {
  line-height: 1.45;
  max-width: 100%;
}

.tp-card-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 4px;
}

.tp-btn-danger {
  color: #b42318;
  border-color: rgba(220, 38, 38, 0.35);
}

.tp-btn-danger:hover {
  background: #fef2f2;
}

.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: white;
  border-radius: 8px;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 15px 20px;
  border-bottom: 1px solid #e1e4e8;
}

.modal-header h3 {
  margin: 0;
  font-size: 18px;
}

.modal-close {
  background: none;
  border: none;
  font-size: 24px;
  cursor: pointer;
  color: #6c757d;
}

.modal-close:hover {
  color: #343a40;
}

.modal-body {
  padding: 20px;
  max-height: 60vh;
  overflow-y: auto;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding: 15px 20px;
  border-top: 1px solid #e1e4e8;
}

.create-step {
  min-height: 300px;
}

.scope-selector-row {
  margin-bottom: 14px;
}

.scope-selector-row label {
  display: block;
  margin-bottom: 6px;
  font-weight: 600;
  color: #2c3e50;
}

.scope-required-terms {
  margin-top: 6px;
  font-size: 12px;
}

.validation-warning {
  margin-top: 10px;
  padding: 10px 12px;
  border-radius: 6px;
  border: 1px solid #f5c6cb;
  background: #fff5f5;
  color: #a94442;
  font-size: 12px;
}

.virtual-template-preview {
  width: 100%;
  min-height: 140px;
  border: 1px dashed #c5d3de;
  border-radius: 6px;
  background: #f7fafc;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 8px;
  padding: 12px;
  color: #4f6575;
}

.virtual-template-title {
  font-size: 14px;
  font-weight: 600;
}

.virtual-template-terms {
  font-size: 12px;
  line-height: 1.5;
}

.preview-modal-content {
  background: #f8f9fa;
  border-radius: 8px;
  padding: 20px;
  display: flex;
  justify-content: center;
}

.form-group {
  margin-bottom: 15px;
}

.form-group label {
  display: block;
  font-weight: 500;
  margin-bottom: 6px;
  color: #2c3e50;
}

.form-control {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
}

.form-control:focus {
  outline: none;
  border-color: #42b983;
  box-shadow: 0 0 0 2px rgba(66, 185, 131, 0.2);
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

.btn-secondary {
  background: #6c757d;
  color: white;
}

.btn-secondary:hover {
  background: #5a6268;
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

.btn-success {
  background: #28a745;
  color: white;
}

.btn-success:hover {
  background: #218838;
}

.btn-danger {
  background: #dc3545;
  color: white;
}

.btn-danger:hover {
  background: #c82333;
}

.btn-info {
  background: #17a2b8;
  color: white;
}

.btn-info:hover {
  background: #138496;
}

.muted {
  color: #6c757d;
}

.analyzing-progress {
  margin-top: 16px;
  padding: 20px;
  background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
  border-radius: 8px;
  border: 1px solid #dee2e6;
}

.progress-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  font-size: 14px;
  color: #495057;
  font-weight: 500;
}

.progress-bar {
  width: 100%;
  height: 20px;
  background: #e9ecef;
  border-radius: 10px;
  overflow: hidden;
  margin-bottom: 20px;
  box-shadow: inset 0 1px 2px rgba(0,0,0,0.1);
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #007bff 0%, #0056b3 100%);
  transition: width 0.3s ease;
  border-radius: 10px;
  position: relative;
  overflow: hidden;
}

.progress-fill::after {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  bottom: 0;
  right: 0;
  background: linear-gradient(
    90deg,
    rgba(255,255,255,0) 0%,
    rgba(255,255,255,0.3) 50%,
    rgba(255,255,255,0) 100%
  );
  animation: shimmer 1.5s infinite;
}

@keyframes shimmer {
  0% { transform: translateX(-100%); }
  100% { transform: translateX(100%); }
}

.progress-steps {
  display: flex;
  justify-content: space-between;
  gap: 10px;
}

.progress-steps .step {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 12px 8px;
  background: #fff;
  border-radius: 8px;
  border: 2px solid #dee2e6;
  transition: all 0.3s ease;
  opacity: 0.6;
}

.progress-steps .step.active {
  border-color: #007bff;
  background: #e7f3ff;
  opacity: 1;
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(0,123,255,0.2);
}

.step-icon {
  font-size: 24px;
  margin-bottom: 6px;
}

.step-label {
  font-size: 12px;
  color: #6c757d;
  font-weight: 500;
}

.step.active .step-label {
  color: #007bff;
  font-weight: 600;
}

@media (max-width: 900px) {
  .tp-toolbar__right {
    width: 100%;
    margin-left: 0;
    justify-content: flex-start;
  }

  .tp-stash-row {
    flex-direction: column;
    align-items: stretch;
  }

  .tp-stash-row .btn {
    width: 100%;
  }
}

@media (max-width: 640px) {
  .tp-hero {
    flex-direction: column;
    align-items: stretch;
  }

  .tp-hero-actions {
    width: 100%;
    justify-content: flex-end;
  }

  .tp-grid {
    grid-template-columns: 1fr;
  }

  .tp-card-actions .btn {
    flex: 1 1 calc(50% - 6px);
    min-width: 0;
  }
}

@media (min-width: 1400px) {
  .tp-grid {
    grid-template-columns: repeat(auto-fit, minmax(min(100%, 340px), 1fr));
  }
}
</style>
