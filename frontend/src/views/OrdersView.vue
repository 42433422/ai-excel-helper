<template>
  <div class="page-view" id="view-orders">
    <div class="page-content">
      <div class="page-header">
        <h2>出货单记录</h2>
        <div style="display: flex; gap: 10px;">
          <button class="btn btn-primary" @click="$router.push('/orders/create')">+ 新建订单</button>
          <button class="btn btn-danger" @click="handleClearAll" :disabled="store.loading">清空全部</button>
        </div>
      </div>
      <div class="search-box">
        <input v-model.trim="searchQuery" type="text" placeholder="搜索客户名/单号..." @input="doSearch">
      </div>
      <div class="card">
        <DataTable
          :columns="columns"
          :data="store.orders"
          :loading="store.loading"
          :selectable="false"
          row-key="id"
          empty-text="暂无出货记录"
        >
          <template #cell-order_number="{ value }">
            {{ value || '-' }}
          </template>
          <template #cell-customer_name="{ row }">
            {{ row.customer_name || row.purchase_unit || '-' }}
          </template>
          <template #cell-date="{ value }">
            {{ value || '-' }}
          </template>
          <template #cell-total_amount="{ value }">
            {{ formatAmount(value) }}
          </template>
          <template #cell-status="{ value }">
            <span class="badge badge-success">{{ value || '已完成' }}</span>
          </template>
          <template #actions="{ row }">
            <button
              class="btn btn-danger btn-sm"
              @click="handleDelete(row.id || row.order_number)"
              :disabled="store.loading || !(row.id || row.order_number)"
            >
              删除
            </button>
          </template>
        </DataTable>
      </div>
    </div>

    <ConfirmDialog
      v-model="showClearConfirm"
      title="清空全部"
      message="确定要清空所有出货记录吗？此操作不可恢复！"
      confirm-text="清空"
      confirm-class="btn-danger"
      @confirm="confirmClearAll"
    />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { useOrdersStore } from '../stores/orders';
import { storeToRefs } from 'pinia';
import DataTable from '../components/DataTable.vue';
import ConfirmDialog from '../components/ConfirmDialog.vue';

const store = useOrdersStore();
const { orders } = storeToRefs(store);

const searchQuery = ref('');
const showClearConfirm = ref(false);

const columns = [
  { key: 'order_number', label: '单号' },
  { key: 'customer_name', label: '客户' },
  { key: 'date', label: '日期' },
  { key: 'total_amount', label: '金额' },
  { key: 'status', label: '状态' }
];

function formatAmount(value) {
  const n = Number(value || 0);
  if (Number.isNaN(n)) return '¥0';
  return `¥${n.toFixed(2)}`;
}

async function loadOrders() {
  await store.fetchOrders({ limit: 200 });
}

async function doSearch() {
  if (!searchQuery.value) {
    await loadOrders();
    return;
  }
  await store.searchOrders(searchQuery.value);
}

async function handleDelete(orderNumber) {
  if (!orderNumber) return;
  if (!confirm(`确定要删除订单 ${orderNumber} 吗？`)) return;
  await store.deleteOrder(orderNumber);
}

function handleClearAll() {
  const key = prompt('请输入密钥确认清空:');
  if (key !== '61408693') {
    alert('密钥错误');
    return;
  }
  showClearConfirm.value = true;
}

async function confirmClearAll() {
  await store.clearAllOrders();
}

onMounted(() => {
  loadOrders();
});
</script>
