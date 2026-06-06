<template>
  <div class="traditional-mode page-view active" id="view-traditional-mode">
    <div class="address-bar">
      <span class="address-icon">📁</span>
      <div class="breadcrumb">
        <span class="breadcrumb-segment" @click="navigateToSegment(-1)">{{ ROOT_NAME }}</span>
        <template v-for="(seg, idx) in pathSegments" :key="idx">
          <span class="separator" aria-hidden="true">›</span>
          <span class="breadcrumb-segment" @click="navigateToSegment(idx)">{{ seg }}</span>
        </template>
      </div>
      <input
        v-model="pathInput"
        type="text"
        class="path-input"
        :placeholder="displayPath"
        @keydown.enter="goToPath"
      >
      <button class="btn-go" @click="goToPath">Go</button>
    </div>

    <div class="toolbar explorer-toolbar">
      <div class="toolbar-group">
        <button type="button" class="toolbar-btn iconish" :disabled="historyIndex <= 0" @click="goBack" title="后退 (Alt+←)">◀</button>
        <button type="button" class="toolbar-btn iconish" :disabled="historyIndex >= history.length - 1" @click="goForward" title="前进 (Alt+→)">▶</button>
        <button type="button" class="toolbar-btn iconish" :disabled="!currentPath" @click="goUp" title="上级文件夹">↑</button>
        <button type="button" class="toolbar-btn iconish" @click="refresh" :disabled="loading" title="刷新">↻</button>
      </div>
      <div class="toolbar-divider tall"></div>
      <div class="toolbar-group">
        <button type="button" class="toolbar-btn" @click="showMkdirDialog = true" title="新建文件夹">新建文件夹</button>
        <label class="toolbar-btn" title="上传文件">
          上传
          <input ref="fileInputRef" type="file" style="display:none" multiple @change="handleUpload">
        </label>
      </div>
      <div class="toolbar-divider tall"></div>
      <div class="toolbar-group view-mode-group" role="group" aria-label="视图布局">
        <button
          type="button"
          class="toolbar-btn view-mode-btn"
          :class="{ 'is-active': viewMode === 'details' }"
          title="详细信息列表"
          @click="setViewMode('details')"
        >
          详细信息
        </button>
        <button
          type="button"
          class="toolbar-btn view-mode-btn"
          :class="{ 'is-active': viewMode === 'icons' }"
          title="中等图标（与资源管理器类似）"
          @click="setViewMode('icons')"
        >
          中等图标
        </button>
        <button
          type="button"
          class="toolbar-btn view-mode-btn"
          :class="{ 'is-active': viewMode === 'large' }"
          title="大图标"
          @click="setViewMode('large')"
        >
          大图标
        </button>
      </div>
    </div>

    <div class="file-list-container explorer-list-host">
      <table v-show="viewMode === 'details'" class="file-table explorer-detail-table">
        <thead>
          <tr>
            <th class="col-name sortable" scope="col" @click="toggleSort('name')">
              名称<span class="sort-glyph" v-if="sortKey === 'name'">{{ sortAsc ? ' ▲' : ' ▼' }}</span>
            </th>
            <th class="col-size sortable" scope="col" @click="toggleSort('size')">
              大小<span class="sort-glyph" v-if="sortKey === 'size'">{{ sortAsc ? ' ▲' : ' ▼' }}</span>
            </th>
            <th class="col-time sortable" scope="col" @click="toggleSort('modified')">
              修改日期<span class="sort-glyph" v-if="sortKey === 'modified'">{{ sortAsc ? ' ▲' : ' ▼' }}</span>
            </th>
            <th class="col-type sortable" scope="col" @click="toggleSort('type')">
              类型<span class="sort-glyph" v-if="sortKey === 'type'">{{ sortAsc ? ' ▲' : ' ▼' }}</span>
            </th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="loading && files.length === 0">
            <td colspan="4" class="text-center">加载中...</td>
          </tr>
          <tr v-else-if="files.length === 0">
            <td colspan="4" class="text-center empty-hint">此文件夹为空</td>
          </tr>
          <template v-for="file in sortedFiles" :key="file.name">
            <tr
              :class="['file-row', { selected: selectedFile?.name === file.name, 'is-dir': file.is_dir }]"
              @click="selectFile(file)"
              @dblclick="onFileDoubleClick(file)"
              @contextmenu.prevent="showContextMenu($event, file)"
            >
              <td class="name-cell">
                <span v-if="changedFiles.has(file.name)" class="changed-badge">⚠️</span>
                <template v-if="file.is_dir">
                  <span class="icon">📁</span>
                  <span>{{ file.name }}</span>
                </template>
                <template v-else-if="isImageFile(file)">
                  <img
                    :data-src="getImageUrl(file)"
                    :alt="file.name"
                    class="thumbnail lazy-thumb"
                    @click.stop="openImagePreview(file)"
                  >
                </template>
                <template v-else>
                  <span
                    class="icon icon-read-open"
                    title="单击：读取文件（Excel 在网页中打开，其它文件下载）"
                    role="button"
                    tabindex="0"
                    @click.stop="openFileByRead(file)"
                    @keydown.enter.prevent="openFileByRead(file)"
                    @keydown.space.prevent="openFileByRead(file)"
                  >{{ getFileIcon(file) }}</span>
                  <span>{{ file.name }}</span>
                </template>
              </td>
              <td>{{ formatSize(file.size) }}</td>
              <td>{{ formatTime(file.modified_time) }}</td>
              <td><span class="type-tag">{{ file.is_dir ? '文件夹' : (file.type || '文件') }}</span></td>
            </tr>
          </template>
        </tbody>
      </table>

      <div
        v-show="viewMode !== 'details'"
        class="explorer-icon-view"
        :class="{ 'mode-icons': viewMode === 'icons', 'mode-large': viewMode === 'large' }"
      >
        <div v-if="loading && files.length === 0" class="icon-view-state">加载中...</div>
        <div v-else-if="files.length === 0" class="icon-view-state empty-hint">此文件夹为空</div>
        <div v-else class="icon-grid" role="list">
          <div
            v-for="file in sortedFiles"
            :key="file.name"
            class="icon-tile"
            role="listitem"
            :class="{ selected: selectedFile?.name === file.name, 'is-dir': file.is_dir }"
            @click="selectFile(file)"
            @dblclick="onFileDoubleClick(file)"
            @contextmenu.prevent="showContextMenu($event, file)"
          >
            <span v-if="changedFiles.has(file.name)" class="tile-changed" title="有变更">⚠</span>
            <div class="tile-visual">
              <template v-if="file.is_dir">
                <span class="tile-folder-glyph" aria-hidden="true">📁</span>
              </template>
              <template v-else-if="isImageFile(file)">
                <img
                  :data-src="getImageUrl(file)"
                  :alt="file.name"
                  class="tile-thumb lazy-thumb"
                  @click.stop="openImagePreview(file)"
                >
              </template>
              <template v-else>
                <div
                  class="tile-visual-file-hit"
                  title="单击：读取文件（Excel 用 /read 在网页中编辑，其它文件下载）"
                  role="button"
                  tabindex="0"
                  @click.stop="openFileByRead(file)"
                  @keydown.enter.prevent="openFileByRead(file)"
                  @keydown.space.prevent="openFileByRead(file)"
                >
                  <span class="tile-file-glyph" aria-hidden="true">{{ getFileIcon(file) }}</span>
                </div>
              </template>
            </div>
            <div
              class="tile-name"
              :title="file.is_dir ? file.name : (file.name + '（单击图标/双击：读取打开；Excel 网页编辑）')"
            >{{ file.name }}</div>
          </div>
        </div>
      </div>
    </div>

    <div
      v-if="contextMenu.visible && contextMenu.file"
      class="context-menu"
      :style="{ left: contextMenu.x + 'px', top: contextMenu.y + 'px' }"
      @click.stop
    >
      <div class="context-menu-item" @click="openFile(contextMenu.file!)">打开（读取）</div>
      <div class="context-menu-item" @click="startRename(contextMenu.file!)">重命名</div>
      <div class="context-menu-item context-menu-danger" @click="confirmDelete(contextMenu.file!)">删除</div>
    </div>

    <div v-if="showMkdirDialog" class="modal-overlay" @click.self="showMkdirDialog = false">
      <div class="modal-box">
        <div class="modal-header">新建文件夹</div>
        <div class="modal-body">
          <input v-model="newFolderName" type="text" placeholder="请输入文件夹名称" @keydown.enter="createFolder" ref="mkdirInputRef">
        </div>
        <div class="modal-footer">
          <button class="btn btn-secondary" @click="showMkdirDialog = false">取消</button>
          <button class="btn btn-primary" @click="createFolder" :disabled="!newFolderName.trim()">创建</button>
        </div>
      </div>
    </div>

    <div v-if="renameDialog.show" class="modal-overlay" @click.self="renameDialog.show = false">
      <div class="modal-box">
        <div class="modal-header">重命名</div>
        <div class="modal-body">
          <input v-model="renameDialog.newName" type="text" @keydown.enter="doRename" ref="renameInputRef">
        </div>
        <div class="modal-footer">
          <button class="btn btn-secondary" @click="renameDialog.show = false">取消</button>
          <button class="btn btn-primary" @click="doRename" :disabled="!renameDialog.newName.trim()">确定</button>
        </div>
      </div>
    </div>

    <div v-if="previewImage.visible" class="modal-overlay image-preview-overlay" @click="closeImagePreview">
      <img :src="previewImage.url" :alt="previewImage.name" class="preview-image">
      <button class="close-preview-btn" @click="closeImagePreview">&times;</button>
    </div>

    <div v-if="excelPanel.visible" class="excel-editor-panel traditional-excel-panel">
      <div class="excel-editor-header">
        <div class="excel-editor-title-wrap">
          <span class="excel-editor-title">{{ excelPanel.fileName }}</span>
          <div class="excel-main-tabs" role="tablist">
            <button
              type="button"
              role="tab"
              class="excel-tab"
              :class="{ 'is-active': excelPanel.mainTab === 'edit' }"
              :aria-selected="excelPanel.mainTab === 'edit'"
              @click="setExcelMainTab('edit')"
            >
              直接编辑
            </button>
            <button
              type="button"
              role="tab"
              class="excel-tab"
              :class="{ 'is-active': excelPanel.mainTab === 'induct' }"
              :aria-selected="excelPanel.mainTab === 'induct'"
              @click="setExcelMainTab('induct')"
            >
              手动归纳
            </button>
          </div>
          <span class="excel-editor-sub">
            {{
              excelPanel.mainTab === 'edit'
                ? '在下方表格中修改单元格，保存后写回服务器上的文件（多工作表会一并保存）。'
                : '选择客户与目标业务库，解析全表行后校验主数据；缺失时可勾选新增再入库。'
            }}
          </span>
        </div>
        <div class="excel-editor-actions">
          <button
            v-if="excelPanel.mainTab === 'edit'"
            type="button"
            class="btn btn-sm btn-success"
            :disabled="excelPanel.editSaving || !excelPanel.editContent || excelPanel.editLoading || excelPanel.editTruncated"
            @click="saveExcelEdit"
          >
            {{ excelPanel.editSaving ? '保存中…' : '保存' }}
          </button>
          <button type="button" class="btn btn-sm btn-secondary" @click="closeExcelPanel">关闭</button>
        </div>
      </div>

      <template v-if="excelPanel.mainTab === 'edit'">
        <div v-if="editSheetNames.length" class="traditional-sheet-bar">
          <label for="traditional-edit-sheet">工作表</label>
          <select
            id="traditional-edit-sheet"
            class="form-control traditional-sheet-select"
            v-model="excelPanel.editActiveSheet"
            :disabled="excelPanel.editLoading"
          >
            <option v-for="s in editSheetNames" :key="s" :value="s">{{ s }}</option>
          </select>
        </div>
        <div
          v-if="excelPanel.editTruncated && excelPanel.editTruncatedHint"
          class="excel-panel-state excel-panel-warn"
          role="status"
        >{{ excelPanel.editTruncatedHint }}</div>
        <div v-if="excelPanel.editLoading" class="excel-panel-state">正在加载工作簿…</div>
        <div v-else-if="excelPanel.editError" class="excel-panel-state excel-panel-error">{{ excelPanel.editError }}</div>
        <div v-else-if="excelPanel.editContent && editActiveRows.length" class="excel-editor-body traditional-edit-body">
          <table class="excel-table">
            <tbody>
              <tr v-for="(row, rIdx) in editActiveRows" :key="'er-' + excelPanel.editActiveSheet + '-' + rIdx">
                <td
                  v-for="(cell, cIdx) in row"
                  :key="'ec-' + rIdx + '-' + cIdx"
                  contenteditable="true"
                  spellcheck="false"
                  @blur="updateEditCell(rIdx, cIdx, $event)"
                >{{ formatEditCell(cell) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div v-else-if="excelPanel.editContent" class="excel-panel-state empty-excel">当前工作表无数据行</div>
      </template>

      <template v-else>
        <div v-if="excelPanel.sheetNames.length" class="traditional-sheet-bar">
          <label for="traditional-excel-sheet">工作表</label>
          <select
            id="traditional-excel-sheet"
            class="form-control traditional-sheet-select"
            v-model="excelPanel.selectedSheetName"
            :disabled="excelPanel.loading"
            @change="onTraditionalExtractSheetChange"
          >
            <option v-for="s in excelPanel.sheetNames" :key="s" :value="s">{{ s }}</option>
          </select>
        </div>

        <div class="induct-toolbar" v-if="!excelPanel.loading && !excelPanel.error && excelPanel.extractResult">
          <div class="induct-toolbar-row">
            <label class="induct-label">客户</label>
            <input
              v-model.trim="inductPurchaseUnit"
              class="form-control induct-select"
              list="traditional-induct-pu-datalist"
              placeholder="从列表选择或直接输入新单位"
              autocomplete="off"
            >
            <datalist id="traditional-induct-pu-datalist">
              <option v-for="u in inductPurchaseUnitOptions" :key="'pu-dl-' + u" :value="u" />
            </datalist>
          </div>
          <div class="induct-toolbar-row">
            <label class="induct-label">目标业务库</label>
            <select v-model="inductTargetScope" class="form-control induct-select">
              <option v-for="opt in inductScopeOptions" :key="opt.key" :value="opt.key">
                {{ opt.label }}
              </option>
            </select>
          </div>
          <div class="induct-toolbar-actions">
            <button
              type="button"
              class="btn btn-sm btn-secondary"
              :disabled="inductRowsLoading || excelPanel.loading"
              @click="reloadInductRows"
            >
              {{ inductRowsLoading ? '加载行数据…' : '重新加载行数据' }}
            </button>
            <button
              type="button"
              class="btn btn-sm btn-primary"
              :disabled="inductPreviewLoading || inductRowsLoading || !inductRows.length"
              @click="runInductPreview"
            >
              {{ inductPreviewLoading ? '校验中…' : '校验数据' }}
            </button>
            <button
              type="button"
              class="btn btn-sm btn-success"
              :disabled="inductCommitLoading || inductRowsLoading || !inductRows.length || !inductLastPreview"
              @click="onInductCommitClick"
            >
              {{ inductCommitLoading ? '入库中…' : '确认入库' }}
            </button>
          </div>
          <div class="induct-meta muted" v-if="inductRows.length">
            已加载 {{ inductRows.length }} 行（当前 Sheet：{{ traditionalExtractTitle }}）
          </div>
          <div v-if="inductRowsError" class="excel-panel-error induct-inline-error">{{ inductRowsError }}</div>
          <div v-if="inductPreviewMessage" class="induct-preview-msg" :class="{ warn: inductPreviewHasMissing }">
            {{ inductPreviewMessage }}
          </div>
        </div>

        <div v-if="excelPanel.loading" class="excel-panel-state">
          <div class="extract-progress-title">正在提取网格…</div>
          <div class="extract-progress-track" role="progressbar" :aria-valuenow="excelPanel.extractProgressPercent" aria-valuemin="0" aria-valuemax="100">
            <div class="extract-progress-fill" :style="{ width: Math.min(100, Math.max(0, excelPanel.extractProgressPercent)) + '%' }" />
          </div>
          <div v-if="excelPanel.extractProgressStep" class="extract-progress-step muted">{{ excelPanel.extractProgressStep }}</div>
          <div class="induct-loading-hint muted">
            若刚启动后端，首次请求可能需数十秒（服务初始化/模型加载）。请确认已运行 <code>python run.py</code>（5000）且 Vite 代理指向该端口。
          </div>
        </div>
        <div v-else-if="excelPanel.error" class="excel-panel-state excel-panel-error">{{ excelPanel.error }}</div>
        <div v-else-if="excelPanel.extractResult" class="excel-editor-body traditional-excel-body">
          <div v-if="(excelPanel.extractResult.fields || []).length" class="traditional-field-strip">
            <div class="traditional-field-title">识别字段（{{ excelPanel.extractResult.fields.length }}）</div>
            <ul class="traditional-field-list">
              <li v-for="(field, idx) in excelPanel.extractResult.fields" :key="(field.label || field.name || '') + '-' + idx">
                <span class="field-idx">{{ idx + 1 }}.</span>
                {{ field.label || field.name || '未命名' }}
              </li>
            </ul>
          </div>
          <ExcelPreview
            :fields="excelPanel.extractResult.fields || []"
            :sample-rows="excelPanel.extractResult?.preview_data?.sample_rows || []"
            :title="traditionalExtractTitle + ' 真实网格'"
            :grid-data="excelPanel.extractResult?.preview_data?.grid_preview || null"
            :rows="12"
            :columns="10"
          />
        </div>
      </template>
    </div>

    <div v-if="inductMissingModal" class="modal-overlay" @click.self="closeInductMissingModal">
      <div class="modal-box induct-missing-modal">
        <div class="modal-header">缺失主数据</div>
        <div class="modal-body">
          <p class="muted induct-missing-lead">以下数据在库中不存在。勾选「新增」后将在入库前创建；取消勾选将仍尝试入库（可能失败）。</p>
          <div v-if="inductModalMissingList.length === 0" class="muted">无待确认项</div>
          <div v-else class="induct-missing-groups">
            <div v-for="grp in inductModalMissingList" :key="grp.key" class="induct-missing-group">
              <div class="induct-missing-group-title">{{ grp.label }}</div>
              <label v-for="item in grp.items" :key="grp.key + ':' + item" class="induct-missing-item">
                <input type="checkbox" v-model="inductCreateSelected[inductSelKey(grp.key, item)]" />
                <span>{{ item }}</span>
              </label>
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button type="button" class="btn btn-secondary" @click="closeInductMissingModal">取消</button>
          <button type="button" class="btn btn-primary" :disabled="inductCommitLoading" @click="confirmInductCommitFromModal">
            {{ inductCommitLoading ? '处理中…' : '确认并入库' }}
          </button>
        </div>
      </div>
    </div>

    <div v-if="toastMessage" class="toast" :class="toastType">{{ toastMessage }}</div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, reactive, onMounted, onBeforeUnmount, nextTick } from 'vue'
import api, { buildFullApiUrl } from '@/api/core'
import manualInductApi from '@/api/manualInduct'
import templatePreviewApi from '@/api/templatePreview'
import { traditionalApi, FileInfo } from '@/api/traditional'
import ExcelPreview from '@/components/template/ExcelPreview.vue'
import { appConfirm } from '@/utils/appDialog'

const INDUCT_SCOPE_OPTIONS = [
  { key: 'products', label: '产品目录表' },
  { key: 'customers', label: '客户管理' },
  { key: 'materials', label: '原材料仓库' },
  { key: 'shipmentRecords', label: '出货记录' },
  { key: 'orders', label: '出货明细（发货单）' }
] as const

const ROOT_NAME = 'bang'

const VIEW_MODE_STORAGE_KEY = 'xcagi_traditional_view_mode'
type ExplorerViewMode = 'details' | 'icons' | 'large'

function readStoredViewMode(): ExplorerViewMode {
  if (typeof localStorage === 'undefined') return 'icons'
  try {
    const v = localStorage.getItem(VIEW_MODE_STORAGE_KEY)
    if (v === 'details' || v === 'icons' || v === 'large') return v
  } catch {
    /* ignore */
  }
  return 'icons'
}

const viewMode = ref<ExplorerViewMode>(readStoredViewMode())

function setViewMode(m: ExplorerViewMode) {
  viewMode.value = m
  try {
    localStorage.setItem(VIEW_MODE_STORAGE_KEY, m)
  } catch {
    /* ignore */
  }
  nextTick(() => initLazyObserver())
}

const currentPath = ref('')
const files = ref<FileInfo[]>([])
const loading = ref(false)
const pathInput = ref('')
const selectedFile = ref<FileInfo | null>(null)
const history = ref<string[]>([''])
const historyIndex = ref(0)
const showMkdirDialog = ref(false)
const newFolderName = ref('')
const mkdirInputRef = ref<HTMLInputElement | null>(null)
const fileInputRef = ref<HTMLInputElement | null>(null)
const renameInputRef = ref<HTMLInputElement | null>(null)
const previewImage = ref({ visible: false, url: '', name: '' })

/** 直接编辑：read/write；手动归纳：extract-grid + 全表行解析 + 主数据校验入库 */
const excelPanel = reactive({
  visible: false,
  fileName: '',
  filePath: '',
  mainTab: 'edit' as 'edit' | 'induct',
  loading: false,
  /** 异步 extract-grid 进度（0–100） */
  extractProgressPercent: 0,
  extractProgressStep: '',
  extractResult: null as Record<string, any> | null,
  sheetNames: [] as string[],
  selectedSheetName: '',
  error: '',
  /** 与当前 filePath 一致时表示提取结果仍有效；直接编辑保存后清空以强制刷新 */
  extractLoadedPath: '',
  editContent: null as Record<string, { rows: any[][] }> | null,
  editActiveSheet: '',
  editLoading: false,
  editSaving: false,
  editError: '',
  /** 后端因行/列上限截断预览：禁止保存，避免覆盖未加载区域 */
  editTruncated: false,
  editTruncatedHint: '',
  /** 与目录列表一致的 size|mtime，用于下载缓存与防 HTTP 缓存串文件 */
  sourceFingerprint: '',
})

let cachedTradExcel: { path: string; fingerprint: string; file: File } | null = null
let traditionalSheetChangeBusy = false
/** 防止快速切换文件时旧请求晚到覆盖新状态 */
let excelEditLoadGeneration = 0
/** 防止多次并发 extract-grid 结束时错误清除 loading */
let traditionalExtractGeneration = 0

const inductScopeOptions = INDUCT_SCOPE_OPTIONS
const inductPurchaseUnit = ref('')
const inductPurchaseUnitOptions = ref<string[]>([])
const inductTargetScope = ref('products')
const inductRows = ref<Record<string, any>[]>([])
const inductRowsLoading = ref(false)
const inductRowsError = ref('')
const inductRowsLoadedKey = ref('')
const inductPreviewLoading = ref(false)
const inductCommitLoading = ref(false)
const inductLastPreview = ref<Record<string, any> | null>(null)
const inductMissingModal = ref(false)
const inductCreateSelected = ref<Record<string, boolean>>({})

const MISSING_LABELS: Record<string, string> = {
  purchase_units: '客户',
  product_models: '产品型号（产品库）',
  customer_names: '客户名称',
  material_codes: '原材料编码'
}

function inductSelKey(cat: string, item: string) {
  return `${cat}::${item}`
}

const inductModalMissingList = computed(() => {
  const prev = inductLastPreview.value as { missing?: Record<string, string[]> } | null
  const m = prev?.missing
  if (!m) return []
  const out: { key: string; label: string; items: string[] }[] = []
  for (const key of Object.keys(m)) {
    const items = Array.isArray(m[key]) ? m[key].filter(Boolean) : []
    if (!items.length) continue
    out.push({ key, label: MISSING_LABELS[key] || key, items })
  }
  return out
})

const inductPreviewHasMissing = computed(() => inductModalMissingList.value.length > 0)

const inductPreviewMessage = computed(() => {
  const p = inductLastPreview.value
  if (!p) return ''
  if (!p.success) return String(p.message || '校验失败')
  if (!inductPreviewHasMissing.value) return '校验通过：未发现缺失主数据，可直接确认入库。'
  const parts = inductModalMissingList.value.map((g) => `${g.label} ${g.items.length} 项`)
  return `校验完成：待确认 ${parts.join('；')}`
})

function resetInductState() {
  inductPurchaseUnit.value = ''
  inductTargetScope.value = 'products'
  inductRows.value = []
  inductRowsLoading.value = false
  inductRowsError.value = ''
  inductRowsLoadedKey.value = ''
  inductPreviewLoading.value = false
  inductCommitLoading.value = false
  inductLastPreview.value = null
  inductMissingModal.value = false
  inductCreateSelected.value = {}
}

async function loadInductPurchaseUnits() {
  try {
    const res = (await api.get('/api/orders/purchase-units')) as { success?: boolean; data?: unknown }
    const raw = res?.data
    const list = Array.isArray(raw) ? raw : []
    const names: string[] = []
    for (const x of list) {
      if (typeof x === 'string' && x.trim()) names.push(x.trim())
      else if (x && typeof x === 'object' && (x as { unit_name?: string }).unit_name) {
        const n = String((x as { unit_name?: string }).unit_name || '').trim()
        if (n) names.push(n)
      }
    }
    inductPurchaseUnitOptions.value = [...new Set(names)].sort((a, b) => a.localeCompare(b, 'zh-CN'))
  } catch {
    inductPurchaseUnitOptions.value = []
  }
}

function inductRowsCacheKey() {
  return `${excelPanel.filePath}|${excelPanel.selectedSheetName || ''}|${excelPanel.sourceFingerprint || ''}`
}

async function ensureInductRowsLoaded() {
  if (!excelPanel.visible || !excelPanel.filePath) return
  const key = inductRowsCacheKey()
  if (inductRowsLoadedKey.value === key && inductRows.value.length) return
  inductRowsLoading.value = true
  inductRowsError.value = ''
  try {
    const f = await getTraditionalExcelFile(
      excelPanel.filePath,
      excelPanel.fileName,
      excelPanel.sourceFingerprint || buildFileFingerprint({
        name: excelPanel.fileName,
        is_dir: false,
        size: 0,
        modified_time: '',
        type: ''
      })
    )
    const sheet = excelPanel.selectedSheetName || ''
    const res = (await manualInductApi.extractUpload(f, sheet)) as {
      success?: boolean
      rows?: unknown
      message?: string
    }
    if (res && res.success === false) {
      throw new Error(res.message || '解析 Excel 行失败')
    }
    const rows = Array.isArray(res.rows) ? res.rows : []
    inductRows.value = rows
    inductRowsLoadedKey.value = key
  } catch (e: any) {
    inductRows.value = []
    inductRowsLoadedKey.value = ''
    inductRowsError.value = e?.message || String(e)
    showToast(inductRowsError.value, 'error')
  } finally {
    inductRowsLoading.value = false
  }
}

async function reloadInductRows() {
  inductRowsLoadedKey.value = ''
  await ensureInductRowsLoaded()
}

function initInductCreateSelections() {
  const next: Record<string, boolean> = {}
  for (const grp of inductModalMissingList.value) {
    for (const item of grp.items) {
      next[inductSelKey(grp.key, item)] = true
    }
  }
  inductCreateSelected.value = next
}

async function runInductPreview() {
  if (!inductRows.value.length) {
    showToast('请先等待行数据加载完成', 'error')
    return
  }
  if (
    (inductTargetScope.value === 'shipmentRecords' || inductTargetScope.value === 'orders') &&
    !String(inductPurchaseUnit.value || '').trim()
  ) {
    showToast('当前目标库需要选择客户', 'error')
    return
  }
  inductPreviewLoading.value = true
  inductLastPreview.value = null
  try {
    const res = await manualInductApi.preview({
      target_scope: inductTargetScope.value,
      purchase_unit: inductPurchaseUnit.value.trim() || undefined,
      rows: inductRows.value
    })
    inductLastPreview.value = res as Record<string, any>
    if (!res?.success) {
      showToast(res?.message || '校验失败', 'error')
      return
    }
    if (inductPreviewHasMissing.value) {
      showToast('校验完成：存在缺失主数据，点击「确认入库」可勾选是否新增', 'error')
    } else {
      showToast('校验通过', 'success')
    }
  } catch (e: any) {
    showToast(e?.message || '校验失败', 'error')
  } finally {
    inductPreviewLoading.value = false
  }
}

function buildCreateMissingPayload(): Record<string, string[]> {
  const out: Record<string, string[]> = {
    purchase_units: [],
    product_models: [],
    customer_names: [],
    material_codes: []
  }
  for (const grp of inductModalMissingList.value) {
    const key = grp.key
    if (!(key in out)) continue
    const acc: string[] = []
    for (const item of grp.items) {
      const sel = inductCreateSelected.value[inductSelKey(key, item)]
      if (sel !== false) acc.push(item)
    }
    out[key] = acc
  }
  return out
}

async function submitInductCommit(createMissing: Record<string, string[]>) {
  inductCommitLoading.value = true
  try {
    const res = await manualInductApi.commit({
      target_scope: inductTargetScope.value,
      purchase_unit: inductPurchaseUnit.value.trim() || undefined,
      rows: inductRows.value,
      create_missing: createMissing
    })
    if (!res?.success) {
      showToast(res?.message || '入库失败', 'error')
      return
    }
    showToast(res?.message || '入库成功', 'success')
    inductMissingModal.value = false
    inductLastPreview.value = null
    await loadInductPurchaseUnits()
  } catch (e: any) {
    showToast(e?.message || '入库失败', 'error')
  } finally {
    inductCommitLoading.value = false
  }
}

function closeInductMissingModal() {
  if (inductCommitLoading.value) return
  inductMissingModal.value = false
}

async function confirmInductCommitFromModal() {
  const cm = buildCreateMissingPayload()
  await submitInductCommit(cm)
}

async function onInductCommitClick() {
  if (!inductLastPreview.value?.success) {
    showToast('请先完成校验', 'error')
    return
  }
  if (
    (inductTargetScope.value === 'shipmentRecords' || inductTargetScope.value === 'orders') &&
    !String(inductPurchaseUnit.value || '').trim()
  ) {
    showToast('请选择客户', 'error')
    return
  }
  if (inductPreviewHasMissing.value) {
    initInductCreateSelections()
    inductMissingModal.value = true
    return
  }
  await submitInductCommit({
    purchase_units: [],
    product_models: [],
    customer_names: [],
    material_codes: []
  })
}

function cloneSheetRowsForEdit(rows: any[][]): any[][] {
  if (typeof structuredClone === 'function') {
    try {
      return structuredClone(rows) as any[][]
    } catch {
      /* 含不可克隆类型时回退 */
    }
  }
  return JSON.parse(JSON.stringify(rows)) as any[][]
}

const traditionalExtractTitle = computed(() => {
  return (
    excelPanel.selectedSheetName ||
    excelPanel.extractResult?.preview_data?.sheet_name ||
    excelPanel.extractResult?.preview_data?.selected_sheet_name ||
    'Sheet'
  )
})

const editSheetNames = computed(() => {
  if (!excelPanel.editContent) return []
  return Object.keys(excelPanel.editContent)
})

const editActiveRows = computed(() => {
  const s = excelPanel.editActiveSheet
  if (!s || !excelPanel.editContent?.[s]) return []
  return excelPanel.editContent[s].rows
})

function formatEditCell(cell: unknown): string {
  if (cell === null || cell === undefined) return ''
  if (typeof cell === 'string') return cell
  if (typeof cell === 'number' || typeof cell === 'boolean') return String(cell)
  return String(cell)
}

function clearTraditionalExcelCache() {
  cachedTradExcel = null
}

function buildFileFingerprint(file: FileInfo): string {
  const sz = Number(file.size) || 0
  const mt = String(file.modified_time || '').trim()
  return `${sz}|${mt}`
}

async function getTraditionalExcelFile(
  filePath: string,
  displayName: string,
  fingerprint: string
): Promise<File> {
  if (
    cachedTradExcel &&
    cachedTradExcel.path === filePath &&
    cachedTradExcel.fingerprint === fingerprint
  ) {
    return cachedTradExcel.file
  }
  const ac = new AbortController()
  const tid = window.setTimeout(() => ac.abort(), 180_000)
  let res: Response
  try {
    res = await api.download(
      '/api/traditional-mode/download',
      { file: filePath, v: fingerprint },
      { signal: ac.signal }
    )
  } finally {
    window.clearTimeout(tid)
  }
  const blob = await res.blob()
  const lower = displayName.toLowerCase()
  const mime =
    blob.type ||
    (lower.endsWith('.xls') && !lower.endsWith('.xlsx')
      ? 'application/vnd.ms-excel'
      : 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
  const file = new File([blob], displayName, { type: mime })
  cachedTradExcel = { path: filePath, fingerprint, file }
  return file
}
const toastMessage = ref('')
const toastType = ref<'success' | 'error'>('success')
let toastTimer: number | null = null
const changedFiles = ref(new Set<string>())
const contextMenu = ref({ visible: false, x: 0, y: 0, file: null as FileInfo | null })
const renameDialog = ref({ show: false, file: null as FileInfo | null, newName: '' })
let watchTimer: number | null = null
let lastWatchData: Record<string, string> = {}
let eventSource: AbortController | null = null
let visibilityHandler: ((e: Event) => void) | null = null
let lazyObserver: IntersectionObserver | null = null
let sseRetryCount = 0
let sseStopped = false
const SSE_MAX_RETRIES = 10

const pathSegments = computed(() => {
  if (!currentPath.value) return []
  return currentPath.value.replace(/\\/g, '/').split('/').filter(Boolean)
})

const displayPath = computed(() => {
  if (!currentPath.value) return ROOT_NAME
  return `${ROOT_NAME}\\${currentPath.value.replace(/\//g, '\\')}`
})

/** 地址栏：根目录与多级路径均带逻辑根名，反斜杠风格同资源管理器 */
function formatPathInput(path: string): string {
  if (!path) return ROOT_NAME
  return `${ROOT_NAME}\\${path.replace(/\//g, '\\')}`
}

type SortKey = 'name' | 'size' | 'modified' | 'type'
const sortKey = ref<SortKey>('name')
const sortAsc = ref(true)

function toggleSort(key: SortKey) {
  if (sortKey.value === key) {
    sortAsc.value = !sortAsc.value
  } else {
    sortKey.value = key
    sortAsc.value = key !== 'size'
  }
}

const sortedFiles = computed(() => {
  const k = sortKey.value
  const asc = sortAsc.value ? 1 : -1
  const byName = (a: FileInfo, b: FileInfo) =>
    a.name.localeCompare(b.name, 'zh-CN', { numeric: true, sensitivity: 'base' })

  return [...files.value].sort((a, b) => {
    if (k === 'name') {
      if (a.is_dir !== b.is_dir) return a.is_dir ? -1 : 1
      return asc * byName(a, b)
    }
    if (k === 'type') {
      if (a.is_dir !== b.is_dir) return a.is_dir ? -1 : 1
      const ta = a.is_dir ? '\u0000' : (a.type || '')
      const tb = b.is_dir ? '\u0000' : (b.type || '')
      const c = ta.localeCompare(tb, 'zh-CN')
      if (c !== 0) return asc * c
      return asc * byName(a, b)
    }
    if (k === 'size') {
      if (a.is_dir !== b.is_dir) return a.is_dir ? -1 : 1
      const sa = a.is_dir ? 0 : (a.size || 0)
      const sb = b.is_dir ? 0 : (b.size || 0)
      if (sa !== sb) return asc * (sa < sb ? -1 : 1)
      return asc * byName(a, b)
    }
    const ta = new Date(a.modified_time || 0).getTime()
    const tb = new Date(b.modified_time || 0).getTime()
    if (ta !== tb) return asc * (ta < tb ? -1 : 1)
    return byName(a, b)
  })
})

function showToast(message: string, type: 'success' | 'error' = 'success') {
  toastMessage.value = message
  toastType.value = type
  if (toastTimer) clearTimeout(toastTimer)
  toastTimer = window.setTimeout(() => { toastMessage.value = '' }, 3000)
}

async function loadList(path?: string) {
  const target = path !== undefined ? path : currentPath.value
  loading.value = true
  try {
    const res = await traditionalApi.list(target)
    if (res.success && res.data) {
      files.value = res.data.files || []
      if (path === undefined || path === null) {
        currentPath.value = res.data.path || ''
      }
      syncExcelPanelFingerprintFromList()
      nextTick(() => initLazyObserver())
    } else {
      showToast(res.error || '加载目录失败', 'error')
    }
  } catch (e: any) {
    showToast('网络错误: ' + (e.message || ''), 'error')
  } finally {
    loading.value = false
  }
}

function navigate(path: string, pushHistory = true) {
  if (pushHistory) {
    const lastPath = history.value[history.value.length - 1]
    if (lastPath !== path) {
      history.value = history.value.slice(0, historyIndex.value + 1)
      history.value.push(path)
      historyIndex.value = history.value.length - 1
    }
  }
  currentPath.value = path
  pathInput.value = formatPathInput(path)
  selectedFile.value = null
  changedFiles.value.clear()
  lastWatchData = {}
  if (eventSource) {
    startSSE()
  }
  loadList(path)
}

function navigateToSegment(idx: number) {
  if (idx < 0) { navigate(''); return }
  const segs = pathSegments.value
  const newPath = segs.slice(0, idx + 1).join('/')
  navigate(newPath)
}

function goToPath() {
  let input = (pathInput.value || '').trim().replace(/\\/g, '/')
  if (input === '/' || input === '\\') input = ''
  const lower = input.toLowerCase()
  const rootPref = `${ROOT_NAME.toLowerCase()}/`
  if (lower.startsWith(rootPref)) {
    input = input.slice(rootPref.length).replace(/^\/+/, '')
  } else if (lower === ROOT_NAME.toLowerCase()) {
    input = ''
  }
  if (input.includes('..')) {
    showToast('路径不能包含 ..', 'error')
    return
  }
  navigate(input)
}

function goBack() {
  if (historyIndex.value > 0) {
    historyIndex.value--
    const path = history.value[historyIndex.value]
    currentPath.value = path
    pathInput.value = formatPathInput(path)
    selectedFile.value = null
    loadList(path)
  }
}

function goForward() {
  if (historyIndex.value < history.value.length - 1) {
    historyIndex.value++
    const path = history.value[historyIndex.value]
    currentPath.value = path
    pathInput.value = formatPathInput(path)
    selectedFile.value = null
    loadList(path)
  }
}

function goUp() {
  if (!currentPath.value) return
  const parts = currentPath.value.replace(/\\/g, '/').split('/').filter(Boolean)
  parts.pop()
  navigate(parts.join('/') || '', true)
}

function refresh() {
  changedFiles.value.clear()
  loadList()
}

/** 传统模式根下文件的逻辑相对路径（与 list/read/download 的 file 参数一致） */
function traditionalRelPathForFile(file: FileInfo): string {
  return currentPath.value ? `${currentPath.value}/${file.name}` : file.name
}

/** 列表刷新后：若当前打开的 Excel 在磁盘上已变，更新指纹并丢弃下载缓存，避免「提取预览」仍是旧文档 */
function syncExcelPanelFingerprintFromList() {
  if (!excelPanel.visible || !excelPanel.filePath || !excelPanel.fileName) return
  const target = excelPanel.filePath
  const row = files.value.find(
    (f) => !f.is_dir && f.name === excelPanel.fileName && traditionalRelPathForFile(f) === target
  )
  if (!row) return
  const next = buildFileFingerprint(row)
  if (next !== excelPanel.sourceFingerprint) {
    excelPanel.sourceFingerprint = next
    clearTraditionalExcelCache()
    excelPanel.extractLoadedPath = ''
  }
}

function selectFile(file: FileInfo) {
  selectedFile.value = file
  /**
   * 图标视图下单击整块 tile 只会选中，不会走「图标上的读取」；
   * 若侧栏 Excel 已打开，容易仍显示上一个文件，表现为「点的文件和网格/内容不对」。
   * 选中变化时与侧栏同步：Excel 切到当前文件，目录/非 Excel 则关闭侧栏。
   */
  if (!excelPanel.visible) return
  if (file.is_dir) {
    closeExcelPanel()
    return
  }
  if (isExcelFile(file)) {
    const p = traditionalRelPathForFile(file)
    if (p !== excelPanel.filePath) {
      void openTraditionalExcelPanel(file)
    }
    return
  }
  closeExcelPanel()
}

/**
 * 双击：文件夹进入；图片内置预览；其它文件走「读取」流程（Excel → GET /read 网页编辑，其它 → 下载）。
 */
async function onFileDoubleClick(file: FileInfo) {
  if (file.is_dir) {
    const nextPath = traditionalRelPathForFile(file)
    navigate(nextPath)
  } else if (isImageFile(file)) {
    openImagePreview(file)
  } else {
    await openFileByRead(file)
  }
}

/** 单击图标/双击非图片：Excel 用 traditionalApi.read 拉取并在侧栏编辑；其它类型走下载。 */
async function openFileByRead(file: FileInfo) {
  if (!file || file.is_dir) return
  if (isExcelFile(file)) {
    await openTraditionalExcelPanel(file)
    return
  }
  await openTraditionalFileLocally(file, { skipHideMenu: true })
}

function isImageFile(file: FileInfo): boolean {
  const ext = getExtension(file.name).toLowerCase()
  return ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp', 'svg'].includes(ext)
}

function isExcelFile(file: FileInfo): boolean {
  const ext = getExtension(file.name).toLowerCase()
  return ['xlsx', 'xls', 'xlsm'].includes(ext)
}

function getExtension(name: string): string {
  const dot = name.lastIndexOf('.')
  return dot > 0 ? name.substring(dot + 1) : ''
}

function getFileIcon(file: FileInfo): string {
  const ext = getExtension(file.name).toLowerCase()
  if (['xlsx', 'xls', 'xlsm'].includes(ext)) return '📄'
  if (['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp'].includes(ext)) return '🖼'
  if (['pdf'].includes(ext)) return '📕'
  if (['doc', 'docx'].includes(ext)) return '📝'
  if (['txt', 'csv', 'log'].includes(ext)) return '📃'
  return '📄'
}

function formatSize(size: number): string {
  if (!size || size <= 0) return '-'
  if (size < 1024) return size + ' B'
  if (size < 1024 * 1024) return (size / 1024).toFixed(1) + ' KB'
  return (size / (1024 * 1024)).toFixed(1) + ' MB'
}

function formatTime(time: string): string {
  if (!time) return '-'
  try {
    const d = new Date(time)
    return d.toLocaleString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
  } catch {
    return time
  }
}

function getImageUrl(file: FileInfo): string {
  const filePath = traditionalRelPathForFile(file)
  return buildFullApiUrl(`/api/traditional-mode/read?file=${encodeURIComponent(filePath)}`)
}

function openImagePreview(file: FileInfo) {
  previewImage.value = { visible: true, url: getImageUrl(file), name: file.name }
}

function closeImagePreview() {
  previewImage.value = { visible: false, url: '', name: '' }
}

/** 浏览器侧：下载后用户可用本机默认程序打开（Chrome 下载条也可点「打开」）。 */
async function openTraditionalFileLocally(
  file: FileInfo | null | undefined,
  opts?: { skipHideMenu?: boolean }
) {
  if (!opts?.skipHideMenu) {
    hideContextMenu()
  }
  if (!file || file.is_dir) return
  const filePath = traditionalRelPathForFile(file)
  try {
    const res = await api.download('/api/traditional-mode/download', { file: filePath })
    if (!res.ok) {
      let msg = `下载失败 (${res.status})`
      const ct = res.headers.get('content-type') || ''
      if (ct.includes('application/json')) {
        try {
          const j = await res.json()
          msg =
            (typeof j?.error === 'string' && j.error) ||
            (typeof j?.message === 'string' && j.message) ||
            msg
        } catch {
          /* ignore */
        }
      }
      throw new Error(msg)
    }
    const blob = await res.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = file.name
    document.body.appendChild(a)
    a.click()
    a.remove()
    URL.revokeObjectURL(url)
    showToast('已开始下载，完成后可在「下载」中点击「打开」或用资源管理器双击', 'success')
  } catch (e: any) {
    showToast(e?.message || '下载失败', 'error')
  }
}

async function openTraditionalExcelPanel(file: FileInfo) {
  const filePath = traditionalRelPathForFile(file)
  traditionalExtractGeneration += 1
  clearTraditionalExcelCache()
  resetInductState()
  excelPanel.visible = true
  excelPanel.fileName = file.name
  excelPanel.filePath = filePath
  excelPanel.mainTab = 'edit'
  excelPanel.loading = false
  excelPanel.extractResult = null
  excelPanel.sheetNames = []
  excelPanel.selectedSheetName = ''
  excelPanel.error = ''
  excelPanel.extractLoadedPath = ''
  excelPanel.editContent = null
  excelPanel.editActiveSheet = ''
  excelPanel.editError = ''
  excelPanel.editTruncated = false
  excelPanel.editTruncatedHint = ''
  excelPanel.sourceFingerprint = buildFileFingerprint(file)
  await loadExcelEditData()
}

async function loadExcelEditData() {
  if (!excelPanel.filePath) return
  const myGen = ++excelEditLoadGeneration
  excelPanel.editLoading = true
  excelPanel.editError = ''
  excelPanel.editContent = null
  excelPanel.editActiveSheet = ''
  excelPanel.editTruncated = false
  excelPanel.editTruncatedHint = ''
  const ac = new AbortController()
  const READ_TIMEOUT_MS = 90_000
  const tid = window.setTimeout(() => ac.abort(), READ_TIMEOUT_MS)
  try {
    const res = await traditionalApi.read(
      excelPanel.filePath,
      { signal: ac.signal },
      excelPanel.sourceFingerprint || undefined
    )
    if (myGen !== excelEditLoadGeneration) {
      return
    }
    if (!res.success || !res.data || res.data.type !== 'excel' || !res.data.content) {
      throw new Error((res as { error?: string }).error || '无法读取 Excel（仅支持 .xlsx / .xlsm 等，旧版 .xls 可能不支持）')
    }
    const content = res.data.content as Record<string, { rows?: any[][] }>
    const out: Record<string, { rows: any[][] }> = {}
    await nextTick()
    for (const [name, sheet] of Object.entries(content)) {
      const rows = Array.isArray(sheet?.rows) ? sheet.rows : []
      out[name] = { rows: cloneSheetRowsForEdit(rows) }
    }
    if (myGen !== excelEditLoadGeneration) {
      return
    }
    const names = Object.keys(out)
    if (!names.length) {
      throw new Error('工作簿中无工作表数据')
    }
    excelPanel.editContent = out
    excelPanel.editActiveSheet = names[0]
    const d = res.data as { edit_truncated?: boolean; edit_truncated_hint?: string }
    excelPanel.editTruncated = !!d.edit_truncated
    excelPanel.editTruncatedHint = String(d.edit_truncated_hint || '').trim()
  } catch (e: any) {
    if (myGen !== excelEditLoadGeneration) {
      return
    }
    const aborted =
      e?.name === 'AbortError' ||
      (typeof e?.message === 'string' && /aborted|AbortError|abort/i.test(e.message))
    const msg = aborted
      ? `读取 Excel 超时或已取消（${Math.round(READ_TIMEOUT_MS / 1000)}s 内无完整响应）。请确认本机已启动后端 run.py（5000）、文件不要过大，或改用「下载」后用 Excel 打开。`
      : (e?.message || String(e))
    excelPanel.editError = msg
    showToast(msg, 'error')
  } finally {
    if (myGen === excelEditLoadGeneration) {
      window.clearTimeout(tid)
      excelPanel.editLoading = false
    } else {
      window.clearTimeout(tid)
    }
  }
}

async function setExcelMainTab(tab: 'edit' | 'induct') {
  /** 离开「手动归纳」时作废进行中的 extract-grid，避免旧请求晚到或 loading 一直为 true */
  if (tab === 'edit' && excelPanel.mainTab === 'induct') {
    traditionalExtractGeneration += 1
    excelPanel.loading = false
  }
  excelPanel.mainTab = tab
  if (tab === 'induct') {
    void loadInductPurchaseUnits()
    if (excelPanel.extractLoadedPath !== excelPanel.filePath || !excelPanel.extractResult) {
      await runTraditionalGridExtract('')
    }
    await ensureInductRowsLoaded()
  }
}

function sleepMs(ms: number) {
  return new Promise<void>((resolve) => {
    window.setTimeout(resolve, ms)
  })
}

async function runTraditionalGridExtract(preferredSheet: string) {
  if (!excelPanel.visible || !excelPanel.filePath) return
  const myGen = ++traditionalExtractGeneration
  excelPanel.loading = true
  excelPanel.error = ''
  excelPanel.extractProgressPercent = 0
  excelPanel.extractProgressStep = '准备文件…'
  const ac = new AbortController()
  const EXTRACT_TIMEOUT_MS = 120_000
  const tid = window.setTimeout(() => ac.abort(), EXTRACT_TIMEOUT_MS)
  try {
    const f = await getTraditionalExcelFile(
      excelPanel.filePath,
      excelPanel.fileName,
      excelPanel.sourceFingerprint || buildFileFingerprint({
        name: excelPanel.fileName,
        is_dir: false,
        size: 0,
        modified_time: '',
        type: '',
      })
    )
    if (myGen !== traditionalExtractGeneration) {
      return
    }
    const formData = new FormData()
    formData.append('file', f)
    formData.append('analyze_all_sheets', 'false')
    if (preferredSheet) {
      formData.append('sheet_name', preferredSheet)
    }
    excelPanel.extractProgressStep = '提交任务…'
    excelPanel.extractProgressPercent = 2
    const start = (await templatePreviewApi.startExtractGridAsync(formData, {
      signal: ac.signal,
    })) as Record<string, any>
    if (myGen !== traditionalExtractGeneration) {
      return
    }
    if (!start?.success || !start?.task_id) {
      throw new Error(typeof start?.message === 'string' ? start.message : '无法启动提取任务')
    }
    const taskId = String(start.task_id)
    const pollMs = 280
    let res: Record<string, any> | null = null
    while (res === null) {
      if (myGen !== traditionalExtractGeneration) {
        return
      }
      const st = (await templatePreviewApi.getExtractGridStatus(taskId, {
        signal: ac.signal,
      })) as Record<string, any>
      if (myGen !== traditionalExtractGeneration) {
        return
      }
      if (typeof st.percent === 'number' && !Number.isNaN(st.percent)) {
        excelPanel.extractProgressPercent = st.percent
      }
      excelPanel.extractProgressStep = String(st.step || '')
      if (st.status === 'done' && st.result) {
        res = st.result as Record<string, any>
        break
      }
      if (st.status === 'error') {
        throw new Error(String(st.message || '提取失败'))
      }
      if (st.success === false && st.status !== 'running') {
        throw new Error(String(st.message || '提取失败'))
      }
      await sleepMs(pollMs)
    }
    if (myGen !== traditionalExtractGeneration) {
      return
    }
    if (!res?.success) {
      throw new Error(typeof res?.message === 'string' ? res.message : '提取失败')
    }
    excelPanel.extractResult = res
    const names = res?.preview_data?.sheet_names
    excelPanel.sheetNames = Array.isArray(names) ? [...names] : []
    excelPanel.selectedSheetName =
      preferredSheet ||
      res?.preview_data?.selected_sheet_name ||
      res?.preview_data?.sheet_name ||
      (excelPanel.sheetNames[0] || '')
    excelPanel.extractLoadedPath = excelPanel.filePath
  } catch (e: any) {
    if (myGen !== traditionalExtractGeneration) {
      return
    }
    const aborted =
      e?.name === 'AbortError' ||
      (typeof e?.message === 'string' && /aborted|AbortError|abort/i.test(e.message))
    const msg = aborted
      ? `提取网格超时（${Math.round(EXTRACT_TIMEOUT_MS / 1000)}s）。文件可能过大、工作表过多，或接口繁忙；可切换工作表重试或仅用「直接编辑」。`
      : (e?.message || String(e))
    excelPanel.error = msg
    showToast(msg, 'error')
  } finally {
    window.clearTimeout(tid)
    if (myGen === traditionalExtractGeneration) {
      excelPanel.loading = false
      excelPanel.extractProgressPercent = 0
      excelPanel.extractProgressStep = ''
    }
  }
}

async function onTraditionalExtractSheetChange() {
  if (traditionalSheetChangeBusy || !excelPanel.visible || !excelPanel.filePath) return
  const sheet = excelPanel.selectedSheetName
  if (!sheet) return
  traditionalSheetChangeBusy = true
  try {
    await runTraditionalGridExtract(sheet)
    inductRowsLoadedKey.value = ''
    inductLastPreview.value = null
    if (excelPanel.mainTab === 'induct') {
      await ensureInductRowsLoaded()
    }
  } finally {
    traditionalSheetChangeBusy = false
  }
}

function updateEditCell(rowIdx: number, colIdx: number, event: FocusEvent) {
  const sheet = excelPanel.editActiveSheet
  if (!sheet || !excelPanel.editContent?.[sheet]) return
  const rows = excelPanel.editContent[sheet].rows
  if (!rows[rowIdx]) {
    rows[rowIdx] = []
  }
  const el = event.target as HTMLElement | null
  rows[rowIdx][colIdx] = el?.textContent ?? ''
}

async function saveExcelEdit() {
  if (!excelPanel.filePath || !excelPanel.editContent) return
  if (excelPanel.editTruncated) {
    showToast('当前为截断预览，已禁止保存以免覆盖未加载的行列。请下载后用 Excel 编辑，或调大后端 TRADITIONAL_MODE_EXCEL_MAX_ROWS / MAX_COLS 后重新打开。', 'error')
    return
  }
  excelPanel.editSaving = true
  try {
    const content: Record<string, { rows: any[][] }> = {}
    for (const [k, v] of Object.entries(excelPanel.editContent)) {
      content[k] = { rows: v.rows }
    }
    const active = excelPanel.editActiveSheet || Object.keys(content)[0] || 'Sheet'
    const res = await traditionalApi.write({
      file: excelPanel.filePath,
      type: 'excel',
      data: {
        active_sheet: active,
        content,
      },
    })
    if (res.success) {
      showToast('已保存')
      excelPanel.extractLoadedPath = ''
      inductRowsLoadedKey.value = ''
      inductLastPreview.value = null
      clearTraditionalExcelCache()
      refresh()
    } else {
      showToast(res.error || '保存失败', 'error')
    }
  } catch (e: any) {
    showToast('保存错误: ' + (e.message || ''), 'error')
  } finally {
    excelPanel.editSaving = false
  }
}

function closeExcelPanel() {
  /** 作废进行中的 read/extract，避免关闭后仍被旧 Promise 把状态锁在「加载中」 */
  excelEditLoadGeneration += 1
  traditionalExtractGeneration += 1
  excelPanel.editLoading = false
  excelPanel.loading = false
  excelPanel.visible = false
  excelPanel.mainTab = 'edit'
  resetInductState()
  excelPanel.extractResult = null
  excelPanel.sheetNames = []
  excelPanel.selectedSheetName = ''
  excelPanel.error = ''
  excelPanel.extractLoadedPath = ''
  excelPanel.editContent = null
  excelPanel.editActiveSheet = ''
  excelPanel.editError = ''
  excelPanel.editTruncated = false
  excelPanel.editTruncatedHint = ''
  excelPanel.sourceFingerprint = ''
  clearTraditionalExcelCache()
}

function showContextMenu(event: MouseEvent, file: FileInfo) {
  contextMenu.value = { visible: true, x: event.clientX, y: event.clientY, file }
  window.addEventListener('click', hideContextMenu, { once: true })
}

function hideContextMenu() {
  contextMenu.value.visible = false
}

function openFile(file: FileInfo) {
  hideContextMenu()
  onFileDoubleClick(file)
}

function startRename(file: FileInfo) {
  hideContextMenu()
  renameDialog.value = { show: true, file, newName: file.name }
  nextTick(() => renameInputRef.value?.focus())
}

async function doRename() {
  if (!renameDialog.value.file || !renameDialog.value.newName.trim()) return
  try {
    const res = await traditionalApi.rename({
      path: currentPath.value,
      old_name: renameDialog.value.file.name,
      new_name: renameDialog.value.newName.trim()
    })
    if (res.success) {
      renameDialog.value.show = false
      showToast('重命名成功')
      refresh()
    } else {
      showToast(res.error || '重命名失败', 'error')
    }
  } catch (e: any) {
    showToast('操作失败: ' + (e.message || ''), 'error')
  }
}

async function confirmDelete(file: FileInfo) {
  hideContextMenu()
  if (!(await appConfirm(`确定要删除 "${file.name}" 吗？\n${file.is_dir ? '这将删除整个文件夹及其内容！' : ''}`, { danger: true }))) return
  deleteFile(file)
}

async function deleteFile(file: FileInfo) {
  const rel = traditionalRelPathForFile(file)
  if (excelPanel.visible && excelPanel.filePath === rel) {
    closeExcelPanel()
  }
  try {
    const res = await traditionalApi.delete({
      path: currentPath.value,
      name: file.name,
      rel_target: rel,
    })
    if (res.success) {
      showToast('删除成功')
      refresh()
    } else {
      showToast(res.error || '删除失败', 'error')
    }
  } catch (e: any) {
    showToast('删除失败: ' + (e.message || ''), 'error')
  }
}

async function createFolder() {
  const name = newFolderName.value.trim()
  if (!name) return
  if (/[/\\:*?"<>|]/.test(name)) {
    showToast('文件夹名称包含非法字符', 'error')
    return
  }
  try {
    const res = await traditionalApi.mkdir({ path: currentPath.value, name })
    if (res.success) {
      showMkdirDialog.value = false
      newFolderName.value = ''
      showToast('文件夹创建成功')
      refresh()
    } else {
      showToast(res.error || '创建失败', 'error')
    }
  } catch (e: any) {
    showToast('创建失败: ' + (e.message || ''), 'error')
  }
}

async function handleUpload(event: Event) {
  const input = event.target as HTMLInputElement
  const fileList = input.files
  if (!fileList || fileList.length === 0) return

  const uploadPath = currentPath.value
  let uploadedCount = 0
  let failedCount = 0

  for (let i = 0; i < fileList.length; i++) {
    const file = fileList[i]
    try {
      const res = await traditionalApi.upload(uploadPath, file)
      if (res.success) {
        uploadedCount++
      } else {
        failedCount++
        showToast(`${file.name} 上传失败: ${res.error || '未知错误'}`, 'error')
      }
    } catch (e: any) {
      failedCount++
      showToast(`${file.name} 上传失败: ${e.message || ''}`, 'error')
    }
  }

  input.value = ''

  if (uploadedCount > 0 && failedCount === 0) {
    showToast(`上传成功：${uploadedCount} 个文件已上传到 "${uploadPath || '根目录'}"`)
  } else if (uploadedCount > 0 && failedCount > 0) {
    showToast(`部分上传成功：${uploadedCount} 个成功，${failedCount} 个失败`, 'error')
  }

  loadList(currentPath.value)
}

function handleSSEMessage(data: any) {
  if (!data) return
  const changed = data.changed || []
  const snapshot = data.snapshot
  if (snapshot) {
    lastWatchData = snapshot
  }
  if (changed.length > 0) {
    const newChanged = new Set<string>()
    for (const fname of changed) {
      if (fname.startsWith('__deleted__:')) {
        newChanged.add(fname.replace('__deleted__:', ''))
      } else {
        newChanged.add(fname)
      }
    }
    changedFiles.value = newChanged
    loadList(currentPath.value)
  }
}

function startSSE() {
  stopSSE()
  sseRetryCount = 0
  sseStopped = false
  const url = buildFullApiUrl(`/api/traditional-mode/watch?path=${encodeURIComponent(currentPath.value)}`)
  eventSource = { _url: url } as any
  ;(async () => {
    try {
      const res = await fetch(url, { credentials: 'include' })
      if (!res.ok || !res.body || sseStopped) return
      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      while (!sseStopped) {
        const { done, value } = await reader.read()
        if (done || sseStopped) break
        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              sseRetryCount = 0
              handleSSEMessage(JSON.parse(line.slice(6)))
            } catch { /* ignore parse errors */ }
          }
        }
      }
      if (!sseStopped) reader.releaseLock()
    } catch (err: any) {
      if (sseStopped) return
    }
    if (!sseStopped && document.visibilityState === 'visible' && sseRetryCount < SSE_MAX_RETRIES) {
      sseRetryCount++
      const delay = Math.min(5000 * Math.pow(1.5, sseRetryCount - 1), 30000)
      setTimeout(() => { if (!sseStopped && document.visibilityState === 'visible' && !eventSource) startSSE() }, delay)
    }
  })()
}

