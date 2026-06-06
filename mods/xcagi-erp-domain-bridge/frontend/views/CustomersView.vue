<template>
  <div class="page-view" id="view-customers">
    <div class="page-content">
      <div class="page-header customers-page-header">
        <div class="customers-header-main">
          <h2>{{ pageNavTitle }}</h2>
          <p class="muted customers-header-desc">
            购买单位与「{{ productsNavLabel }}」「{{ shipmentNavLabel }}」同源；可选单位筛选客户列表。
            <span v-if="pageNavTitle !== '客户管理'" class="customers-header-note">（当前行业显示为「{{ pageNavTitle }}」，数据实体为购买单位/客户）</span>
          </p>
          <div class="customers-unit-filter">
            <label class="customers-unit-label" for="customers-purchase-unit">购买单位</label>
            <select
              id="customers-purchase-unit"
              v-model="selectedPurchaseUnit"
              class="customers-unit-select"
              title="与产品页、出货记录页单位下拉一致"
            >
              <option value="">全部购买单位</option>
              <option
                v-for="(unit, idx) in purchaseUnitOptions"
                :key="unitOptionKey(unit, idx)"
                :value="unitOptionValue(unit)"
              >
                {{ unitOptionLabel(unit) }}
              </option>
            </select>
          </div>
        </div>
        <div class="header-actions customers-header-actions">
          <select
            v-model="selectedTemplateId"
            class="template-select"
            :disabled="loadingTemplateOptions || templateOptions.length === 0"
            title="客户管理导出模板"
          >
            <option value="" disabled>{{ loadingTemplateOptions ? '加载模板中...' : '请选择导出模板' }}</option>
            <option v-for="tpl in templateOptions" :key="tpl.id" :value="tpl.id">
              {{ tpl.name }}
            </option>
          </select>
          <button class="btn btn-icon" @click="triggerImport" title="上传Excel更新购买单位">
            <i class="fa fa-upload" aria-hidden="true"></i>
          </button>
          <input
            ref="importFileInput"
            type="file"
            accept=".xlsx"
            style="display:none"
            @change="handleImport"
          >
          <button
            class="btn btn-icon"
            @click="exportCustomers"
            title="导出购买单位Excel"
            :disabled="!selectedTemplateId"
          >
            <svg class="excel-icon-svg" viewBox="0 0 24 24" width="22" height="22">
              <rect width="24" height="24" rx="3" fill="#217346"/>
              <path stroke="#fff" stroke-width="2.2" stroke-linecap="round" fill="none" d="M7 7l10 10M17 7L7 17"/>
            </svg>
          </button>
          <button class="btn btn-primary" @click="openAddModal">+ 新建客户</button>
          <button v-if="selectedIds.length > 0" class="btn btn-danger" @click="handleBatchDelete">批量删除 ({{ selectedIds.length }})</button>
        </div>
      </div>
      <div class="stat-cards">
        <div class="stat-card">
          <div class="number">{{ totalCustomers }}</div>
          <div class="label">客户总数</div>
        </div>
      </div>
      <div class="card">
        <DataTable
          :columns="columns"
          :data="customers"
          :loading="loading"
          :selectable="true"
          :selected-ids="selectedIds"
          :has-more="hasMore"
          row-key="id"
          empty-text="暂无客户数据"
          @update:selected-ids="selectedIds = $event"
          @load-more="loadMoreCustomers"
        >
          <template #cell-customer_name="{ row }">
            {{ row.customer_name || row.unit_name || row.name || '-' }}
          </template>
          <template #cell-contact_person="{ value }">
            {{ value || '-' }}
          </template>
          <template #cell-contact_phone="{ value }">
            {{ value || '-' }}
          </template>
          <template #cell-address="{ value }">
            {{ value || '-' }}
          </template>
          <template #actions="{ row }">
            <button
              class="btn btn-primary"
              style="padding: 6px 10px; font-size: 12px; margin-right: 5px;"
              @click="openEditModal(row)"
            >
              编辑
            </button>
            <button
              class="btn btn-danger"
              style="padding: 6px 10px; font-size: 12px;"
              @click="handleDelete(row)"
            >
              删除
            </button>
          </template>
        </DataTable>
      </div>
    </div>

    <ConfirmDialog
      v-model="showDeleteConfirm"
      title="确认删除"
      :message="`确定删除客户 &quot;${itemToDelete?.customer_name || itemToDelete?.unit_name || ''}&quot; 吗？`"
      confirm-text="删除"
      confirm-class="btn-danger"
      @confirm="confirmDelete"
    />

    <ConfirmDialog
      v-model="showBatchDeleteConfirm"
      title="批量删除"
      :message="`确定要删除选中的 ${selectedIds.length} 个客户吗？`"
      confirm-text="批量删除"
      confirm-class="btn-danger"
      @confirm="confirmBatchDelete"
    />

    <div v-if="showAddModal" class="modal-overlay" @click.self="closeAddModal">
      <div class="modal-content">
        <div class="modal-header">
          <h3>新建客户</h3>
          <button class="btn btn-icon" @click="closeAddModal">×</button>
        </div>
        <div class="modal-body">
          <div class="form-group">
            <label>客户名称 *</label>
            <input type="text" v-model="addForm.customer_name" placeholder="请输入客户名称" />
          </div>
          <div class="form-group">
            <label>联系人</label>
            <input type="text" v-model="addForm.contact_person" placeholder="请输入联系人" />
          </div>
          <div class="form-group">
            <label>电话</label>
            <input type="text" v-model="addForm.contact_phone" placeholder="请输入联系电话" />
          </div>
          <div class="form-group">
            <label>地址</label>
            <input type="text" v-model="addForm.address" placeholder="请输入地址" />
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn btn-secondary" @click="closeAddModal">取消</button>
          <button class="btn btn-primary" @click="saveAdd" :disabled="loading">创建</button>
        </div>
      </div>
    </div>

    <div v-if="showEditModal" class="modal-overlay" @click.self="closeEditModal">
      <div class="modal-content">
        <div class="modal-header">
          <h3>编辑客户</h3>
          <button class="btn btn-icon" @click="closeEditModal">×</button>
        </div>
        <div class="modal-body">
          <div class="form-group">
            <label>客户名称</label>
            <input type="text" v-model="editForm.customer_name" placeholder="请输入客户名称" />
          </div>
          <div class="form-group">
            <label>联系人</label>
            <input type="text" v-model="editForm.contact_person" placeholder="请输入联系人" />
          </div>
          <div class="form-group">
            <label>电话</label>
            <input type="text" v-model="editForm.contact_phone" placeholder="请输入联系电话" />
          </div>
          <div class="form-group">
            <label>地址</label>
            <input type="text" v-model="editForm.address" placeholder="请输入地址" />
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn btn-secondary" @click="closeEditModal">取消</button>
          <button class="btn btn-primary" @click="saveEdit">保存</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue';
