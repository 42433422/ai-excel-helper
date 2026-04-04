<template>
  <div class="page-view" id="view-printer-list">
    <div class="page-content">
      <div class="page-header">
        <h2>打印机列表</h2>
        <div class="header-actions">
          <button class="btn btn-secondary" @click="loadPrinters" :disabled="loading">
            {{ loading ? '刷新中...' : '刷新' }}
          </button>
        </div>
      </div>

      <div class="card">
        <div class="card-header">打印机分类</div>
        <div style="display:flex; gap:12px; flex-wrap:wrap; padding: 15px 20px;">
          <div
            style="flex:1; min-width: 260px; background:#f8f9fa; border:1px solid #eee; border-radius:8px; padding:12px;"
          >
            <div style="font-weight:600; margin-bottom:6px;">发货单打印机</div>
            <select v-model="selectedDocumentPrinter" style="width:100%; max-width: 100%; margin-bottom:6px;">
              <option value="">未设置（自动识别）</option>
              <option v-for="p in printers" :key="`doc-${p.name}`" :value="p.name">
                {{ p.name }}
              </option>
            </select>
            <div style="margin-top:6px; font-size:12px; opacity:0.85;">
              状态：{{
                getPrinterStatus(selectedDocumentPrinter || classified?.document_printer?.name) ||
                classified?.document_printer?.status ||
                '-'
              }}
            </div>
          </div>

          <div
            style="flex:1; min-width: 260px; background:#f8f9fa; border:1px solid #eee; border-radius:8px; padding:12px;"
          >
            <div style="font-weight:600; margin-bottom:6px;">标签打印机</div>
            <select v-model="selectedLabelPrinter" style="width:100%; max-width: 100%; margin-bottom:6px;">
              <option value="">未设置（自动识别）</option>
              <option v-for="p in printers" :key="`label-${p.name}`" :value="p.name">
                {{ p.name }}
              </option>
            </select>
            <div style="margin-top:6px; font-size:12px; opacity:0.85;">
              状态：{{
                getPrinterStatus(selectedLabelPrinter || classified?.label_printer?.name) ||
                classified?.label_printer?.status ||
                '-'
              }}
            </div>
          </div>
        </div>
        <div style="padding: 0 20px 15px; display:flex; align-items:center; gap:10px; flex-wrap: wrap;">
          <button class="btn btn-primary" @click="saveSelection" :disabled="saving || loading || printers.length === 0">
            {{ saving ? '保存中...' : '保存自定义选择' }}
          </button>
          <button class="btn btn-secondary" @click="resetSelection" :disabled="saving">
            恢复自动识别
          </button>
          <span v-if="saveMessage" :style="{ color: saveMessageType === 'error' ? '#dc3545' : '#198754', fontSize: '13px' }">
            {{ saveMessage }}
          </span>
        </div>
      </div>

      <div class="card" style="margin-top: 15px;">
        <div class="card-header">全部打印机</div>
        <div v-if="selectedPrinterNames.length > 0" class="table-batch-bar">
          <div class="batch-info">已选择 {{ selectedPrinterNames.length }} 台打印机</div>
          <div class="batch-actions">
            <button class="btn btn-sm btn-secondary" @click="clearSelectedRows">清空选择</button>
            <button
              class="btn btn-sm btn-primary"
              @click="applySingleSelectionAs('document')"
              :disabled="selectedPrinterNames.length !== 1 || saving"
            >
              设为发货单打印机
            </button>
            <button
              class="btn btn-sm btn-info"
              @click="applySingleSelectionAs('label')"
              :disabled="selectedPrinterNames.length !== 1 || saving"
            >
              设为标签打印机
            </button>
          </div>
        </div>

        <div style="overflow:auto; border:1px solid #d5dce6; border-radius:8px; background:#f8fafc;">
          <table class="data-table" style="margin:0;">
            <thead>
              <tr>
                <th style="width:52px;">
                  <input
                    type="checkbox"
                    :checked="isAllRowsSelected"
                    @change="toggleSelectAllRows($event)"
                    title="全选/取消全选"
                  >
                </th>
                <th>打印机名称</th>
                <th>类型</th>
                <th>状态</th>
                <th>默认</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="loading">
                <td colspan="5" style="padding:14px 12px;" class="empty-state">加载中...</td>
              </tr>
              <tr v-else-if="printers.length === 0">
                <td colspan="5" style="padding:14px 12px;" class="empty-state">暂无打印机</td>
              </tr>
              <tr v-else v-for="p in printers" :key="p.name">
                <td>
                  <input
                    type="checkbox"
                    :checked="selectedRows.has(p.name)"
                    @change="toggleRowSelection(p.name, $event)"
                    :aria-label="`选择打印机 ${p.name}`"
                  >
                </td>
                <td>{{ p.name }}</td>
                <td>{{ getPrinterType(p.name) }}</td>
                <td>
                  <span :style="getStatusPillStyle(p.status)">
                    {{ p.status || '未知' }}
                  </span>
                </td>
                <td>{{ p.is_default ? '是' : '否' }}</td>
              </tr>
            </tbody>
          </table>
        </div>

        <div v-if="error" style="margin-top: 10px; color: #dc3545; font-size: 13px;">
          {{ error }}
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import printApi from '../api/print'

const loading = ref(false)
const error = ref('')
const printers = ref([])
const classified = ref(null)
const selectedDocumentPrinter = ref('')
const selectedLabelPrinter = ref('')
const saving = ref(false)
const saveMessage = ref('')
const saveMessageType = ref('success')
const selectedRows = ref(new Set())

