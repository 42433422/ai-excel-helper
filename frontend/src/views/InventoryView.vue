<template>
  <div class="page-view" id="view-inventory">
    <div class="page-content">
      <div class="page-header">
        <h2>库存管理</h2>
        <div>
          <button class="btn btn-secondary" @click="exportInventory" style="margin-right:10px;">导出</button>
          <button class="btn btn-primary" @click="showInModal">入库</button>
          <button class="btn btn-warning" @click="showOutModal" style="margin-left:10px;">出库</button>
        </div>
      </div>

      <div class="search-box">
        <select v-model="selectedWarehouse" style="min-width:180px;" @change="loadInventory">
          <option value="">全部仓库</option>
          <option v-for="w in warehouses" :key="w.id" :value="w.id">{{ w.name }}</option>
        </select>
        <input v-model="searchQuery" type="text" placeholder="搜索产品名称或型号..." @input="loadInventory">
      </div>

      <div class="card">
        <div class="table-responsive">
          <table class="data-table">
            <thead>
              <tr>
                <th>产品名称</th>
                <th>型号</th>
                <th>仓库</th>
                <th>批次</th>
                <th>库存数量</th>
                <th>可用数量</th>
                <th>单位</th>
                <th>入库日期</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in inventoryList" :key="item.id">
                <td>{{ item.product_name || '-' }}</td>
                <td>{{ item.product_code || '-' }}</td>
                <td>{{ item.warehouse_name || '-' }}</td>
                <td>{{ item.batch_no || '-' }}</td>
                <td>{{ item.quantity }}</td>
                <td :class="{'text-danger': item.available_quantity <= 0}">{{ item.available_quantity }}</td>
                <td>{{ item.unit || '个' }}</td>
                <td>{{ item.in_date || '-' }}</td>
              </tr>
              <tr v-if="inventoryList.length === 0">
                <td colspan="8" class="text-center">暂无库存数据</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div class="pagination" v-if="total > pageSize">
          <button @click="prevPage" :disabled="page <= 1">上一页</button>
          <span>{{ page }} / {{ totalPages }}</span>
          <button @click="nextPage" :disabled="page >= totalPages">下一页</button>
        </div>
      </div>

      <div class="card" style="margin-top:20px;">
        <h4>库存预警</h4>
        <div class="table-responsive">
          <table class="data-table">
            <thead>
              <tr>
                <th>产品名称</th>
                <th>型号</th>
                <th>仓库</th>
                <th>当前库存</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in lowStockList" :key="item.id" class="text-danger">
                <td>{{ item.product_name || '-' }}</td>
                <td>{{ item.product_code || '-' }}</td>
                <td>{{ item.warehouse_name || '-' }}</td>
                <td>{{ item.available_quantity }}</td>
              </tr>
              <tr v-if="lowStockList.length === 0">
                <td colspan="4" class="text-center">暂无预警信息</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <div v-if="showInDialog" class="modal active">
      <div class="modal-content">
        <div class="modal-header">入库</div>
        <div class="modal-body">
          <div class="form-group">
            <label>产品 *</label>
            <select v-model="inForm.product_id">
              <option value="">选择产品</option>
              <option v-for="p in products" :key="p.id" :value="p.id">{{ p.name }} - {{ p.model_number }}</option>
            </select>
          </div>
          <div class="form-group">
            <label>仓库 *</label>
            <select v-model="inForm.warehouse_id">
              <option value="">选择仓库</option>
              <option v-for="w in warehouses" :key="w.id" :value="w.id">{{ w.name }}</option>
            </select>
          </div>
          <div class="form-group">
            <label>数量 *</label>
            <input v-model.number="inForm.quantity" type="number" min="1" placeholder="入库数量">
          </div>
          <div class="form-group">
            <label>批次号</label>
            <input v-model="inForm.batch_no" type="text" placeholder="批次号（可选）">
          </div>
          <div class="form-group">
            <label>单价</label>
            <input v-model.number="inForm.unit_price" type="number" step="0.01" placeholder="单价（可选）">
          </div>
          <div class="form-group">
            <label>备注</label>
            <input v-model="inForm.remark" type="text" placeholder="备注">
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn btn-secondary" @click="showInDialog = false">取消</button>
          <button class="btn btn-primary" @click="doInventoryIn">确认入库</button>
        </div>
      </div>
    </div>

    <div v-if="showOutDialog" class="modal active">
      <div class="modal-content">
        <div class="modal-header">出库</div>
        <div class="modal-body">
          <div class="form-group">
            <label>产品 *</label>
            <select v-model="outForm.product_id">
              <option value="">选择产品</option>
              <option v-for="p in products" :key="p.id" :value="p.id">{{ p.name }} - {{ p.model_number }}</option>
            </select>
          </div>
          <div class="form-group">
            <label>仓库 *</label>
            <select v-model="outForm.warehouse_id">
              <option value="">选择仓库</option>
              <option v-for="w in warehouses" :key="w.id" :value="w.id">{{ w.name }}</option>
            </select>
          </div>
          <div class="form-group">
            <label>数量 *</label>
            <input v-model.number="outForm.quantity" type="number" min="1" placeholder="出库数量">
          </div>
          <div class="form-group">
            <label>备注</label>
            <input v-model="outForm.remark" type="text" placeholder="备注">
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn btn-secondary" @click="showOutDialog = false">取消</button>
          <button class="btn btn-primary" @click="doInventoryOut">确认出库</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted, computed } from 'vue'
