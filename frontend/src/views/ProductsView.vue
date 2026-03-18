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
        <label style="white-space:nowrap;">购买单位：</label>
        <select v-model="selectedUnit" style="min-width:180px;">
          <option value="">请选择购买单位</option>
        </select>
        <input v-model="searchQuery" type="text" placeholder="搜索产品型号或名称..." @input="loadProducts">
      </div>
      <div class="card">
        <table class="data-table">
          <thead>
            <tr>
              <th><input type="checkbox" v-model="selectAll" @change="toggleSelectAll"></th>
              <th>型号</th>
              <th>名称</th>
              <th>规格</th>
              <th>价格</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading">
              <td colspan="6" class="empty-state">加载中...</td>
            </tr>
            <tr v-else-if="products.length === 0">
              <td colspan="6" class="empty-state">暂无产品数据</td>
            </tr>
            <tr v-for="product in products" :key="product.id">
              <td><input type="checkbox" :value="product.id" v-model="selectedIds"></td>
              <td>{{ product.model_number || '-' }}</td>
              <td>{{ product.name || '-' }}</td>
              <td>{{ product.spec || '-' }}</td>
              <td>{{ product.price ? '¥' + product.price.toFixed(2) : '-' }}</td>
              <td>
                <button class="btn btn-sm btn-secondary" @click="editProduct(product)">编辑</button>
                <button class="btn btn-sm btn-danger" @click="deleteProduct(product)">删除</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div v-if="showModal" class="modal show">
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
            <input v-model="formData.spec" type="text" placeholder="规格描述">
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
import { ref, onMounted, computed } from 'vue';
import productsApi from '../api/products';

const products = ref([]);
const loading = ref(false);
const showModal = ref(false);
const isEdit = ref(false);
const selectedIds = ref([]);
const selectAll = ref(false);
const searchQuery = ref('');
const selectedUnit = ref('');
const formData = ref({
  id: null,
  model_number: '',
  name: '',
  spec: '',
  price: 0
});

const loadProducts = async () => {
  loading.value = true;
  try {
    const params = {};
    if (searchQuery.value) params.search = searchQuery.value;
    if (selectedUnit.value) params.unit = selectedUnit.value;
    const data = await productsApi.getProducts(params);
    if (data.success) {
      products.value = data.data || [];
    }
  } catch (e) {
    console.error('加载产品失败:', e);
  } finally {
    loading.value = false;
  }
};

const showAddModal = () => {
  isEdit.value = false;
  formData.value = {
    id: null,
    model_number: '',
    name: '',
    spec: '',
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
  try {
    if (isEdit.value && formData.value.id) {
      await productsApi.updateProduct(formData.value.id, formData.value);
    } else {
      await productsApi.createProduct(formData.value);
    }
    showModal.value = false;
    loadProducts();
  } catch (e) {
    console.error('保存产品失败:', e);
    alert('保存失败: ' + (e.message || '未知错误'));
  }
};

const deleteProduct = async (product) => {
  if (!confirm('确定要删除该产品吗？')) return;
  try {
    await productsApi.deleteProduct(product.id);
    loadProducts();
  } catch (e) {
    console.error('删除产品失败:', e);
    alert('删除失败: ' + (e.message || '未知错误'));
  }
};

const toggleSelectAll = () => {
  if (selectAll.value) {
    selectedIds.value = products.value.map(p => p.id);
  } else {
    selectedIds.value = [];
  }
};

const batchDelete = async () => {
  if (!confirm(`确定要删除选中的 ${selectedIds.value.length} 个产品吗？`)) return;
  try {
    await productsApi.batchDeleteProducts(selectedIds.value);
    selectedIds.value = [];
    selectAll.value = false;
    loadProducts();
  } catch (e) {
    console.error('批量删除失败:', e);
    alert('批量删除失败: ' + (e.message || '未知错误'));
  }
};

const exportPriceList = async () => {
  try {
    const params = {};
    if (selectedUnit.value) params.unit = selectedUnit.value;
    const response = await productsApi.exportUnitProductsXlsx(params);
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = '产品价格表.xlsx';
    a.click();
    URL.revokeObjectURL(url);
  } catch (e) {
    console.error('导出失败:', e);
    alert('导出失败: ' + (e.message || '未知错误'));
  }
};

onMounted(() => {
  loadProducts();
});
</script>
