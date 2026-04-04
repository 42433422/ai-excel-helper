<template>
  <div class="page-view" id="view-shipment-records">
    <div class="page-content">
      <div class="page-header">
        <h2>出货记录管理</h2>
        <div class="header-actions">
          <select v-model="selectedUnit" style="min-width: 200px; padding: 8px 12px; margin-right: 10px;">
            <option value="">请选择购买单位</option>
            <option v-for="unit in units" :key="unit" :value="unit">{{ unit }}</option>
          </select>
          <select v-model="selectedStatusFilter" style="min-width: 140px; padding: 8px 12px; margin-right: 10px;">
            <option value="all">全部状态</option>
            <option value="printed">已打印</option>
            <option value="pending">未打印</option>
          </select>
          <select v-model="selectedTemplateId" style="min-width: 320px; padding: 8px 12px; margin-right: 10px;">
            <option value="">请选择出货记录模板</option>
            <option v-for="tpl in templateOptions" :key="tpl.id" :value="tpl.id">
              {{ tpl.name }}{{ templateBadge(tpl) }}
            </option>
          </select>
          <button class="btn btn-primary" @click="loadRecords" :disabled="loading">查看记录</button>
          <button
            class="btn btn-success"
            :title="exportButtonTitle"
            @click="exportRecords"
            :disabled="!selectedUnit || !selectedTemplateId || !selectedTemplateHasFile || loading"
          >
            导出 Excel
          </button>
        </div>
      </div>
      <div class="card">
        <div class="card-header">
          {{ selectedUnit ? `${selectedUnit} - 共 ${filteredRecords.length} 条` : '选择购买单位后点击「查看记录」加载数据' }}
        </div>
        <div class="table-responsive table-responsive-shipment-records">
          <table class="data-table data-table-shipment-records">
            <thead>
              <tr>
                <th v-if="columns.length === 0">暂无数据</th>
                <th v-for="col in columns" :key="col">{{ colLabels[col] || col }}</th>
                <th v-if="columns.length > 0">操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="loading">
                <td :colspan="Math.max(columns.length + 1, 1)" class="empty-state">加载中...</td>
              </tr>
              <tr v-else-if="filteredRecords.length === 0">
                <td :colspan="Math.max(columns.length + 1, 1)" class="empty-state">请先选择购买单位并加载</td>
              </tr>
              <tr v-for="row in filteredRecords" :key="row.id || JSON.stringify(row)">
                <td v-for="col in columns" :key="col">
                  <span v-if="col === 'status'" :class="statusClass(row.status)">
                    {{ statusLabel(row.status) }}
                  </span>
                  <span v-else>{{ row[col] ?? '' }}</span>
                </td>
                <td>
                  <button class="btn btn-sm btn-secondary" @click="openEdit(row)" :disabled="!row.id">编辑</button>
                  <button class="btn btn-sm btn-danger" @click="deleteRow(row)" :disabled="!row.id">删除</button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div v-if="showEditModal" class="modal active">
        <div class="modal-content">
          <div class="modal-header">编辑出货记录</div>
          <div class="modal-body">
            <div class="form-group" v-for="col in editableColumns" :key="col">
              <label>{{ colLabels[col] || col }}</label>
              <input type="text" v-model="editForm[col]">
            </div>
          </div>
          <div class="modal-footer">
            <button class="btn btn-secondary" @click="closeEdit">取消</button>
            <button class="btn btn-primary" @click="saveEdit" :disabled="loading">保存</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import ordersApi from '../api/orders';
import templatePreviewApi from '../api/templatePreview';

const loading = ref(false);
const units = ref([]);
const selectedUnit = ref('');
const records = ref([]);
const columns = ref([]);
const templateOptions = ref([]);
const selectedTemplateId = ref('');
const selectedStatusFilter = ref('all');
const showEditModal = ref(false);
const editRowId = ref(null);
const editForm = ref({});

const editableColumns = computed(() => columns.value.filter((c) => c !== 'id'));
const filteredRecords = computed(() => {
  if (selectedStatusFilter.value === 'all') return records.value;
  if (selectedStatusFilter.value === 'printed') {
    return records.value.filter((r) => String(r?.status || '').trim().toLowerCase() === 'printed');
  }
  return records.value.filter((r) => {
    const status = String(r?.status || '').trim().toLowerCase();
    return status === 'pending' || status === '';
  });
});
const selectedTemplateOption = computed(() => {
  const targetId = String(selectedTemplateId.value || '').trim();
  return templateOptions.value.find((tpl) => String(tpl?.id || '').trim() === targetId) || null;
});
const selectedTemplateHasFile = computed(() => !!selectedTemplateOption.value?.hasFilePath);
const exportButtonTitle = computed(() => {
  if (!selectedTemplateId.value) return '请先选择出货记录模板';
  if (!selectedTemplateHasFile.value) return '所选模板未绑定 Excel 文件，请先在业务对接中上传并替换';
  return '按已选模板导出当前单位（支持状态筛选）出货记录 Excel';
});

