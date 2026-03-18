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
      <div v-if="lowStockMaterials.length > 0" class="warning-card">
        <div class="title">⚠️ 库存预警</div>
        <div id="lowStockList">
          <span v-for="(item, idx) in lowStockMaterials" :key="idx">
            {{ item.name }} (库存: {{ item.quantity }}/{{ item.min_stock || 0 }})
          </span>
        </div>
      </div>
      <div class="search-box">
        <input v-model="searchQuery" type="text" placeholder="搜索原材料..." @input="loadMaterials">
        <select v-model="selectedCategory">
          <option value="">全部分类</option>
          <option v-for="cat in categories" :key="cat" :value="cat">{{ cat }}</option>
        </select>
      </div>
      <div class="card">
        <table class="data-table">
          <thead>
            <tr>
              <th><input type="checkbox" v-model="selectAll" @change="toggleSelectAll"></th>
              <th>编码</th>
              <th>名称</th>
              <th>分类</th>
              <th>库存</th>
              <th>单价</th>
              <th>供应商</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading">
              <td colspan="8" class="empty-state">加载中...</td>
            </tr>
            <tr v-else-if="materials.length === 0">
              <td colspan="8" class="empty-state">暂无原材料数据</td>
            </tr>
            <tr v-for="material in materials" :key="material.id">
              <td><input type="checkbox" :value="material.id" v-model="selectedIds"></td>
              <td>{{ material.code || '-' }}</td>
              <td>{{ material.name || '-' }}</td>
              <td>{{ material.category || '-' }}</td>
              <td :class="{ 'text-red': material.quantity < (material.min_stock || 0) }">
                {{ material.quantity }} {{ material.unit || '' }}
              </td>
              <td>{{ material.price ? '¥' + material.price.toFixed(2) : '-' }}</td>
              <td>{{ material.supplier || '-' }}</td>
              <td>
                <button class="btn btn-sm btn-secondary" @click="editMaterial(material)">编辑</button>
                <button class="btn btn-sm btn-danger" @click="deleteMaterial(material)">删除</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

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
import { ref, onMounted, computed } from 'vue';
import materialsApi from '../api/materials';

const materials = ref([]);
const loading = ref(false);
const showModal = ref(false);
const isEdit = ref(false);
const selectedIds = ref([]);
const selectAll = ref(false);
const searchQuery = ref('');
const selectedCategory = ref('');
const lowStockMaterials = ref([]);
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

const categories = computed(() => {
  const cats = new Set(materials.value.map(m => m.category).filter(Boolean));
  return Array.from(cats);
});

const loadMaterials = async () => {
  loading.value = true;
  try {
    const params = {};
    if (searchQuery.value) params.search = searchQuery.value;
    if (selectedCategory.value) params.category = selectedCategory.value;
    const data = await materialsApi.getMaterials(params);
    if (data.success) {
      materials.value = data.data || [];
      checkLowStock();
    }
  } catch (e) {
    console.error('加载原材料失败:', e);
  } finally {
    loading.value = false;
  }
};

const checkLowStock = () => {
  lowStockMaterials.value = materials.value.filter(m => 
    m.quantity !== null && m.min_stock !== null && m.quantity < m.min_stock
  );
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
  try {
    if (isEdit.value && formData.value.id) {
      await materialsApi.updateMaterial(formData.value.id, formData.value);
    } else {
      await materialsApi.createMaterial(formData.value);
    }
    showModal.value = false;
    loadMaterials();
  } catch (e) {
    console.error('保存原材料失败:', e);
    alert('保存失败: ' + (e.message || '未知错误'));
  }
};

const deleteMaterial = async (material) => {
  if (!confirm('确定要删除该原材料吗？')) return;
  try {
    await materialsApi.deleteMaterial(material.id);
    loadMaterials();
  } catch (e) {
    console.error('删除原材料失败:', e);
    alert('删除失败: ' + (e.message || '未知错误'));
  }
};

const toggleSelectAll = () => {
  if (selectAll.value) {
    selectedIds.value = materials.value.map(m => m.id);
  } else {
    selectedIds.value = [];
  }
};

const batchDelete = async () => {
  if (!confirm(`确定要删除选中的 ${selectedIds.value.length} 个原材料吗？`)) return;
  try {
    await materialsApi.batchDeleteMaterials(selectedIds.value);
    selectedIds.value = [];
    selectAll.value = false;
    loadMaterials();
  } catch (e) {
    console.error('批量删除失败:', e);
    alert('批量删除失败: ' + (e.message || '未知错误'));
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