import { get, post } from '@/api'

export default {
  name: 'InventoryView',
  setup() {
    const inventoryList = ref([])
    const warehouses = ref([])
    const products = ref([])
    const lowStockList = ref([])
    const loading = ref(false)
    const selectedWarehouse = ref('')
    const searchQuery = ref('')
    const page = ref(1)
    const pageSize = 50
    const total = ref(0)
    const showInDialog = ref(false)
    const showOutDialog = ref(false)

    const inForm = ref({
      product_id: '',
      warehouse_id: '',
      quantity: 1,
      batch_no: '',
      unit_price: null,
      remark: ''
    })

    const outForm = ref({
      product_id: '',
      warehouse_id: '',
      quantity: 1,
      remark: ''
    })

    const totalPages = computed(() => Math.ceil(total.value / pageSize))

    const loadWarehouses = async () => {
      try {
        const res = await get('/api/inventory/warehouses')
        if (res.success) {
          warehouses.value = res.data || []
        }
      } catch (e) {
        console.error('加载仓库失败', e)
      }
    }

    const loadProducts = async () => {
      try {
        const res = await get('/api/products')
        if (res.success) {
          products.value = res.data || []
        }
      } catch (e) {
        console.error('加载产品失败', e)
      }
    }

    const loadInventory = async () => {
      loading.value = true
      try {
        const params = {
          page: page.value,
          per_page: pageSize
        }
        if (selectedWarehouse.value) {
          params.warehouse_id = selectedWarehouse.value
        }
        if (searchQuery.value) {
          params.keyword = searchQuery.value
        }
        const res = await get('/api/inventory/inventory', params)
        if (res.success) {
          inventoryList.value = res.data || []
          total.value = res.total || 0
        }
      } catch (e) {
        console.error('加载库存失败', e)
      } finally {
        loading.value = false
      }
    }

    const loadLowStock = async () => {
      try {
        const res = await get('/api/inventory/alert')
        if (res.success) {
          lowStockList.value = res.data || []
        }
      } catch (e) {
        console.error('加载预警失败', e)
      }
    }

    const showInModal = () => {
      inForm.value = {
        product_id: '',
        warehouse_id: selectedWarehouse.value || '',
        quantity: 1,
        batch_no: '',
        unit_price: null,
        remark: ''
      }
      showInDialog.value = true
    }

    const showOutModal = () => {
      outForm.value = {
        product_id: '',
        warehouse_id: selectedWarehouse.value || '',
        quantity: 1,
        remark: ''
      }
      showOutDialog.value = true
    }

    const doInventoryIn = async () => {
      if (!inForm.value.product_id || !inForm.value.warehouse_id || !inForm.value.quantity) {
        alert('请填写必填项')
        return
      }
      try {
        const res = await post('/api/inventory/in', inForm.value)
        if (res.success) {
          alert('入库成功')
          showInDialog.value = false
          loadInventory()
          loadLowStock()
        } else {
          alert('入库失败: ' + res.message)
        }
      } catch (e) {
        alert('入库失败')
      }
    }

    const doInventoryOut = async () => {
      if (!outForm.value.product_id || !outForm.value.warehouse_id || !outForm.value.quantity) {
        alert('请填写必填项')
        return
      }
      try {
        const res = await post('/api/inventory/out', outForm.value)
        if (res.success) {
          alert('出库成功')
          showOutDialog.value = false
          loadInventory()
          loadLowStock()
        } else {
          alert('出库失败: ' + res.message)
        }
      } catch (e) {
        alert('出库失败')
      }
    }

    const exportInventory = async () => {
      alert('导出功能开发中')
    }

    const prevPage = () => {
      if (page.value > 1) {
        page.value--
        loadInventory()
      }
    }

    const nextPage = () => {
      if (page.value < totalPages.value) {
        page.value++
        loadInventory()
      }
    }

    onMounted(() => {
      loadWarehouses()
      loadProducts()
      loadInventory()
      loadLowStock()
    })

    return {
      inventoryList,
      warehouses,
      products,
      lowStockList,
      loading,
      selectedWarehouse,
      searchQuery,
      page,
      pageSize,
      total,
      showInDialog,
      showOutDialog,
      inForm,
      outForm,
      totalPages,
      loadInventory,
      showInModal,
      showOutModal,
      doInventoryIn,
      doInventoryOut,
      exportInventory,
      prevPage,
      nextPage
    }
  }
}
</script>

<style scoped>
.text-danger {
  color: #dc3545;
}
.text-center {
  text-align: center;
}
.table-responsive {
  overflow-x: auto;
}
.pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 10px;
  margin-top: 15px;
}
</style>