// 固定列顺序 + 友好表头，避免动态 Object.keys 导致列错位
const colLabels = {
  id: 'ID',
  purchase_unit: '购买单位',
  product_name: '产品名称',
  model_number: '型号',
  quantity_kg: '数量 (KG)',
  quantity_tins: '数量 (桶)',
  tin_spec: '规格',
  unit_price: '单价',
  amount: '金额',
  status: '状态',
  created_at: '创建时间',
  updated_at: '更新时间',
  printed_at: '打印时间',
  printer_name: '打印机',
};

function normalizeUnits(data) {
  const list = data?.data || data?.units || [];
  return Array.isArray(list) ? list : [];
}

function normalizeRecords(data) {
  const list = data?.data || data?.records || [];
  return Array.isArray(list) ? list : [];
}

function rebuildColumns() {
  if (!records.value.length) {
    columns.value = [];
    return;
  }
  const record = records.value[0];
  const preferred = [
    'id',
    'purchase_unit',
    'product_name',
    'model_number',
    'quantity_kg',
    'quantity_tins',
    'tin_spec',
    'unit_price',
    'amount',
    'status',
    'created_at',
    'printed_at',
    'printer_name',
  ];
  columns.value = preferred.filter((k) => Object.prototype.hasOwnProperty.call(record, k));
}

async function loadUnits() {
  try {
    const data = await ordersApi.getShipmentRecordUnits();
    if (data?.success === false) throw new Error(data?.message || '加载单位失败');
    units.value = normalizeUnits(data);
  } catch (e) {
    console.error('加载单位失败:', e);
    units.value = [];
  }
}

async function loadTemplateOptions() {
  try {
    const data = await templatePreviewApi.listTemplates();
    const templates = Array.isArray(data?.templates) ? data.templates : [];
    const normalizedOptions = templates
      .filter((tpl) => tpl?.category === 'excel' && !tpl?.virtual)
      .filter((tpl) => {
        const scope = String(tpl?.business_scope || '').trim();
        const type = String(tpl?.template_type || '').trim();
        return scope === 'shipmentRecords' || type === '出货记录';
      })
      .map((tpl) => {
        const source = String(tpl?.source || '').trim();
        const hasFilePath = !!String(tpl?.file_path || tpl?.path || '').trim();
        const templateType = String(tpl?.template_type || '出货记录').trim();
        const name = String(tpl?.name || '未命名模板').trim();
        const id = String(tpl?.id || '').trim();
        // 优先级：有文件路径 > 系统默认 > 其他（无文件路径的历史冗余替换）
        const priority = hasFilePath ? 2 : (source === 'system-default' ? 1 : 0);
        return {
          id,
          name: `${name}（${templateType}）`,
          source,
          hasFilePath,
          templateType,
          dedupKey: `${name}__${templateType}`,
          priority
        };
      })
      .sort((a, b) => {
        if (a.priority !== b.priority) return b.priority - a.priority;
        return b.id.localeCompare(a.id);
      });

    const deduped = [];
    const seen = new Set();
    for (const item of normalizedOptions) {
      // 同名同类型时，保留“系统默认”与“自定义模板”各一条，避免自定义被系统默认覆盖。
      const dedupKey = `${item.dedupKey}__${item.source === 'system-default' ? 'system' : 'custom'}`;
      if (seen.has(dedupKey)) continue;
      seen.add(dedupKey);
      deduped.push(item);
    }

    templateOptions.value = deduped;
    if (templateOptions.value.length > 0) {
      selectedTemplateId.value = templateOptions.value[0].id;
    }
  } catch (e) {
    console.error('加载出货记录模板失败:', e);
    templateOptions.value = [];
  }
}

