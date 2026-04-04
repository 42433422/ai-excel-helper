<template>
  <div class="page-view" id="view-products">
    <div class="page-content">
      <div class="page-header">
        <h2>产品管理</h2>
        <div>
          <button class="btn btn-secondary" @click="exportPriceList" style="margin-right:10px;" title="导出当前单位产品价格表">导出价格表</button>
          <button v-if="selectedIds.length > 0" class="btn btn-danger" @click="batchDelete" style="margin-right:10px;">批量删除 ({{ selectedIds.length }})</button>
          <button class="btn btn-primary" @click="showAddModal">+ 添加产品</button>
        </div>
      </div>
      <div class="search-box" style="display:flex;flex-wrap:wrap;align-items:center;gap:10px;">
        <label style="white-space:nowrap;">产品单位：</label>
        <select v-model="selectedUnit" style="min-width:180px;" @change="loadProducts">
          <option value="">请选择产品单位</option>
          <option v-for="u in units" :key="u" :value="u">{{ u }}</option>
        </select>
        <select v-model="selectedTemplateId" style="min-width:220px;">
          <option value="">系统默认导出模板</option>
          <option v-for="tpl in templateOptions" :key="tpl.id" :value="tpl.id">{{ tpl.name }}</option>
        </select>
        <input v-model="searchQuery" type="text" placeholder="搜索产品型号或名称..." @input="loadProducts">
      </div>
      <div class="card">
        <DataTable
          :columns="columns"
          :data="products"
          :loading="loading"
          :selectable="true"
          :selected-ids="selectedIds"
          :has-more="hasMore"
          :height="'500px'"
          row-key="id"
          empty-text="暂无产品数据"
          @update:selected-ids="selectedIds = $event"
          @load-more="loadMoreProducts"
        >
          <template #cell-model_number="{ value }">
            {{ value || '-' }}
          </template>
          <template #cell-name="{ value }">
            {{ value || '-' }}
          </template>
          <template #cell-specification="{ value }">
            {{ value || '-' }}
          </template>
          <template #cell-price="{ value }">
            {{ value ? '¥' + value.toFixed(2) : '-' }}
          </template>
          <template #actions="{ row }">
            <button type="button" class="btn btn-sm btn-secondary" @click.stop="editProduct(row)">编辑</button>
            <button type="button" class="btn btn-sm btn-danger" @click.stop="handleDelete(row)">删除</button>
          </template>
        </DataTable>
      </div>
    </div>

    <ConfirmDialog
      v-model="showDeleteConfirm"
      title="确认删除"
      :message="`确定要删除该产品吗？`"
      confirm-text="删除"
      confirm-class="btn-danger"
      @confirm="confirmDelete"
    />

    <ConfirmDialog
      v-model="showBatchDeleteConfirm"
      title="批量删除"
      :message="`确定要删除选中的 ${selectedIds.length} 个产品吗？`"
      confirm-text="批量删除"
      confirm-class="btn-danger"
      @confirm="confirmBatchDelete"
    />

    <div v-if="showModal" class="modal active">
      <div class="modal-content">
        <div class="modal-header">{{ isEdit ? '编辑产品' : '添加产品' }}</div>
        <div class="modal-body">
          <div class="form-group">
            <label>产品型号 *</label>
            <input v-model="formData.model_number" type="text" placeholder="如：A001">
          </div>
          <div class="form-group">
            <label>产品名称 *</label>
            <input v-model="formData.name" type="text" placeholder="产品名称">
          </div>
          <div class="form-group">
            <label>规格</label>
            <input v-model="formData.specification" type="text" placeholder="规格描述">
          </div>
          <div class="form-group">
            <label>价格</label>
            <input v-model.number="formData.price" type="number" step="0.01" placeholder="0.00">
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn btn-secondary" @click="showModal = false">取消</button>
          <button class="btn btn-primary" @click="saveProduct">保存</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { useProductsStore } from '../stores/products';
import { storeToRefs } from 'pinia';
import customersApi from '../api/customers';
import productsApi from '../api/products';
import templatePreviewApi from '../api/templatePreview';
import DataTable from '../components/DataTable.vue';
import ConfirmDialog from '../components/ConfirmDialog.vue';

const store = useProductsStore();
const { products, loading } = storeToRefs(store);

const units = ref([]);
const showModal = ref(false);
const isEdit = ref(false);
const selectedIds = ref([]);
const selectAll = ref(false);
const searchQuery = ref('');
const selectedUnit = ref('');
const currentPage = ref(1);
const perPage = ref(1000);
const hasMore = ref(false);
const selectedTemplateId = ref('');
const templateOptions = ref([]);
const formData = ref({
  id: null,
  model_number: '',
  name: '',
  specification: '',
  price: 0
});
const showDeleteConfirm = ref(false);
const showBatchDeleteConfirm = ref(false);
const itemToDelete = ref(null);

const columns = [
  { key: 'model_number', label: '型号' },
  { key: 'name', label: '名称' },
  { key: 'specification', label: '规格' },
  { key: 'price', label: '价格' }
];