import customersApi from '@/api/customers';
import ordersApi from '@/api/orders';
import templatePreviewApi from '@/api/templatePreview';
import DataTable from '@/components/DataTable.vue';
import ConfirmDialog from '@/components/ConfirmDialog.vue';
import { appAlert } from '@/utils/appDialog';
import { useCoreNavLabel } from '@/composables/useCoreNavLabel';

const pageNavTitle = useCoreNavLabel('customers');
const productsNavLabel = useCoreNavLabel('products');
const shipmentNavLabel = useCoreNavLabel('shipment-records');

const customers = ref([]);
const purchaseUnitOptions = ref([]);
const selectedPurchaseUnit = ref('');
const loading = ref(false);
const selectedIds = ref([]);
const page = ref(1);
const perPage = 20;
const totalCustomers = ref(0);
const hasMore = ref(false);
const importFileInput = ref(null);
const showEditModal = ref(false);
const showDeleteConfirm = ref(false);
const showBatchDeleteConfirm = ref(false);
const showAddModal = ref(false);
const addForm = ref({ customer_name: '', contact_person: '', contact_phone: '', address: '' });
const itemToDelete = ref(null);
const templateOptions = ref([]);
const selectedTemplateId = ref('');
const loadingTemplateOptions = ref(false);
const editForm = ref({
  id: null,
  customer_name: '',
  contact_person: '',
  contact_phone: '',
  address: ''
});

const columns = [
  { key: 'customer_name', label: '客户名称' },
  { key: 'contact_person', label: '联系人' },
  { key: 'contact_phone', label: '电话' },
  { key: 'address', label: '地址' }
];

function normalizeUnitsPayload(data) {
  const list = data?.data || data?.units || [];
  return Array.isArray(list) ? list : [];
}

function unitOptionValue(unit) {
  if (unit == null) return '';
  if (typeof unit === 'string') return unit.trim();
  const v = unit.name ?? unit.symbol ?? unit.unit_name ?? unit.customer_name ?? unit.unitName;
  return String(v ?? '').trim();
}

