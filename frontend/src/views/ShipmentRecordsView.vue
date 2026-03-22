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
          <button class="btn btn-primary" @click="loadRecords" :disabled="loading">查看记录</button>
          <button class="btn btn-success" title="导出当前单位出货记录 Excel" @click="exportRecords" :disabled="!selectedUnit || loading">导出 Excel</button>
        </div>
      </div>
      <div class="card">
        <div class="card-header">
          {{ selectedUnit ? `${selectedUnit} - 共 ${records.length} 条` : '选择购买单位后点击「查看记录」加载数据' }}
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
              <tr v-else-if="records.length === 0">
                <td :colspan="Math.max(columns.length + 1, 1)" class="empty-state">请先选择购买单位并加载</td>
              </tr>
              <tr v-for="row in records" :key="row.id || JSON.stringify(row)">
                <td v-for="col in columns" :key="col">{{ row[col] ?? '' }}</td>
                <td>
                  <button class="btn btn-sm btn-secondary" @click="openEdit(row)" :disabled="!row.id">编辑</button>
                  <button class="btn btn-sm btn-danger" @click="deleteRow(row)" :disabled="!row.id">删除</button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div v-if="showEditModal" class="modal show">
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
import { computed, onMounted, ref } from 'vue';
import ordersApi from '../api/orders';

const loading = ref(false);
const units = ref([]);
const selectedUnit = ref('');
const records = ref([]);
const columns = ref([]);
const showEditModal = ref(false);
const editRowId = ref(null);
const editForm = ref({});

const editableColumns = computed(() => columns.value.filter((c) => c !== 'id'));

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

async function loadRecords() {
  if (!selectedUnit.value) {
    alert('请先选择购买单位');
    return;
  }
  loading.value = true;
  try {
    const data = await ordersApi.getShipmentRecords(selectedUnit.value);
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
  if (!selectedUnit.value) return;
  try {
    const response = await ordersApi.exportShipmentRecords(selectedUnit.value);
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${selectedUnit.value}_出货记录.xlsx`;
    a.click();
    URL.revokeObjectURL(url);
  } catch (e) {
    console.error('导出失败:', e);
    alert(`导出失败: ${e?.message || '未知错误'}`);
  }
}

onMounted(() => {
  loadUnits();
});
</script>
