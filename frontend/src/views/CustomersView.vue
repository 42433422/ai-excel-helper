<template>
  <div class="page-view" id="view-customers">
    <div class="page-content">
      <div class="page-header">
        <h2>客户管理</h2>
        <div class="header-actions">
          <button class="btn btn-icon" @click="triggerImport" title="上传Excel更新购买单位">📥</button>
          <input 
            ref="importFileInput"
            type="file" 
            accept=".xlsx" 
            style="display:none"
            @change="handleImport"
          >
          <button class="btn btn-icon" @click="exportCustomers" title="导出购买单位Excel">
            <svg class="excel-icon-svg" viewBox="0 0 24 24" width="22" height="22">
              <rect width="24" height="24" rx="3" fill="#217346"/>
              <path stroke="#fff" stroke-width="2.2" stroke-linecap="round" fill="none" d="M7 7l10 10M17 7L7 17"/>
            </svg>
          </button>
          <button v-if="selectedIds.length > 0" class="btn btn-danger" @click="batchDelete">批量删除 ({{ selectedIds.length }})</button>
        </div>
      </div>
      <div class="stat-cards">
        <div class="stat-card">
          <div class="number">{{ customers.length }}</div>
          <div class="label">客户总数</div>
        </div>
      </div>
      <div class="card">
        <table class="data-table">
          <thead>
            <tr>
              <th><input type="checkbox" v-model="selectAll" @change="toggleSelectAll"></th>
              <th>客户名称</th>
              <th>联系人</th>
              <th>电话</th>
              <th>地址</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading">
              <td colspan="5" class="empty-state">加载中...</td>
            </tr>
            <tr v-else-if="customers.length === 0">
              <td colspan="5" class="empty-state">暂无客户数据</td>
            </tr>
            <tr v-for="customer in customers" :key="customer.id">
              <td><input type="checkbox" :value="customer.id" v-model="selectedIds"></td>
              <td>{{ customer.unit_name || customer.name || '-' }}</td>
              <td>{{ customer.contact_person || '-' }}</td>
              <td>{{ customer.contact_phone || '-' }}</td>
              <td>{{ customer.address || '-' }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import customersApi from '../api/customers';

const customers = ref([]);
const loading = ref(false);
const selectedIds = ref([]);
const selectAll = ref(false);
const importFileInput = ref(null);

const loadCustomers = async () => {
  loading.value = true;
  try {
    const data = await customersApi.getCustomers();
    if (data.success) {
      customers.value = data.customers || data.data || [];
    }
  } catch (e) {
    console.error('加载客户失败:', e);
  } finally {
    loading.value = false;
  }
};

const toggleSelectAll = () => {
  if (selectAll.value) {
    selectedIds.value = customers.value.map(c => c.id);
  } else {
    selectedIds.value = [];
  }
};

const batchDelete = async () => {
  if (!confirm(`确定要删除选中的 ${selectedIds.value.length} 个客户吗？`)) return;
  try {
    await customersApi.batchDeleteCustomers(selectedIds.value);
    selectedIds.value = [];
    selectAll.value = false;
    loadCustomers();
  } catch (e) {
    console.error('批量删除失败:', e);
    alert('批量删除失败: ' + (e.message || '未知错误'));
  }
};

const exportCustomers = async () => {
  try {
    const response = await customersApi.exportCustomersXlsx();
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = '购买单位列表.xlsx';
    a.click();
    URL.revokeObjectURL(url);
  } catch (e) {
    console.error('导出失败:', e);
    alert('导出失败: ' + (e.message || '未知错误'));
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
      alert('导入成功！');
      loadCustomers();
    }
  } catch (e) {
    console.error('导入失败:', e);
    alert('导入失败: ' + (e.message || '未知错误'));
  } finally {
    e.target.value = '';
  }
};

onMounted(() => {
  loadCustomers();
});
</script>