function normalizePrinters(list) {
  if (!Array.isArray(list)) return []
  return list
    .map((p) => {
      if (!p) return null
      if (typeof p === 'string') {
        return { name: p, status: '未知', is_default: false }
      }
      return {
        name: p.name || p.printer || '',
        status: p.status || '未知',
        is_default: !!(p.is_default ?? p.isDefault ?? false)
      }
    })
    .filter(Boolean)
}

async function loadPrinters() {
  loading.value = true
  error.value = ''
  try {
    const data = await printApi.getPrinters()
    if (data?.success === false) throw new Error(data?.message || '加载打印机失败')

    printers.value = normalizePrinters(data?.printers)
    classified.value = data?.classified || null
    const selection = data?.selection || {}
    selectedDocumentPrinter.value =
      selection.document_printer || classified.value?.document_printer?.name || ''
    selectedLabelPrinter.value =
      selection.label_printer || classified.value?.label_printer?.name || ''
    selectedRows.value = new Set()
  } catch (e) {
    console.error('加载打印机失败:', e)
    error.value = `加载失败: ${e?.message || '未知错误'}`
    printers.value = []
    classified.value = null
  } finally {
    loading.value = false
  }
}

async function loadSelection() {
  try {
    const data = await printApi.getPrinterSelection()
    const selection = data?.selection || data || {}
    if (selection.document_printer !== undefined && selection.document_printer !== null) {
      selectedDocumentPrinter.value = selection.document_printer || selectedDocumentPrinter.value
    }
    if (selection.label_printer !== undefined && selection.label_printer !== null) {
      selectedLabelPrinter.value = selection.label_printer || selectedLabelPrinter.value
    }
  } catch (_e) {
    // 忽略独立 selection 接口加载失败，不影响列表展示
  }
}

async function saveSelection() {
  saving.value = true
  saveMessage.value = ''
  try {
    const payload = {
      document_printer: selectedDocumentPrinter.value || '',
      label_printer: selectedLabelPrinter.value || ''
    }
    const data = await printApi.savePrinterSelection(payload)
    if (!data?.success) throw new Error(data?.message || '保存失败')
    saveMessageType.value = 'success'
    saveMessage.value = data?.message || '打印机选择已保存'
    await loadPrinters()
  } catch (e) {
    saveMessageType.value = 'error'
    saveMessage.value = `保存失败: ${e?.message || '未知错误'}`
  } finally {
    saving.value = false
  }
}

async function resetSelection() {
  selectedDocumentPrinter.value = ''
  selectedLabelPrinter.value = ''
  await saveSelection()
}

const documentPrinterName = computed(
  () => classified.value?.document_printer?.name || classified.value?.document_printer || ''
)
const labelPrinterName = computed(
  () => classified.value?.label_printer?.name || classified.value?.label_printer || ''
)
const selectedPrinterNames = computed(() => Array.from(selectedRows.value))
const isAllRowsSelected = computed(
  () => printers.value.length > 0 && selectedRows.value.size === printers.value.length
)

function getPrinterType(name) {
  if (!name) return '-'
  if (documentPrinterName.value && name === documentPrinterName.value) return '发货单打印机'
  if (labelPrinterName.value && name === labelPrinterName.value) return '标签打印机'
  return '其他'
}

function getPrinterStatus(name) {
  if (!name) return ''
  const p = printers.value.find((x) => x.name === name)
  return p?.status || ''
}

function getStatusPillStyle(status) {
  const s = status || ''
  let bg = '#e9ecef'
  let color = '#495057'
  let border = 'transparent'

  if (s === '就绪') {
    bg = '#e7f5ea'
    color = '#198754'
    border = '#b7e4c0'
  } else if (s === '打印中') {
    bg = '#e3f2fd'
    color = '#0d6efd'
    border = '#b6d4fe'
  } else if (s === '错误' || s === '不可用') {
    bg = '#fdecea'
    color = '#dc3545'
    border = '#f5c6cb'
  } else if (s === '卡纸' || s === '缺纸') {
    bg = '#fff3cd'
    color = '#856404'
    border = '#ffeeba'
  } else if (s === '暂停') {
    bg = '#fff7ed'
    color = '#c2410c'
    border = '#fed7aa'
  }

  return {
    display: 'inline-block',
    padding: '3px 10px',
    borderRadius: '999px',
    fontSize: '12px',
    fontWeight: 600,
    background: bg,
    color,
    border: `1px solid ${border}`
  }
}

function toggleRowSelection(name, event) {
  const checked = !!event?.target?.checked
  const next = new Set(selectedRows.value)
  if (checked) next.add(name)
  else next.delete(name)
  selectedRows.value = next
}

function toggleSelectAllRows(event) {
  const checked = !!event?.target?.checked
  if (!checked) {
    selectedRows.value = new Set()
    return
  }
  selectedRows.value = new Set(printers.value.map((p) => p.name))
}

function clearSelectedRows() {
  selectedRows.value = new Set()
}

async function applySingleSelectionAs(type) {
  if (selectedPrinterNames.value.length !== 1) return
  const only = selectedPrinterNames.value[0]
  if (type === 'document') {
    selectedDocumentPrinter.value = only
  } else {
    selectedLabelPrinter.value = only
  }
  await saveSelection()
}

onMounted(() => {
  loadPrinters().then(() => loadSelection())
})
</script>

