<template>
  <div class="page-view" id="view-purchase">
    <div class="page-content">
      <div class="page-header">
        <h2>采购管理</h2>
        <div>
          <button class="btn btn-primary" @click="showOrderModal">新建采购订单</button>
        </div>
      </div>

      <div class="search-box">
        <select v-model="filterStatus" style="min-width:120px;" @change="loadOrders">
          <option value="">全部状态</option>
          <option value="draft">草稿</option>
          <option value="approved">已审核</option>
          <option value="partial">部分入库</option>
          <option value="completed">已完成</option>
          <option value="cancelled">已取消</option>
        </select>
        <select v-model="selectedSupplier" style="min-width:180px;" @change="loadOrders">
          <option value="">全部供应商</option>
          <option v-for="s in suppliers" :key="s.id" :value="s.id">{{ s.name }}</option>
        </select>
      </div>

      <div class="tabs">
        <button :class="{active: activeTab === 'orders'}" @click="activeTab = 'orders'">采购订单</button>
        <button :class="{active: activeTab === 'inbounds'}" @click="activeTab = 'inbounds'">采购入库</button>
        <button :class="{active: activeTab === 'suppliers'}" @click="activeTab = 'suppliers'">供应商</button>
      </div>

      <div v-if="activeTab === 'orders'" class="card">
        <div class="table-responsive">
          <table class="data-table">
            <thead>
              <tr>
                <th>订单号</th>
                <th>供应商</th>
                <th>订单日期</th>
                <th>交货日期</th>
                <th>总金额</th>
                <th>状态</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="order in orders" :key="order.id">
                <td>{{ order.order_no }}</td>
                <td>{{ order.supplier_name }}</td>
                <td>{{ order.order_date }}</td>
                <td>{{ order.delivery_date || '-' }}</td>
                <td>¥{{ order.total_amount?.toFixed(2) || '0.00' }}</td>
                <td>
                  <span :class="'status-' + order.status">{{ getStatusText(order.status) }}</span>
                </td>
                <td>
                  <button class="btn btn-sm btn-secondary" @click="viewOrder(order)">查看</button>
                  <button v-if="order.status === 'draft'" class="btn btn-sm btn-primary" @click="editOrder(order)">编辑</button>
                  <button v-if="order.status === 'draft'" class="btn btn-sm btn-success" @click="approveOrder(order)">审核</button>
                </td>
              </tr>
              <tr v-if="orders.length === 0">
                <td colspan="7" class="text-center">暂无订单数据</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div v-if="activeTab === 'inbounds'" class="card">
        <div class="table-responsive">
          <table class="data-table">
            <thead>
              <tr>
                <th>入库单号</th>
                <th>供应商</th>
                <th>入库日期</th>
                <th>总金额</th>
                <th>状态</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="inbound in inbounds" :key="inbound.id">
                <td>{{ inbound.inbound_no }}</td>
                <td>{{ inbound.supplier_name }}</td>
                <td>{{ inbound.inbound_date }}</td>
                <td>¥{{ inbound.total_amount?.toFixed(2) || '0.00' }}</td>
                <td>{{ inbound.status }}</td>
              </tr>
              <tr v-if="inbounds.length === 0">
                <td colspan="5" class="text-center">暂无入库记录</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div v-if="activeTab === 'suppliers'" class="card">
        <div class="page-header" style="padding:0;border:none;">
          <h4>供应商列表</h4>
          <button class="btn btn-primary btn-sm" @click="showSupplierModal">添加供应商</button>
        </div>
        <div class="table-responsive">
          <table class="data-table">
            <thead>
              <tr>
                <th>编码</th>
                <th>名称</th>
                <th>联系人</th>
                <th>电话</th>
                <th>评级</th>
                <th>状态</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="s in suppliers" :key="s.id">
                <td>{{ s.code }}</td>
                <td>{{ s.name }}</td>
                <td>{{ s.contact_person || '-' }}</td>
                <td>{{ s.contact_phone || '-' }}</td>
                <td>{{ '★'.repeat(s.rating || 3) }}</td>
                <td>{{ s.status === 'active' ? '正常' : '已删除' }}</td>
                <td>
                  <button class="btn btn-sm btn-secondary" @click="editSupplier(s)">编辑</button>
                </td>
              </tr>
              <tr v-if="suppliers.length === 0">
                <td colspan="7" class="text-center">暂无供应商数据</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <div v-if="showOrderModalFlag" class="modal active">
      <div class="modal-content" style="max-width:800px;">
        <div class="modal-header">{{ isEditOrder ? '编辑采购订单' : '新建采购订单' }}</div>
        <div class="modal-body">
          <div class="form-row">
            <div class="form-group">
              <label>供应商 *</label>
              <select v-model="orderForm.supplier_id">
                <option value="">选择供应商</option>
                <option v-for="s in suppliers" :key="s.id" :value="s.id">{{ s.name }}</option>
              </select>
            </div>
            <div class="form-group">
              <label>订单日期</label>
              <input v-model="orderForm.order_date" type="date">
            </div>
            <div class="form-group">
              <label>交货日期</label>
              <input v-model="orderForm.delivery_date" type="date">
            </div>
          </div>
          <div class="form-group">
            <label>订单明细</label>
            <table class="data-table">
              <thead>
                <tr>
                  <th>产品</th>
                  <th>数量</th>
                  <th>单价</th>
                  <th>金额</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(item, idx) in orderForm.items" :key="idx">
                  <td>
                    <select v-model="item.product_id" @change="selectProduct(idx)">
                      <option value="">选择产品</option>
                      <option v-for="p in products" :key="p.id" :value="p.id">{{ p.name }}</option>
                    </select>
                  </td>
                  <td><input v-model.number="item.quantity" type="number" min="1" @input="calcItemAmount(idx)"></td>
                  <td><input v-model.number="item.unit_price" type="number" step="0.01" @input="calcItemAmount(idx)"></td>
                  <td>{{ item.amount?.toFixed(2) || '0.00' }}</td>
                  <td><button class="btn btn-sm btn-danger" @click="removeOrderItem(idx)">删除</button></td>
                </tr>
              </tbody>
            </table>
            <button class="btn btn-sm btn-secondary" @click="addOrderItem">+ 添加产品</button>
          </div>
          <div class="form-group">
            <label>备注</label>
            <input v-model="orderForm.remark" type="text">
          </div>
          <div class="form-total">
            总金额: ¥{{ orderForm.total_amount?.toFixed(2) || '0.00' }}
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn btn-secondary" @click="showOrderModalFlag = false">取消</button>
          <button class="btn btn-primary" @click="saveOrder">保存</button>
        </div>
      </div>
    </div>

    <div v-if="showSupplierModalFlag" class="modal active">
      <div class="modal-content">
        <div class="modal-header">{{ isEditSupplier ? '编辑供应商' : '添加供应商' }}</div>
        <div class="modal-body">
          <div class="form-group">
            <label>编码 *</label>
            <input v-model="supplierForm.code" type="text" placeholder="供应商编码">
          </div>
          <div class="form-group">
            <label>名称 *</label>
            <input v-model="supplierForm.name" type="text" placeholder="供应商名称">
          </div>
          <div class="form-group">
            <label>联系人</label>
            <input v-model="supplierForm.contact_person" type="text">
          </div>
          <div class="form-group">
            <label>电话</label>
            <input v-model="supplierForm.contact_phone" type="text">
          </div>
          <div class="form-group">
            <label>邮箱</label>
            <input v-model="supplierForm.contact_email" type="email">
          </div>
          <div class="form-group">
            <label>地址</label>
            <input v-model="supplierForm.address" type="text">
          </div>
          <div class="form-group">
            <label>评级</label>
            <select v-model="supplierForm.rating">
              <option :value="1">★</option>
              <option :value="2">★★</option>
              <option :value="3">★★★</option>
              <option :value="4">★★★★</option>
              <option :value="5">★★★★★</option>
            </select>
          </div>
          <div class="form-group">
            <label>备注</label>
            <input v-model="supplierForm.remark" type="text">
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn btn-secondary" @click="showSupplierModalFlag = false">取消</button>
          <button class="btn btn-primary" @click="saveSupplier">保存</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue'