function stopSSE() {
  sseStopped = true
  eventSource = null
}

function onVisibilityChange() {
  if (document.visibilityState === 'visible') {
    startSSE()
    initLazyObserver()
  } else {
    stopSSE()
    destroyLazyObserver()
  }
}

function initLazyObserver() {
  destroyLazyObserver()
  lazyObserver = new IntersectionObserver((entries) => {
    for (const entry of entries) {
      if (entry.isIntersecting) {
        const img = entry.target as HTMLImageElement
        const src = img.dataset.src
        if (src && !img.src) {
          img.src = src
          lazyObserver?.unobserve(img)
        }
      }
    }
  }, { rootMargin: '80px' })
  nextTick(() => {
    document.querySelectorAll('.lazy-thumb').forEach((el) => lazyObserver?.observe(el))
  })
}

function destroyLazyObserver() {
  if (lazyObserver) {
    lazyObserver.disconnect()
    lazyObserver = null
  }
}

onMounted(async () => {
  await loadList('')
  pathInput.value = displayPath.value
  visibilityHandler = onVisibilityChange
  document.addEventListener('visibilitychange', visibilityHandler)
  startSSE()
  initLazyObserver()
  document.addEventListener('click', hideContextMenu)
})

onBeforeUnmount(() => {
  stopSSE()
  destroyLazyObserver()
  if (visibilityHandler) {
    document.removeEventListener('visibilitychange', visibilityHandler)
    visibilityHandler = null
  }
  document.removeEventListener('click', hideContextMenu)
  if (toastTimer) clearTimeout(toastTimer)
})
</script>

