<template>
  <div class="page-view" id="view-materials">
    <div class="page-content">
      <div class="page-header">
        <h2>原材料仓库</h2>
        <div>
          <button v-if="selectedIds.length > 0" class="btn btn-danger" @click="batchDelete" style="margin-right:10px;">批量删除 ({{ selectedIds.length }})</button>
          <button class="btn btn-primary" @click="showAddModal">+ 添加原材料</button>
        </div>
      </div>
      <div v-if="store.lowStockMaterials.length > 0" class="warning-card">
        <div class="title">⚠️ 库存预警</div>
        <div id="lowStockList">
          <span v-for="(item, idx) in store.lowStockMaterials" :key="idx">
            {{ item.name }} (库存: {{ item.quantity }}/{{ item.min_stock || 0 }})
          </span>
        </div>
      </div>
      <div class="search-box">
        <input v-model="searchQuery" type="text" placeholder="搜索原材料..." @input="loadMaterials">
        <select v-model="selectedCategory">
          <option value="">全部分类</option>
          <option v-for="cat in store.categories" :key="cat" :value="cat">{{ cat }}</option>
        </select>
      </div>
      <div class="card">
        <DataTable
          :columns="columns"
          :data="store.materials"
          :loading="store.loading"
          :selectable="true"
          :selected-ids="selectedIds"
          :has-more="hasMore"
          :height="'500px'"
          row-key="id"
          empty-text="暂无原材料数据"
          @update:selected-ids="selectedIds = $event"
          @load-more="loadMoreMaterials"
        >
          <template #cell-code="{ value }">
            {{ value || '-' }}
          </template>
          <template #cell-name="{ value }">
            {{ value || '-' }}
          </template>
          <template #cell-category="{ value }">
            {{ value || '-' }}
          </template>
          <template #cell-quantity="{ row }">
            <span :class="{ 'text-red': row.quantity < (row.min_stock || 0) }">
              {{ row.quantity }} {{ row.unit || '' }}
            </span>
          </template>
          <template #cell-price="{ value }">
            {{ value ? '¥' + value.toFixed(2) : '-' }}
          </template>
          <template #cell-supplier="{ value }">
            {{ value || '-' }}
          </template>
          <template #actions="{ row }">
            <button class="btn btn-sm btn-secondary" @click="editMaterial(row)">编辑</button>
            <button class="btn btn-sm btn-danger" @click="handleDelete(row)">删除</button>
          </template>
        </DataTable>
      </div>
    </div>

    <ConfirmDialog
      v-model="showDeleteConfirm"
      title="确认删除"
      message="确定要删除该原材料吗？"
      confirm-text="删除"
      confirm-class="btn-danger"
      @confirm="confirmDelete"
    />

    <ConfirmDialog
      v-model="showBatchDeleteConfirm"
      title="批量删除"
      :message="`确定要删除选中的 ${selectedIds.length} 个原材料吗？`"
      confirm-text="批量删除"
      confirm-class="btn-danger"
      @confirm="confirmBatchDelete"
    />

    <div v-if="showModal" class="modal show">
      <div class="modal-content">
        <div class="modal-header">{{ isEdit ? '编辑原材料' : '添加原材料' }}</div>
        <div class="modal-body">
          <div class="form-group">
            <label>原材料编码 *</label>
            <input v-model="formData.code" type="text" placeholder="如：M001">
          </div>
          <div class="form-group">
            <label>名称 *</label>
            <input v-model="formData.name" type="text" placeholder="原材料名称">
          </div>
          <div class="form-group">
            <label>分类</label>
            <input v-model="formData.category" type="text" placeholder="如：油漆、板材">
          </div>
          <div class="form-group">
            <label>规格</label>
            <input v-model="formData.spec" type="text" placeholder="规格描述">
          </div>
          <div class="form-group">
            <label>单位</label>
            <input v-model="formData.unit" type="text" value="个">
          </div>
          <div class="form-group">
            <label>库存数量</label>
            <input v-model.number="formData.quantity" type="number" value="0">
          </div>
          <div class="form-group">
            <label>单价</label>
            <input v-model.number="formData.price" type="number" step="0.01" value="0">
          </div>
          <div class="form-group">
            <label>供应商</label>
            <input v-model="formData.supplier" type="text" placeholder="供应商名称">
          </div>
          <div class="form-group">
            <label>最低库存</label>
            <input v-model.number="formData.min_stock" type="number" value="0">
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn btn-secondary" @click="showModal = false">取消</button>
          <button class="btn btn-primary" @click="saveMaterial">保存</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { useMaterialsStore } from '../stores/materials';
import DataTable from '../components/DataTable.vue';
import ConfirmDialog from '../components/ConfirmDialog.vue';

const store = useMaterialsStore();

const searchQuery = ref('');
const selectedCategory = ref('');
const showModal = ref(false);
const isEdit = ref(false);
const selectedIds = ref([]);
const currentPage = ref(1);
const perPage = ref(20);
const hasMore = ref(true);
const formData = ref({
  id: null,
  code: '',
  name: '',
  category: '',
  spec: '',
  unit: '个',
  quantity: 0,
  price: 0,
  supplier: '',
  min_stock: 0
});
const showDeleteConfirm = ref(false);
const showBatchDeleteConfirm = ref(false);
const itemToDelete = ref(null);

const columns = [
  { key: 'code', label: '编码' },
  { key: 'name', label: '名称' },
  { key: 'category', label: '分类' },
  { key: 'quantity', label: '库存' },
  { key: 'price', label: '单价' },
  { key: 'supplier', label: '供应商' }
];

const loadMaterials = async (reset = true) => {
  if (reset) {
    currentPage.value = 1;
    hasMore.value = true;
  }
  const params = { page: currentPage.value, per_page: perPage.value };
  if (searchQuery.value) params.search = searchQuery.value;
  if (selectedCategory.value) params.category = selectedCategory.value;
  const result = await store.fetchMaterials(params);
  if (result && result.data) {
    if (reset) {
      store.materials = result.data;
    } else {
      store.materials = [...store.materials, ...result.data];
    }
    hasMore.value = store.materials.length < (result.total || 0);
    currentPage.value++;
  }
};

const loadMoreMaterials = async () => {
  if (store.loading || !hasMore.value) return;
  await loadMaterials(false);
};

const showAddModal = () => {
  isEdit.value = false;
  formData.value = {
    id: null,
    code: '',
    name: '',
    category: '',
    spec: '',
    unit: '个',
    quantity: 0,
    price: 0,
    supplier: '',
    min_stock: 0
  };
  showModal.value = true;
};

const editMaterial = (material) => {
  isEdit.value = true;
  formData.value = { ...material };
  showModal.value = true;
};

const saveMaterial = async () => {
  const result = isEdit.value && formData.value.id
    ? await store.updateMaterial(formData.value.id, formData.value)
    : await store.createMaterial(formData.value);

  if (result.success) {
    showModal.value = false;
    loadMaterials();
  } else {
    alert('保存失败: ' + (result.message || '未知错误'));
  }
};

const handleDelete = (material) => {
  itemToDelete.value = material;
  showDeleteConfirm.value = true;
};

const confirmDelete = async () => {
  if (!itemToDelete.value) return;
  const result = await store.deleteMaterial(itemToDelete.value.id);
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
    loadMaterials();
  } else {
    alert('批量删除失败: ' + (result.message || '未知错误'));
  }
};

onMounted(() => {
  loadMaterials();
});
</script>

<style scoped>
.text-red {
  color: #dc3545;
  font-weight: bold;
}
</style>