function unitOptionLabel(unit) {
  return unitOptionValue(unit) || '(未命名单位)';
}

function unitOptionKey(unit, idx) {
  if (unit != null && typeof unit === 'object' && unit.id != null) return `pu-${unit.id}`;
  const v = unitOptionValue(unit);
  return v ? `pu-${v}` : `pu-idx-${idx}`;
}

async function loadPurchaseUnitOptions() {
  try {
    const data = await ordersApi.getShipmentRecordUnits();
    if (data?.success === false) throw new Error(data?.message || '加载单位失败');
    purchaseUnitOptions.value = normalizeUnitsPayload(data);
  } catch (e) {
    console.error('加载购买单位失败:', e);
    purchaseUnitOptions.value = [];
  }
}

const mergeCustomers = (existing, incoming) => {
  const merged = [...existing];
  const seen = new Set(existing.map((x) => x?.id).filter((id) => id !== undefined && id !== null));
  for (const row of incoming) {
    const rowId = row?.id;
    if (rowId === undefined || rowId === null) {
      merged.push(row);
      continue;
    }
    if (!seen.has(rowId)) {
      seen.add(rowId);
      merged.push(row);
    }
  }
  return merged;
};

const loadCustomers = async ({ reset = true } = {}) => {
  if (loading.value) return;
  loading.value = true;
  try {
    const nextPage = reset ? 1 : page.value;
    const pu = String(selectedPurchaseUnit.value || '').trim();
    const data = await customersApi.getCustomers({
      page: nextPage,
      per_page: perPage,
      ...(pu ? { purchase_unit: pu } : {})
    });
    if (data.success) {
      const incoming = data.customers || data.data || [];
      const total = Number(data.total ?? incoming.length ?? 0);
      totalCustomers.value = Number.isFinite(total) ? total : incoming.length;

      if (reset) {
        customers.value = incoming;
      } else {
        customers.value = mergeCustomers(customers.value, incoming);
      }

      page.value = nextPage + 1;
      hasMore.value = customers.value.length < totalCustomers.value;
    }
  } catch (e) {
    console.error('加载客户失败:', e);
  } finally {
    loading.value = false;
  }
};

const loadMoreCustomers = async () => {
  if (!hasMore.value || loading.value) return;
  await loadCustomers({ reset: false });
};

const handleDelete = (customer) => {
  itemToDelete.value = customer;
  showDeleteConfirm.value = true;
};

const confirmDelete = async () => {
  if (!itemToDelete.value?.id) return;
  try {
    await customersApi.deleteCustomer(itemToDelete.value.id);
    await loadCustomers({ reset: true });
  } catch (e) {
    console.error('删除客户失败:', e);
    await appAlert('删除失败: ' + (e?.message || '未知错误'));
  }
  itemToDelete.value = null;
};

const handleBatchDelete = () => {
  showBatchDeleteConfirm.value = true;
};

const confirmBatchDelete = async () => {
  try {
    await customersApi.batchDeleteCustomers(selectedIds.value);
    selectedIds.value = [];
    await loadCustomers({ reset: true });
  } catch (e) {
    console.error('批量删除失败:', e);
    await appAlert('批量删除失败: ' + (e.message || '未知错误'));
  }
};

const openEditModal = (customer) => {
  editForm.value = {
    id: customer.id,
    customer_name: customer.customer_name || customer.unit_name || customer.name || '',
    contact_person: customer.contact_person || '',
    contact_phone: customer.contact_phone || '',
    address: customer.address || customer.contact_address || ''
  };
  showEditModal.value = true;
};

const closeEditModal = () => {
  showEditModal.value = false;
};

const openAddModal = () => {
  addForm.value = { customer_name: '', contact_person: '', contact_phone: '', address: '' };
  showAddModal.value = true;
};

const closeAddModal = () => {
  showAddModal.value = false;
};

const saveAdd = async () => {
  if (!addForm.value.customer_name?.trim()) {
    await appAlert('客户名称不能为空');
    return;
  }
  try {
    await customersApi.createCustomer({
      customer_name: addForm.value.customer_name,
      contact_person: addForm.value.contact_person,
      contact_phone: addForm.value.contact_phone,
      contact_address: addForm.value.address,
    });
    await appAlert('客户创建成功');
    closeAddModal();
    await loadCustomers({ reset: true });
  } catch (e) {
    await appAlert('创建失败: ' + (e?.message || '未知错误'));
  }
};