import { get, post } from '@/api'

export default {
  name: 'PurchaseView',
  setup() {
    const activeTab = ref('orders')
    const orders = ref([])
    const inbounds = ref([])
    const suppliers = ref([])
    const products = ref([])
    const filterStatus = ref('')
    const selectedSupplier = ref('')
    const showOrderModalFlag = ref(false)
    const showSupplierModalFlag = ref(false)
    const isEditOrder = ref(false)
    const isEditSupplier = ref(false)

    const orderForm = ref({
      id: null,
      supplier_id: '',
      order_date: new Date().toISOString().split('T')[0],
      delivery_date: '',
      remark: '',
      items: [],
      total_amount: 0
    })

    const supplierForm = ref({
      id: null,
      code: '',
      name: '',
      contact_person: '',
      contact_phone: '',
      contact_email: '',
      address: '',
      rating: 3,
      remark: ''
    })

    const loadOrders = async () => {
      try {
        const params = {}
        if (filterStatus.value) params.status = filterStatus.value
        if (selectedSupplier.value) params.supplier_id = selectedSupplier.value
        const res = await get('/api/purchase/orders', params)
        if (res.success) {
          orders.value = res.data || []
        }
      } catch (e) {
        console.error('加载订单失败', e)
      }
    }

    const loadInbounds = async () => {
      try {
        const res = await get('/api/purchase/inbounds')
        if (res.success) {
          inbounds.value = res.data || []
        }
      } catch (e) {
        console.error('加载入库记录失败', e)
      }
    }

    const loadSuppliers = async () => {
      try {
        const res = await get('/api/purchase/suppliers')
        if (res.success) {
          suppliers.value = res.data || []
        }
      } catch (e) {
        console.error('加载供应商失败', e)
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

    const getStatusText = (status) => {
      const map = {
        draft: '草稿',
        approved: '已审核',
        partial: '部分入库',
        completed: '已完成',
        cancelled: '已取消'
      }
      return map[status] || status
    }

    const showOrderModal = () => {
      isEditOrder.value = false
      orderForm.value = {
        id: null,
        supplier_id: '',
        order_date: new Date().toISOString().split('T')[0],
        delivery_date: '',
        remark: '',
        items: [],
        total_amount: 0
      }
      showOrderModalFlag.value = true
    }

    const editOrder = (order) => {
      isEditOrder.value = true
      orderForm.value = {
        id: order.id,
        supplier_id: order.supplier_id,
        order_date: order.order_date,
        delivery_date: order.delivery_date || '',
        remark: order.remark || '',
        items: order.items || [],
        total_amount: order.total_amount
      }
      showOrderModalFlag.value = true
    }

    const viewOrder = (order) => {
      isEditOrder.value = true
      orderForm.value = { ...order }
      showOrderModalFlag.value = true
    }

    const addOrderItem = () => {
      orderForm.value.items.push({
        product_id: '',
        quantity: 1,
        unit_price: 0,
        amount: 0
      })
    }

    const removeOrderItem = (idx) => {
      orderForm.value.items.splice(idx, 1)
      calcTotalAmount()
    }

    const selectProduct = (idx) => {
      const product = products.value.find(p => p.id === orderForm.value.items[idx].product_id)
      if (product) {
        orderForm.value.items[idx].unit_price = product.price || 0
        calcItemAmount(idx)
      }
    }

    const calcItemAmount = (idx) => {
      const item = orderForm.value.items[idx]
      item.amount = (item.quantity || 0) * (item.unit_price || 0)
      calcTotalAmount()
    }

    const calcTotalAmount = () => {
      orderForm.value.total_amount = orderForm.value.items.reduce((sum, item) => {
        return sum + (item.amount || 0)
      }, 0)
    }

    const saveOrder = async () => {
      if (!orderForm.value.supplier_id) {
        alert('请选择供应商')
        return
      }
      if (orderForm.value.items.length === 0) {
        alert('请添加订单明细')
        return
      }
      try {
        const res = isEditOrder.value
          ? await post(`/api/purchase/orders/${orderForm.value.id}`, orderForm.value)
          : await post('/api/purchase/orders', orderForm.value)
        if (res.success) {
          alert('保存成功')
          showOrderModalFlag.value = false
          loadOrders()
        } else {
          alert('保存失败: ' + res.message)
        }
      } catch (e) {
        alert('保存失败')
      }
    }

    const approveOrder = async (order) => {
      if (!confirm('确认审核该订单？')) return
      try {
        const res = await post(`/api/purchase/orders/${order.id}/approve`)
        if (res.success) {
          alert('审核成功')
          loadOrders()
        } else {
          alert('审核失败: ' + res.message)
        }
      } catch (e) {
        alert('审核失败')
      }
    }

    const showSupplierModal = () => {
      isEditSupplier.value = false
      supplierForm.value = {
        id: null,
        code: '',
        name: '',
        contact_person: '',
        contact_phone: '',
        contact_email: '',
        address: '',
        rating: 3,
        remark: ''
      }
      showSupplierModalFlag.value = true
    }

    const editSupplier = (supplier) => {
      isEditSupplier.value = true
      supplierForm.value = { ...supplier }
      showSupplierModalFlag.value = true
    }

    const saveSupplier = async () => {
      if (!supplierForm.value.code || !supplierForm.value.name) {
        alert('请填写必填项')
        return
      }
      try {
        const res = isEditSupplier.value
          ? await post(`/api/purchase/suppliers/${supplierForm.value.id}`, supplierForm.value)
          : await post('/api/purchase/suppliers', supplierForm.value)
        if (res.success) {
          alert('保存成功')
          showSupplierModalFlag.value = false
          loadSuppliers()
        } else {
          alert('保存失败: ' + res.message)
        }
      } catch (e) {
        alert('保存失败')
      }
    }

    onMounted(() => {
      loadOrders()
      loadInbounds()
      loadSuppliers()
      loadProducts()
    })

    return {
      activeTab,
      orders,
      inbounds,
      suppliers,
      products,
      filterStatus,
      selectedSupplier,
      showOrderModalFlag,
      showSupplierModalFlag,
      isEditOrder,
      isEditSupplier,
      orderForm,
      supplierForm,
      loadOrders,
      getStatusText,
      showOrderModal,
      editOrder,
      viewOrder,
      addOrderItem,
      removeOrderItem,
      selectProduct,
      calcItemAmount,
      saveOrder,
      approveOrder,
      showSupplierModal,
      editSupplier,
      saveSupplier
    }
  }
}
</script>

<style scoped>
.status-draft { color: #6c757d; }
.status-approved { color: #28a745; }
.status-partial { color: #ffc107; }
.status-completed { color: #007bff; }
.status-cancelled { color: #dc3545; }
.text-center { text-align: center; }
.tabs {
  display: flex;
  gap: 5px;
  margin: 15px 0;
}
.tabs button {
  padding: 8px 20px;
  border: 1px solid #ddd;
  background: #f8f9fa;
  cursor: pointer;
}
.tabs button.active {
  background: #007bff;
  color: white;
  border-color: #007bff;
}
.form-row {
  display: flex;
  gap: 15px;
}
.form-row .form-group {
  flex: 1;
}
.form-total {
  text-align: right;
  font-size: 18px;
  font-weight: bold;
  padding: 10px;
  background: #f8f9fa;
  border-radius: 4px;
}
</style>