<style scoped>
.traditional-mode {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #f0f0f0;
  gap: 0;
  padding: 0;
  box-sizing: border-box;
  overflow: hidden;
  font-family: 'Segoe UI', 'Segoe UI Variable Text', 'Microsoft YaHei', 'PingFang SC', system-ui, sans-serif;
  font-size: 13px;
  color: #1a1a1a;
}

.address-bar {
  display: flex;
  align-items: center;
  background: #ffffff;
  border: 1px solid #d9d9d9;
  border-radius: 2px;
  padding: 3px 8px 3px 6px;
  gap: 6px;
  box-shadow: none;
  margin: 8px 10px 0;
}

.address-icon {
  font-size: 16px;
  user-select: none;
}

.breadcrumb {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 2px;
  min-width: 0;
  flex: 1;
}

.breadcrumb-segment {
  cursor: pointer;
  color: #0067c0;
  font-size: 12px;
  white-space: nowrap;
  user-select: none;
}

.breadcrumb-segment:hover {
  text-decoration: underline;
  color: #005a9e;
}

.separator {
  color: #8a8a8a;
  margin: 0 4px;
  cursor: default;
  font-size: 12px;
  user-select: none;
}

.path-input {
  flex: 1;
  min-width: 120px;
  border: none;
  outline: none;
  font-size: 12px;
  color: #1a1a1a;
  background: transparent;
  font-family: inherit;
}