const currentRequestId = ref(0);

const loadProducts = async (reset = true) => {
  const requestId = ++currentRequestId.value;
  if (reset) {
    currentPage.value = 1;
    hasMore.value = false;
  }
  const params = { page: currentPage.value, per_page: perPage.value };
  if (searchQuery.value) params.keyword = searchQuery.value;
  if (selectedUnit.value) params.unit = selectedUnit.value;
  const result = await store.fetchProducts(params);
  if (requestId !== currentRequestId.value) return;
  if (result && result.data) {
    if (reset) {
      products.value = result.data;
    } else {
      products.value = [...products.value, ...result.data];
    }
    hasMore.value = false;
    currentPage.value++;
  }
};

let isLoadingMore = false;

const loadMoreProducts = async () => {
  if (loading.value || !hasMore.value || isLoadingMore) return;
  isLoadingMore = true;
  try {
    await loadProducts(false);
  } finally {
    isLoadingMore = false;
  }
};

async function loadUnits() {
  try {
    const resp = await customersApi.getCustomers({ page: 1, per_page: 1000 });
    if (!resp?.success) throw new Error(resp?.message || '加载客户/购买单位失败');
    const list = resp?.data || [];
    units.value = Array.isArray(list) ? list.map(c => c.unit_name || c.customer_name).filter(Boolean) : [];
  } catch (e) {
    console.error('加载产品单位失败:', e);
    units.value = [];
  }
}

const showAddModal = () => {
  isEdit.value = false;
  formData.value = {
    id: null,
    model_number: '',
    name: '',
    specification: '',
    price: 0
  };
  showModal.value = true;
};

const editProduct = (product) => {
  isEdit.value = true;
  formData.value = { ...product };
  showModal.value = true;
};

const saveProduct = async () => {
  const result = isEdit.value && formData.value.id
    ? await store.updateProduct(formData.value.id, formData.value)
    : await store.createProduct(formData.value);

  if (result.success) {
    showModal.value = false;
    loadProducts();
  } else {
    alert('保存失败: ' + (result.message || '未知错误'));
  }
};

const handleDelete = (product) => {
  itemToDelete.value = product;
  showDeleteConfirm.value = true;
};

const confirmDelete = async () => {
  if (!itemToDelete.value) return;
  const result = await store.deleteProduct(itemToDelete.value.id);
  if (!result.success) {
    alert('删除失败: ' + (result.message || '未知错误'));
  }
  itemToDelete.value = null;
};

const batchDelete = () => {
  showBatchDeleteConfirm.value = true;
};

const confirmBatchDelete = async () => {
  const result = await store.batchDelete(selectedIds.value);
  if (result.success) {
    selectedIds.value = [];
    selectAll.value = false;
    loadProducts();
  } else {
    alert('批量删除失败: ' + (result.message || '未知错误'));
  }
};

const exportPriceList = async () => {
  try {
    const params = {};
    if (selectedUnit.value) params.unit = selectedUnit.value;
    if (searchQuery.value) params.keyword = searchQuery.value;
    if (selectedTemplateId.value) params.template_id = selectedTemplateId.value;
    const response = await productsApi.exportUnitProductsXlsx(params);
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    const contentDisposition = response.headers?.get('content-disposition') || '';
    let filename = '产品价格表.xlsx';
    const utf8NameMatch = contentDisposition.match(/filename\*=UTF-8''([^;]+)/i);
    const plainNameMatch = contentDisposition.match(/filename="?([^";]+)"?/i);
    if (utf8NameMatch?.[1]) {
      try {
        filename = decodeURIComponent(utf8NameMatch[1]);
      } catch (_) {
        filename = utf8NameMatch[1];
      }
    } else if (plainNameMatch?.[1]) {
      filename = plainNameMatch[1];
    }
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  } catch (e) {
    console.error('导出失败:', e);
    alert('导出失败: ' + (e.message || '未知错误'));
  }
};

const loadTemplateOptions = async () => {
  try {
    const res = await templatePreviewApi.listTemplates();
    if (!res?.success) return;
    const templates = Array.isArray(res.templates) ? res.templates : [];
    templateOptions.value = templates
      .filter((tpl) => tpl?.category === 'excel' && !tpl?.virtual)
      .filter((tpl) => {
        const scope = String(tpl?.business_scope || '').trim();
        const type = String(tpl?.template_type || '').trim();
        return scope === 'products' || type === '产品';
      })
      .map((tpl) => ({
        id: String(tpl.id),
        name: `${tpl.name || '未命名模板'}（${tpl.template_type || '产品'}）`,
      }));
    // 默认走系统导出结构，避免误用历史模板带出额外列。
    if (!templateOptions.value.find((tpl) => String(tpl.id) === String(selectedTemplateId.value))) {
      selectedTemplateId.value = '';
    }
  } catch (e) {
    console.error('加载产品导出模板失败:', e);
  }
};

onMounted(() => {
  loadUnits().then(() => loadProducts());
  loadTemplateOptions();
});
</script>