const saveEdit = async () => {
  if (!editForm.value.id) return;
  if (!editForm.value.customer_name?.trim()) {
    await appAlert('客户名称不能为空');
    return;
  }
  try {
    await customersApi.updateCustomer(editForm.value.id, {
      customer_name: editForm.value.customer_name,
      contact_person: editForm.value.contact_person,
      contact_phone: editForm.value.contact_phone,
      contact_address: editForm.value.address
    });
    await appAlert('保存成功');
    closeEditModal();
    await loadCustomers({ reset: true });
  } catch (e) {
    console.error('保存失败:', e);
    await appAlert('保存失败: ' + (e?.message || '未知错误'));
  }
};

const exportCustomers = async () => {
  if (!selectedTemplateId.value) {
    await appAlert('请先选择导出模板');
    return;
  }
  try {
    const response = await customersApi.exportCustomersXlsx(selectedTemplateId.value);
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = '购买单位列表.xlsx';
    a.click();
    URL.revokeObjectURL(url);
  } catch (e) {
    console.error('导出失败:', e);
    await appAlert('导出失败: ' + (e.message || '未知错误'));
  }
};

const loadTemplateOptions = async () => {
  loadingTemplateOptions.value = true;
  try {
    const res = await templatePreviewApi.listTemplates();
    if (!res?.success) return;
    const templates = Array.isArray(res.templates) ? res.templates : [];
    templateOptions.value = templates.filter((tpl) => {
      if (!tpl || tpl.virtual || tpl.category !== 'excel') return false;
      const scope = String(tpl.business_scope || '').trim();
      const type = String(tpl.template_type || '').trim();
      return scope === 'customers' || type === '客户';
    });
    if (!selectedTemplateId.value && templateOptions.value.length) {
      selectedTemplateId.value = String(templateOptions.value[0].id);
    }
  } catch (e) {
    console.error('加载客户导出模板失败:', e);
  } finally {
    loadingTemplateOptions.value = false;
  }
};

const triggerImport = () => {
  importFileInput.value?.click();
};

const handleImport = async (e) => {
  const file = e.target.files?.[0];
  if (!file) return;

  try {
    const formData = new FormData();
    formData.append('file', file);
    const data = await customersApi.importCustomersExcel(formData);
    if (data.success) {
      await appAlert('导入成功！');
      await loadCustomers({ reset: true });
    }
  } catch (e) {
    console.error('导入失败:', e);
    await appAlert('导入失败: ' + (e.message || '未知错误'));
  } finally {
    e.target.value = '';
  }
};

watch(selectedPurchaseUnit, () => {
  loadCustomers({ reset: true });
});

onMounted(() => {
  loadPurchaseUnitOptions();
  loadCustomers({ reset: true });
  loadTemplateOptions();
});
</script>

<style scoped>
.customers-page-header {
  align-items: flex-start;
  gap: 16px 24px;
  flex-wrap: wrap;
}

.customers-header-main {
  flex: 1;
  min-width: 0;
}

.customers-header-main h2 {
  margin: 0 0 6px;
}

.customers-header-desc {
  margin: 0 0 10px;
  font-size: 12px;
  line-height: 1.45;
  max-width: 42em;
}

.customers-unit-filter {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
}

.customers-unit-label {
  white-space: nowrap;
  font-size: 13px;
  font-weight: 500;
  margin: 0;
}

.customers-unit-select {
  min-width: 200px;
  height: 32px;
}

.customers-header-actions {
  flex-shrink: 0;
  align-self: flex-start;
}

.modal-overlay {
  display: flex;
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  z-index: 1000;
  justify-content: center;
  align-items: center;
}

.modal-content {
  background: white;
  border-radius: 8px;
  width: 450px;
  max-width: 90%;
  max-height: 90vh;
  overflow-y: auto;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid #e0e0e0;
}

.modal-header h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
}

.modal-body {
  padding: 20px;
}

.form-group {
  margin-bottom: 15px;
}

.form-group label {
  display: block;
  margin-bottom: 5px;
  font-weight: 500;
  color: #333;
}

.form-group input {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
  box-sizing: border-box;
}

.form-group input:focus {
  outline: none;
  border-color: #4a90d9;
}

.modal-footer {
  display: flex;
  gap: 10px;
  justify-content: flex-end;
  padding: 16px 20px;
  border-top: 1px solid #e0e0e0;
}

.template-select {
  min-width: 180px;
  height: 32px;
  border: 1px solid #d6dce5;
  border-radius: 6px;
  background: #fff;
  color: #2f3a45;
  padding: 0 10px;
}
</style>