.btn-go {
  background: #e1e1e1;
  color: #1a1a1a;
  border: 1px solid #c8c8c8;
  border-radius: 2px;
  padding: 2px 12px;
  font-size: 12px;
  cursor: pointer;
  white-space: nowrap;
  transition: background 0.12s, border-color 0.12s;
}

.btn-go:hover {
  background: #d0d0d0;
  border-color: #b0b0b0;
}

.explorer-toolbar {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
  padding: 6px 10px 8px;
  background: #f0f0f0;
  border-bottom: 1px solid #d9d9d9;
}

.toolbar-group {
  display: inline-flex;
  align-items: center;
  gap: 2px;
}

.toolbar-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  border: 1px solid transparent;
  background: transparent;
  color: #1a1a1a;
  border-radius: 2px;
  padding: 4px 10px;
  font-size: 12px;
  cursor: pointer;
  white-space: nowrap;
  transition: background 0.1s, border-color 0.1s;
  user-select: none;
}

.toolbar-btn.iconish {
  min-width: 28px;
  padding: 4px 6px;
  font-size: 14px;
  line-height: 1;
}

.toolbar-btn:hover:not(:disabled) {
  background: #e5e5e5;
  border-color: #d0d0d0;
}

.toolbar-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.toolbar-divider {
  width: 1px;
  height: 20px;
  background: #d0d0d0;
  margin: 0 4px;
}