async function loadRecords() {
  const unit = String(selectedUnit.value || '').trim();
  if (!unit) {
    alert('请先选择购买单位');
    return;
  }
  loading.value = true;
  try {
    const data = await ordersApi.getShipmentRecords(unit);
    if (data?.success === false) throw new Error(data?.message || '加载记录失败');
    records.value = normalizeRecords(data);
    rebuildColumns();
  } catch (e) {
    console.error('加载出货记录失败:', e);
    records.value = [];
    rebuildColumns();
    alert(`加载失败: ${e?.message || '未知错误'}`);
  } finally {
    loading.value = false;
  }
}

const onShipmentRecordUpdated = (evt) => {
  const detail = evt?.detail || {};
  const eventUnit = String(detail?.purchaseUnit || '').trim();
  const currentUnit = String(selectedUnit.value || '').trim();
  if (!currentUnit) return;
  if (eventUnit && eventUnit !== currentUnit) return;
  loadRecords();
};

function openEdit(row) {
  if (!row?.id) return;
  editRowId.value = row.id;
  editForm.value = { ...row };
  showEditModal.value = true;
}

function closeEdit() {
  showEditModal.value = false;
  editRowId.value = null;
  editForm.value = {};
}

async function saveEdit() {
  if (!editRowId.value) return;
  loading.value = true;
  try {
    const payload = {
      id: editRowId.value,
      ...editForm.value
    };
    const data = await ordersApi.updateShipmentRecord(payload);
    if (!data?.success) throw new Error(data?.message || '保存失败');
    closeEdit();
    await loadRecords();
  } catch (e) {
    console.error('保存出货记录失败:', e);
    alert(`保存失败: ${e?.message || '未知错误'}`);
  } finally {
    loading.value = false;
  }
}

async function deleteRow(row) {
  if (!row?.id) return;
  if (!confirm('确定要删除该记录吗？')) return;
  loading.value = true;
  try {
    const data = await ordersApi.deleteShipmentRecord({ id: row.id });
    if (!data?.success) throw new Error(data?.message || '删除失败');
    await loadRecords();
  } catch (e) {
    console.error('删除出货记录失败:', e);
    alert(`删除失败: ${e?.message || '未知错误'}`);
  } finally {
    loading.value = false;
  }
}

async function exportRecords() {
  if (!selectedUnit.value || !selectedTemplateId.value) return;
  if (!selectedTemplateHasFile.value) {
    alert('所选模板未绑定 Excel 文件，请先在「业务对接」中上传并替换后再导出');
    return;
  }
  try {
    const response = await ordersApi.exportShipmentRecords(
      selectedUnit.value,
      selectedTemplateId.value,
      selectedStatusFilter.value === 'all' ? '' : selectedStatusFilter.value
    );
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    const suffix = selectedStatusFilter.value === 'all'
      ? '全部'
      : (selectedStatusFilter.value === 'printed' ? '已打印' : '未打印');
    a.download = `${selectedUnit.value}_出货记录_${suffix}.xlsx`;
    a.click();
    URL.revokeObjectURL(url);
  } catch (e) {
    console.error('导出失败:', e);
    alert(`导出失败: ${e?.message || '未知错误'}`);
  }
}

onMounted(() => {
  loadUnits();
  loadTemplateOptions();
  window.addEventListener('xcagi:shipment-record-updated', onShipmentRecordUpdated);
});

onBeforeUnmount(() => {
  window.removeEventListener('xcagi:shipment-record-updated', onShipmentRecordUpdated);
});

watch(selectedUnit, (unit) => {
  if (!String(unit || '').trim()) {
    records.value = [];
    rebuildColumns();
    return;
  }
  loadRecords();
});

function statusLabel(status) {
  const value = String(status || '').trim().toLowerCase();
  if (value === 'printed') return '已打印';
  return '未打印';
}

function statusClass(status) {
  const value = String(status || '').trim().toLowerCase();
  return value === 'printed' ? 'status-pill status-pill-printed' : 'status-pill status-pill-pending';
}

function templateBadge(tpl) {
  const source = String(tpl?.source || '').trim();
  if (source === 'system-default') return ' [系统默认]';
  if (tpl?.hasFilePath) return ' [已绑定文件]';
  return ' [未绑定文件]';
}
</script>

<style scoped>
.status-pill {
  display: inline-block;
  min-width: 64px;
  text-align: center;
  padding: 2px 10px;
  border-radius: 999px;
  font-size: 12px;
  line-height: 20px;
  font-weight: 600;
}

.status-pill-printed {
  color: #166534;
  background: #dcfce7;
  border: 1px solid #86efac;
}

.status-pill-pending {
  color: #374151;
  background: #f3f4f6;
  border: 1px solid #d1d5db;
}
</style>