.toolbar-divider.tall {
  height: 22px;
}

.explorer-list-host {
  flex: 1;
  margin: 0 10px 10px;
  min-height: 0;
}

.file-list-container {
  flex: 1;
  overflow: auto;
  background: #ffffff;
  border: 1px solid #d9d9d9;
  border-radius: 0;
  box-shadow: none;
}

.file-table {
  width: 100%;
  border-collapse: collapse;
  table-layout: fixed;
}

.file-table thead th {
  position: sticky;
  top: 0;
  z-index: 10;
  background: #f9f9f9;
  color: #1a1a1a;
  font-weight: 600;
  font-size: 12px;
  text-align: left;
  padding: 4px 10px 5px;
  border-bottom: 1px solid #e5e5e5;
  border-right: 1px solid #efefef;
  user-select: none;
}

.file-table thead th:last-child {
  border-right: none;
}

.file-table thead th.sortable {
  cursor: pointer;
}

.file-table thead th.sortable:hover {
  background: #f0f0f0;
}

.sort-glyph {
  font-weight: 700;
  color: #0067c0;
  font-size: 10px;
}

.file-table thead th.col-name { width: 46%; }
.file-table thead th.col-size { width: 12%; }
.file-table thead th.col-time { width: 26%; }
.file-table thead th.col-type { width: 16%; }

.file-row {
  cursor: pointer;
  transition: background 0.08s;
  font-size: 12px;
}

.file-row td {
  padding: 2px 10px;
  border-bottom: 1px solid #f3f3f3;
  vertical-align: middle;
  line-height: 1.35;
}

.file-row:hover {
  background: #e5f3ff;
}

.file-row.selected {
  background: #cce8ff;
}

.file-row.selected td {
  border-bottom-color: #b3d7f5;
}

.view-mode-group {
  margin-left: auto;
}

.view-mode-btn.is-active {
  background: #d0e8ff;
  border-color: #7eb8e8;
  font-weight: 600;
}

.explorer-icon-view {
  flex: 1;
  min-height: 120px;
  padding: 10px 12px 12px;
  overflow: auto;
  box-sizing: border-box;
}

.icon-view-state {
  text-align: center;
  color: #6b6b6b;
  padding: 48px 12px;
  font-size: 13px;
}

.icon-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(92px, 1fr));
  gap: 4px 8px;
  align-content: start;
}

.explorer-icon-view.mode-large .icon-grid {
  grid-template-columns: repeat(auto-fill, minmax(118px, 1fr));
  gap: 10px 12px;
}

.icon-tile {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  padding: 8px 6px 6px;
  border: 1px solid transparent;
  border-radius: 4px;
  cursor: default;
  user-select: none;
  min-height: 0;
}

.icon-tile:hover {
  background: #e5f3ff;
  border-color: #c8e4fc;
}

.icon-tile.selected {
  background: #cce8ff;
  border-color: #7eb8e8;
}

.tile-changed {
  position: absolute;
  top: 2px;
  left: 4px;
  font-size: 11px;
  line-height: 1;
  z-index: 1;
}

.tile-visual {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  min-height: 56px;
  margin-bottom: 4px;
}

/* 非图片文件：子块在 flex 居中时只占 emoji 高度，点上下空白会冒泡到整格只「选中」。让可点区域铺满 tile-visual */
.tile-visual:has(.tile-visual-file-hit) {
  align-items: stretch;
  justify-content: stretch;
}

.explorer-icon-view.mode-large .tile-visual {
  min-height: 88px;
}

.tile-folder-glyph,
.tile-file-glyph {
  font-size: 44px;
  line-height: 1;
  filter: drop-shadow(0 1px 0 rgba(0, 0, 0, 0.06));
}

.tile-visual-file-hit {
  position: relative;
  z-index: 2;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  flex: 1 1 auto;
  min-height: 56px;
  cursor: pointer;
  border-radius: 6px;
  pointer-events: auto;
}

.explorer-icon-view.mode-large .tile-visual-file-hit {
  min-height: 88px;
}

.tile-visual-file-hit:focus-visible {
  outline: 2px solid #0067c0;
  outline-offset: 2px;
}

.tile-file-glyph {
  cursor: inherit;
  pointer-events: none;
}

.icon-read-open {
  cursor: pointer;
}

.icon-read-open:focus-visible {
  outline: 2px solid #0067c0;
  outline-offset: 1px;
  border-radius: 2px;
}

.explorer-icon-view.mode-large .tile-folder-glyph,
.explorer-icon-view.mode-large .tile-file-glyph {
  font-size: 64px;
}

.tile-thumb {
  width: 56px;
  height: 56px;
  object-fit: cover;
  border-radius: 4px;
  border: 1px solid #d0d0d0;
  background: #f3f3f3;
  cursor: pointer;
}

.tile-thumb:not([src]) {
  opacity: 0.35;
  min-height: 56px;
}

.explorer-icon-view.mode-large .tile-thumb {
  width: 88px;
  height: 88px;
}

.tile-name {
  font-size: 12px;
  line-height: 1.25;
  color: #1a1a1a;
  word-break: break-word;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  max-width: 100%;
}

.explorer-icon-view.mode-large .tile-name {
  font-size: 12px;
  -webkit-line-clamp: 3;
}

.name-cell {
  display: flex;
  align-items: center;
  gap: 6px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.icon {
  flex-shrink: 0;
  font-size: 16px;
}

.icon-open-local {
  cursor: pointer;
}

.icon-open-local:focus-visible {
  outline: 2px solid #0067c0;
  outline-offset: 1px;
  border-radius: 2px;
}

.thumbnail {
  width: 28px;
  height: 28px;
  object-fit: cover;
  border-radius: 4px;
  border: 1px solid #e5e7eb;
  cursor: pointer;
  flex-shrink: 0;
  transition: transform 0.15s;
  background: #f3f4f6;
}

.thumbnail:not([src]) {
  opacity: 0;
}

.thumbnail:hover {
  transform: scale(1.25);
  z-index: 5;
}

.changed-badge {
  flex-shrink: 0;
  font-size: 11px;
  animation: pulse-badge 1.5s ease-in-out infinite;
}

@keyframes pulse-badge {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.45; }
}

.type-tag {
  display: inline-block;
  font-size: 11px;
  padding: 1px 8px;
  border-radius: 999px;
  background: #f1f5f9;
  color: #64748b;
  white-space: nowrap;
}

.text-center {
  text-align: center;
  color: #9ca3af;
  padding: 40px 12px;
  font-size: 13px;
}

.empty-hint {
  color: #9ca3af;
}

.context-menu {
  position: fixed;
  z-index: 2000;
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
  padding: 4px 0;
  min-width: 140px;
}

.context-menu-item {
  padding: 7px 14px;
  font-size: 13px;
  color: #374151;
  cursor: pointer;
  transition: background 0.1s;
}

.context-menu-item:hover {
  background: #f3f4f6;
}

.context-menu-danger {
  color: #dc2626;
}

.context-menu-danger:hover {
  background: #fef2f2;
}

.modal-overlay {
  position: fixed;
  inset: 0;
  z-index: 3000;
  background: rgba(0, 0, 0, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
}

.modal-box {
  background: #fff;
  border-radius: 10px;
  width: 400px;
  max-width: 90vw;
  box-shadow: 0 20px 50px rgba(0, 0, 0, 0.18);
  overflow: hidden;
}

.modal-header {
  padding: 14px 18px;
  font-size: 15px;
  font-weight: 600;
  color: #111827;
  border-bottom: 1px solid #e5e7eb;
}

.modal-body {
  padding: 16px 18px;
}

.modal-body input {
  width: 100%;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  padding: 8px 10px;
  font-size: 13px;
  outline: none;
  box-sizing: border-box;
  transition: border-color 0.15s;
}

.modal-body input:focus {
  border-color: #3b82f6;
  box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.12);
}

.modal-footer {
  padding: 12px 18px;
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  border-top: 1px solid #e5e7eb;
}

.image-preview-overlay {
  align-items: center;
  justify-content: center;
}

.preview-image {
  max-width: 92vw;
  max-height: 92vh;
  object-fit: contain;
  border-radius: 6px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.35);
}

.close-preview-btn {
  position: absolute;
  top: 16px;
  right: 20px;
  background: rgba(255, 255, 255, 0.85);
  border: none;
  border-radius: 50%;
  width: 36px;
  height: 36px;
  font-size: 22px;
  line-height: 36px;
  text-align: center;
  cursor: pointer;
  color: #374151;
  transition: background 0.15s;
}

.close-preview-btn:hover {
  background: #fff;
}

.excel-editor-panel {
  position: fixed;
  right: 0;
  top: 0;
  bottom: 0;
  width: 60vw;
  max-width: 900px;
  background: #fff;
  box-shadow: -8px 0 30px rgba(0, 0, 0, 0.15);
  z-index: 2500;
  display: flex;
  flex-direction: column;
}

.excel-editor-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 18px;
  border-bottom: 1px solid #e5e7eb;
  background: #f8fafc;
  flex-shrink: 0;
}

.excel-editor-title {
  font-size: 14px;
  font-weight: 600;
  color: #111827;
}

.excel-editor-actions {
  display: flex;
  gap: 6px;
}

.excel-editor-title-wrap {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.excel-editor-sub {
  font-size: 11px;
  font-weight: 400;
  color: #64748b;
}

.excel-main-tabs {
  display: flex;
  gap: 4px;
  margin-top: 6px;
}

.excel-tab {
  border: 1px solid #d1d5db;
  background: #f9fafb;
  color: #374151;
  font-size: 12px;
  padding: 4px 12px;
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.12s, border-color 0.12s;
}

.excel-tab:hover {
  background: #f3f4f6;
}

.excel-tab.is-active {
  background: #eff6ff;
  border-color: #93c5fd;
  color: #1d4ed8;
  font-weight: 600;
}

.traditional-sheet-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 18px;
  border-bottom: 1px solid #e5e7eb;
  flex-shrink: 0;
}

.traditional-sheet-bar label {
  font-size: 12px;
  color: #374151;
  white-space: nowrap;
}

.traditional-sheet-select {
  max-width: 320px;
  flex: 1;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  padding: 4px 8px;
  font-size: 12px;
  background: #fff;
}

.excel-panel-state {
  padding: 24px 18px;
  text-align: center;
  color: #64748b;
  font-size: 13px;
}

.excel-panel-error {
  color: #b91c1c;
}

.excel-panel-warn {
  text-align: left;
  color: #92400e;
  background: #fffbeb;
  border: 1px solid #fcd34d;
  border-radius: 8px;
  margin: 0 18px 8px;
  padding: 12px 14px;
  line-height: 1.5;
}

.traditional-excel-body {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 12px 14px 16px;
}

.traditional-field-strip {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 8px 10px;
  background: #f8fafc;
  max-height: 120px;
  overflow: auto;
}

.traditional-field-title {
  font-size: 12px;
  font-weight: 600;
  color: #334155;
  margin-bottom: 6px;
}

.traditional-field-list {
  margin: 0;
  padding-left: 18px;
  font-size: 12px;
  color: #475569;
}

.traditional-field-list li {
  margin: 2px 0;
}

.traditional-field-list .field-idx {
  color: #94a3b8;
  margin-right: 4px;
}

.traditional-excel-panel {
  max-width: min(1100px, 96vw);
}

.traditional-edit-body {
  max-height: min(72vh, 820px);
  overflow: auto;
}

.excel-editor-body {
  flex: 1;
  overflow: auto;
  padding: 16px;
}

.excel-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.excel-table td {
  border: 1px solid #e2e8f0;
  padding: 6px 10px;
  min-width: 80px;
  outline: none;
  transition: background 0.1s;
}

.excel-table td:focus {
  background: #eff6ff;
  box-shadow: inset 0 0 0 1px #3b82f6;
}

.empty-excel {
  color: #9ca3af;
  text-align: center;
  padding: 40px 0;
  font-size: 14px;
}

.toast {
  position: fixed;
  top: 20px;
  right: 20px;
  z-index: 9999;
  padding: 10px 18px;
  border-radius: 8px;
  font-size: 13px;
  color: #fff;
  animation: toast-in 0.25s ease-out;
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.12);
}

.toast.success {
  background: linear-gradient(135deg, #059669, #10b981);
}

.toast.error {
  background: linear-gradient(135deg, #dc2626, #ef4444);
}

@keyframes toast-in {
  from {
    transform: translateX(40px);
    opacity: 0;
  }
  to {
    transform: translateX(0);
    opacity: 1;
  }
}

.btn {
  border: 1px solid transparent;
  border-radius: 5px;
  padding: 5px 14px;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.15s;
  white-space: nowrap;
}

.btn-primary {
  background: #3b82f6;
  color: #fff;
  border-color: #3b82f6;
}

.btn-primary:hover:not(:disabled) {
  background: #2563eb;
}

.btn-secondary {
  background: #fff;
  color: #374151;
  border-color: #d1d5db;
}

.btn-secondary:hover:not(:disabled) {
  background: #f3f4f6;
}

.btn-success {
  background: #10b981;
  color: #fff;
  border-color: #10b981;
}

.btn-success:hover:not(:disabled) {
  background: #059669;
}

.btn-sm {
  padding: 4px 10px;
  font-size: 12px;
}

.induct-toolbar {
  padding: 10px 18px 8px;
  border-bottom: 1px solid #e5e7eb;
  background: #f8fafc;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.induct-toolbar-row {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.induct-label {
  font-size: 12px;
  color: #374151;
  min-width: 72px;
}

.induct-select {
  flex: 1;
  min-width: 160px;
  max-width: 420px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  padding: 6px 10px;
  font-size: 12px;
}

.induct-toolbar-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}

.induct-meta {
  font-size: 12px;
}

.induct-inline-error {
  font-size: 12px;
  padding: 4px 0;
}

.induct-preview-msg {
  font-size: 12px;
  color: #166534;
  background: #ecfdf5;
  border: 1px solid #6ee7b7;
  border-radius: 8px;
  padding: 8px 10px;
  line-height: 1.45;
}

.induct-preview-msg.warn {
  color: #92400e;
  background: #fffbeb;
  border-color: #fcd34d;
}

.extract-progress-title {
  font-size: 13px;
  margin-bottom: 8px;
}

.extract-progress-track {
  height: 8px;
  border-radius: 999px;
  background: #e2e8f0;
  overflow: hidden;
  max-width: 420px;
}

.extract-progress-fill {
  height: 100%;
  border-radius: 999px;
  background: linear-gradient(90deg, #3b82f6, #60a5fa);
  transition: width 0.22s ease-out;
}

.extract-progress-step {
  margin-top: 6px;
  font-size: 12px;
  max-width: 52ch;
}

.induct-loading-hint {
  margin-top: 8px;
  font-size: 11px;
  line-height: 1.45;
  max-width: 52ch;
}

.induct-loading-hint code {
  font-size: 10px;
  padding: 1px 4px;
  background: #f1f5f9;
  border-radius: 4px;
}

.induct-missing-modal {
  width: 480px;
  max-width: 92vw;
}

.induct-missing-lead {
  margin: 0 0 10px;
  font-size: 12px;
  line-height: 1.5;
}

.induct-missing-groups {
  max-height: min(52vh, 420px);
  overflow: auto;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.induct-missing-group-title {
  font-size: 12px;
  font-weight: 600;
  color: #334155;
  margin-bottom: 6px;
}

.induct-missing-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: #475569;
  margin: 4px 0;
  cursor: pointer;
}

@media (max-width: 768px) {
  .excel-editor-panel {
    width: 95vw;
    max-width: none;
  }

  .file-list-container {
    overflow-x: auto;
  }

  .explorer-toolbar {
    gap: 2px;
  }

  .toolbar-btn {
    padding: 4px 7px;
    font-size: 11px;
  }
}
</style>
