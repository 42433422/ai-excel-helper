<template>
  <div class="page-view" id="view-materials">
    <div class="page-content">
      <div class="page-header">
        <h2>{{ industryStore.currentIndustryId === '涂料' ? '原材料仓库' : industryStore.currentIndustryId === '电商' ? '商品仓库' : '仓库管理' }}</h2>
        <div>
          <button class="btn btn-secondary" @click="exportData" style="margin-right:10px;">导出</button>
          <button class="btn btn-primary" @click="showAddModal">+ 添加</button>
        </div>
      </div>

      <div class="tabs">
        <button :class="{active: activeTab === 'materials'}" @click="activeTab = 'materials'">原材料</button>
        <button :class="{active: activeTab === 'warehouse'}" @click="activeTab = 'warehouse'">仓库库位</button>
        <button :class="{active: activeTab === 'inout'}" @click="activeTab = 'inout'">出入库</button>
        <button :class="{active: activeTab === 'supplier'}" @click="activeTab = 'supplier'; loadSuppliers()">供应商</button>
      </div>

      <div v-if="activeTab === 'materials'" class="card">
        <div class="search-box">
          <input v-model="searchQuery" type="text" placeholder="搜索..." @input="loadMaterials">
          <select v-model="selectedCategory">
            <option value="">全部分类</option>
            <option v-for="cat in categories" :key="cat" :value="cat">{{ cat }}</option>
          </select>
        </div>
        <table class="data-table">
          <thead>
            <tr>
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
            <tr v-for="item in materials" :key="item.id">
              <td>{{ item.code || '-' }}</td>
              <td>{{ item.name }}</td>
              <td>{{ item.category || '-' }}</td>
              <td :class="{'text-red': item.quantity < (item.min_stock || 0)}">{{ item.quantity }} {{ item.unit || '' }}</td>
              <td>{{ item.price ? '¥' + item.price.toFixed(2) : '-' }}</td>
              <td>{{ item.supplier || '-' }}</td>
              <td>
                <button class="btn btn-sm btn-secondary" @click="editMaterial(item)">编辑</button>
                <button class="btn btn-sm btn-danger" @click="deleteMaterial(item)">删除</button>
              </td>
            </tr>
            <tr v-if="materials.length === 0">
              <td colspan="7" class="text-center">暂无数据</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-if="activeTab === 'warehouse'" class="card">
        <div class="page-header" style="padding:0;border:none;">
          <h4>仓库列表</h4>
          <button class="btn btn-primary btn-sm" @click="showWarehouseModal">+ 添加仓库</button>
        </div>
        <table class="data-table">
          <thead>
            <tr>
              <th>编码</th>
              <th>名称</th>
              <th>类型</th>
              <th>地址</th>
              <th>状态</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="w in warehouses" :key="w.id">
              <td>{{ w.code }}</td>
              <td>{{ w.name }}</td>
              <td>{{ w.type || '-' }}</td>
              <td>{{ w.address || '-' }}</td>
              <td>{{ w.status === 'active' ? '正常' : '禁用' }}</td>
              <td>
                <button class="btn btn-sm btn-secondary" @click="editWarehouse(w)">编辑</button>
                <button class="btn btn-sm btn-secondary" @click="manageLocations(w)">库位</button>
              </td>
            </tr>
            <tr v-if="warehouses.length === 0">
              <td colspan="6" class="text-center">暂无仓库</td>
            </tr>
          </tbody>
        </table>

        <div v-if="selectedWarehouse" style="margin-top:30px;">
          <h4>库位管理 - {{ selectedWarehouse.name }}</h4>
          <button class="btn btn-sm btn-primary" @click="showLocationModal" style="margin-bottom:10px;">+ 添加库位</button>
          <table class="data-table">
            <thead>
              <tr>
                <th>编码</th>
                <th>名称</th>
                <th>容量</th>
                <th>当前用量</th>
                <th>状态</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="loc in locations" :key="loc.id">
                <td>{{ loc.code }}</td>
                <td>{{ loc.name }}</td>
                <td>{{ loc.max_capacity || '-' }}</td>
                <td>{{ loc.current_capacity || 0 }}</td>
                <td>{{ loc.status === 'active' ? '正常' : '禁用' }}</td>
                <td>
                  <button class="btn btn-sm btn-secondary" @click="editLocation(loc)">编辑</button>
                </td>
              </tr>
              <tr v-if="locations.length === 0">
                <td colspan="6" class="text-center">暂无库位</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div v-if="activeTab === 'inout'" class="card">
        <div class="page-header" style="padding:0;border:none;">
          <h4>出入库记录</h4>
          <div>
            <button class="btn btn-sm btn-primary" @click="showInModal">入库</button>
            <button class="btn btn-sm btn-warning" @click="showOutModal" style="margin-left:5px;">出库</button>
          </div>
        </div>
        <table class="data-table">
          <thead>
            <tr>
              <th>时间</th>
              <th>类型</th>
              <th>产品</th>
              <th>仓库</th>
              <th>数量</th>
              <th>操作人</th>
              <th>备注</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="t in transactions" :key="t.id">
              <td>{{ t.transaction_date }}</td>
              <td>
                <span :class="t.transaction_type === 'in' ? 'text-green' : 'text-red'">
                  {{ t.transaction_type === 'in' ? '入库' : '出库' }}
                </span>
              </td>
              <td>{{ t.product_name || '-' }}</td>
              <td>{{ t.warehouse_name || '-' }}</td>
              <td>{{ t.quantity }}</td>
              <td>{{ t.operator || '-' }}</td>
              <td>{{ t.remark || '-' }}</td>
            </tr>
            <tr v-if="transactions.length === 0">
              <td colspan="7" class="text-center">暂无记录</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-if="activeTab === 'supplier'" class="card">
        <div class="page-header" style="padding:0;border:none;">
          <h4>供应商列表</h4>
          <button class="btn btn-primary btn-sm" @click="showSupplierModal">+ 添加供应商</button>
        </div>
        <table class="data-table">
          <thead>
            <tr>
              <th>编码</th>
              <th>名称</th>
              <th>联系人</th>
              <th>电话</th>
              <th>评级</th>
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
              <td>
                <button class="btn btn-sm btn-secondary" @click="editSupplier(s)">编辑</button>
              </td>
            </tr>
            <tr v-if="suppliers.length === 0">
              <td colspan="6" class="text-center">暂无供应商</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div v-if="showMaterialModal" class="modal active">
      <div class="modal-content">
        <div class="modal-header">{{ isEditMaterial ? '编辑' : '添加' }}原材料</div>
        <div class="modal-body">
          <div class="form-group"><label>编码</label><input v-model="materialForm.code" type="text"></div>
          <div class="form-group"><label>名称 *</label><input v-model="materialForm.name" type="text"></div>
          <div class="form-group"><label>分类</label><input v-model="materialForm.category" type="text"></div>
          <div class="form-group"><label>规格</label><input v-model="materialForm.spec" type="text"></div>
          <div class="form-group"><label>单位</label><input v-model="materialForm.unit" type="text"></div>
          <div class="form-group"><label>库存</label><input v-model.number="materialForm.quantity" type="number"></div>
          <div class="form-group"><label>单价</label><input v-model.number="materialForm.price" type="number" step="0.01"></div>
          <div class="form-group"><label>供应商</label><input v-model="materialForm.supplier" type="text"></div>
        </div>
        <div class="modal-footer">
          <button class="btn btn-secondary" @click="showMaterialModal = false">取消</button>
          <button class="btn btn-primary" @click="saveMaterial">保存</button>
        </div>
      </div>
    </div>

    <div v-if="showWarehouseModalFlag" class="modal active">
      <div class="modal-content">
        <div class="modal-header">{{ isEditWarehouse ? '编辑' : '添加' }}仓库</div>
        <div class="modal-body">
          <div class="form-group"><label>编码 *</label><input v-model="warehouseForm.code" type="text"></div>
          <div class="form-group"><label>名称 *</label><input v-model="warehouseForm.name" type="text"></div>
          <div class="form-group"><label>类型</label>
            <select v-model="warehouseForm.type">
              <option value="">请选择</option>
              <option value="原材料">原材料仓</option>
              <option value="成品">成品仓</option>
              <option value="半成品">半成品仓</option>
              <option value="其他">其他</option>
            </select>
          </div>
          <div class="form-group"><label>地址</label><input v-model="warehouseForm.address" type="text"></div>
          <div class="form-group"><label>负责人</label><input v-model="warehouseForm.manager" type="text"></div>
        </div>
        <div class="modal-footer">
          <button class="btn btn-secondary" @click="showWarehouseModalFlag = false">取消</button>
          <button class="btn btn-primary" @click="saveWarehouse">保存</button>
        </div>
      </div>
    </div>

    <div v-if="showLocationModalFlag" class="modal active">
      <div class="modal-content">
        <div class="modal-header">{{ isEditLocation ? '编辑' : '添加' }}库位</div>
        <div class="modal-body">
          <div class="form-group"><label>编码 *</label><input v-model="locationForm.code" type="text"></div>
          <div class="form-group"><label>名称</label><input v-model="locationForm.name" type="text"></div>
          <div class="form-group"><label>最大容量</label><input v-model.number="locationForm.max_capacity" type="number"></div>
        </div>
        <div class="modal-footer">
          <button class="btn btn-secondary" @click="showLocationModalFlag = false">取消</button>
          <button class="btn btn-primary" @click="saveLocation">保存</button>
        </div>
      </div>
    </div>

    <div v-if="showInModalFlag" class="modal active">
      <div class="modal-content">
        <div class="modal-header">入库</div>
        <div class="modal-body">
          <div class="form-group"><label>产品 *</label>
            <select v-model="inoutForm.product_id">
              <option value="">选择产品</option>
              <option v-for="m in materials" :key="m.id" :value="m.id">{{ m.name }}</option>
            </select>
          </div>
          <div class="form-group"><label>仓库 *</label>
            <select v-model="inoutForm.warehouse_id">
              <option value="">选择仓库</option>
              <option v-for="w in warehouses" :key="w.id" :value="w.id">{{ w.name }}</option>
            </select>
          </div>
          <div class="form-group"><label>数量 *</label><input v-model.number="inoutForm.quantity" type="number" min="1"></div>
          <div class="form-group"><label>批次</label><input v-model="inoutForm.batch_no" type="text"></div>
          <div class="form-group"><label>备注</label><input v-model="inoutForm.remark" type="text"></div>
        </div>
        <div class="modal-footer">
          <button class="btn btn-secondary" @click="showInModalFlag = false">取消</button>
          <button class="btn btn-primary" @click="doIn">确认入库</button>
        </div>
      </div>
    </div>

    <div v-if="showOutModalFlag" class="modal active">
      <div class="modal-content">
        <div class="modal-header">出库</div>
        <div class="modal-body">
          <div class="form-group"><label>产品 *</label>
            <select v-model="inoutForm.product_id">
              <option value="">选择产品</option>
              <option v-for="m in materials" :key="m.id" :value="m.id">{{ m.name }}</option>
            </select>
          </div>
          <div class="form-group"><label>仓库 *</label>
            <select v-model="inoutForm.warehouse_id">
              <option value="">选择仓库</option>
              <option v-for="w in warehouses" :key="w.id" :value="w.id">{{ w.name }}</option>
            </select>
          </div>
          <div class="form-group"><label>数量 *</label><input v-model.number="inoutForm.quantity" type="number" min="1"></div>
          <div class="form-group"><label>备注</label><input v-model="inoutForm.remark" type="text"></div>
        </div>
        <div class="modal-footer">
          <button class="btn btn-secondary" @click="showOutModalFlag = false">取消</button>
          <button class="btn btn-primary" @click="doOut">确认出库</button>
        </div>
      </div>
    </div>

    <div v-if="showSupplierModalFlag" class="modal active">
      <div class="modal-content">
        <div class="modal-header">{{ isEditSupplier ? '编辑' : '添加' }}供应商</div>
        <div class="modal-body">
          <div class="form-group"><label>编码 *</label><input v-model="supplierForm.code" type="text"></div>
          <div class="form-group"><label>名称 *</label><input v-model="supplierForm.name" type="text"></div>
          <div class="form-group"><label>联系人</label><input v-model="supplierForm.contact_person" type="text"></div>
          <div class="form-group"><label>电话</label><input v-model="supplierForm.contact_phone" type="text"></div>
          <div class="form-group"><label>评级</label>
            <select v-model="supplierForm.rating">
              <option :value="1">★</option>
              <option :value="2">★★</option>
              <option :value="3">★★★</option>
              <option :value="4">★★★★</option>
              <option :value="5">★★★★★</option>
            </select>
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

<script setup>
import { ref, onMounted } from 'vue'
import { useIndustryStore } from '@/stores/industry'
import { get, post } from '@/api'

const industryStore = useIndustryStore()

const activeTab = ref('materials')
const materials = ref([])
const warehouses = ref([])
const locations = ref([])
const transactions = ref([])
const suppliers = ref([])
const categories = ref([])
const searchQuery = ref('')
const selectedCategory = ref('')

const showMaterialModal = ref(false)
const isEditMaterial = ref(false)
const materialForm = ref({ id: null, code: '', name: '', category: '', spec: '', unit: '个', quantity: 0, price: 0, supplier: '', min_stock: 0 })

const showWarehouseModalFlag = ref(false)
const isEditWarehouse = ref(false)
const warehouseForm = ref({ id: null, code: '', name: '', type: '', address: '', manager: '' })
const selectedWarehouse = ref(null)

const showLocationModalFlag = ref(false)
const isEditLocation = ref(false)
const locationForm = ref({ id: null, warehouse_id: null, code: '', name: '', max_capacity: null })

const showInModalFlag = ref(false)
const showOutModalFlag = ref(false)
const inoutForm = ref({ product_id: '', warehouse_id: '', quantity: 1, batch_no: '', remark: '' })

const showSupplierModalFlag = ref(false)
const isEditSupplier = ref(false)
const supplierForm = ref({ id: null, code: '', name: '', contact_person: '', contact_phone: '', rating: 3 })

const loadMaterials = async () => {
  try {
    const params = {}
    if (searchQuery.value) params.search = searchQuery.value
    if (selectedCategory.value) params.category = selectedCategory.value
    const res = await get('/api/materials', params)
    if (res.success) {
      materials.value = res.data || []
      if (res.categories) categories.value = res.categories
    }
  } catch (e) { console.error(e) }
}

const loadWarehouses = async () => {
  try {
    const res = await get('/api/inventory/warehouses')
    if (res.success) warehouses.value = res.data || []
  } catch (e) { console.error(e) }
}

const loadLocations = async (warehouseId) => {
  try {
    const res = await get('/api/inventory/locations', { warehouse_id: warehouseId })
    if (res.success) locations.value = res.data || []
  } catch (e) { console.error(e) }
}

const loadTransactions = async () => {
  try {
    const res = await get('/api/inventory/transactions', { per_page: 100 })
    if (res.success) transactions.value = res.data || []
  } catch (e) { console.error(e) }
}

const loadSuppliers = async () => {
  try {
    const res = await get('/api/purchase/suppliers')
    if (res.success) suppliers.value = res.data || []
  } catch (e) { console.error(e) }
}

const showAddModal = () => {
  isEditMaterial.value = false
  materialForm.value = { id: null, code: '', name: '', category: '', spec: '', unit: '个', quantity: 0, price: 0, supplier: '', min_stock: 0 }
  showMaterialModal.value = true
}

const editMaterial = (item) => {
  isEditMaterial.value = true
  materialForm.value = { ...item }
  showMaterialModal.value = true
}

const saveMaterial = async () => {
  if (!materialForm.value.name) { alert('请输入名称'); return }
  try {
    const res = isEditMaterial.value
      ? await post(`/api/materials/${materialForm.value.id}`, materialForm.value)
      : await post('/api/materials', materialForm.value)
    if (res.success) { showMaterialModal.value = false; loadMaterials() }
    else alert(res.message || '保存失败')
  } catch (e) { alert('保存失败') }
}

const deleteMaterial = async (item) => {
  if (!confirm('确认删除？')) return
  try {
    const res = await post(`/api/materials/${item.id}/delete`, {})
    if (res.success) loadMaterials()
    else alert(res.message || '删除失败')
  } catch (e) { alert('删除失败') }
}

const showWarehouseModal = () => {
  isEditWarehouse.value = false
  warehouseForm.value = { id: null, code: '', name: '', type: '', address: '', manager: '' }
  showWarehouseModalFlag.value = true
}

const editWarehouse = (w) => {
  isEditWarehouse.value = true
  warehouseForm.value = { ...w }
  showWarehouseModalFlag.value = true
}

const saveWarehouse = async () => {
  if (!warehouseForm.value.code || !warehouseForm.value.name) { alert('请填写必填项'); return }
  try {
    const res = isEditWarehouse.value
      ? await post(`/api/inventory/warehouses/${warehouseForm.value.id}`, warehouseForm.value)
      : await post('/api/inventory/warehouses', warehouseForm.value)
    if (res.success) { showWarehouseModalFlag.value = false; loadWarehouses() }
    else alert(res.message || '保存失败')
  } catch (e) { alert('保存失败') }
}

const manageLocations = (w) => {
  selectedWarehouse.value = w
  loadLocations(w.id)
}

const showLocationModal = () => {
  isEditLocation.value = false
  locationForm.value = { id: null, warehouse_id: selectedWarehouse.value?.id, code: '', name: '', max_capacity: null }
  showLocationModalFlag.value = true
}

const editLocation = (loc) => {
  isEditLocation.value = true
  locationForm.value = { ...loc }
  showLocationModalFlag.value = true
}

const saveLocation = async () => {
  if (!locationForm.value.code) { alert('请输入编码'); return }
  try {
    const res = isEditLocation.value
      ? await post(`/api/inventory/locations/${locationForm.value.id}`, locationForm.value)
      : await post('/api/inventory/locations', locationForm.value)
    if (res.success) { showLocationModalFlag.value = false; loadLocations(selectedWarehouse.value.id) }
    else alert(res.message || '保存失败')
  } catch (e) { alert('保存失败') }
}

const showInModal = () => {
  inoutForm.value = { product_id: '', warehouse_id: '', quantity: 1, batch_no: '', remark: '' }
  showInModalFlag.value = true
}

const showOutModal = () => {
  inoutForm.value = { product_id: '', warehouse_id: '', quantity: 1, batch_no: '', remark: '' }
  showOutModalFlag.value = true
}

const doIn = async () => {
  if (!inoutForm.value.product_id || !inoutForm.value.warehouse_id || !inoutForm.value.quantity) {
    alert('请填写必填项'); return
  }
  try {
    const res = await post('/api/inventory/in', inoutForm.value)
    if (res.success) { alert('入库成功'); showInModalFlag.value = false; loadTransactions() }
    else alert(res.message || '入库失败')
  } catch (e) { alert('入库失败') }
}

const doOut = async () => {
  if (!inoutForm.value.product_id || !inoutForm.value.warehouse_id || !inoutForm.value.quantity) {
    alert('请填写必填项'); return
  }
  try {
    const res = await post('/api/inventory/out', inoutForm.value)
    if (res.success) { alert('出库成功'); showOutModalFlag.value = false; loadTransactions() }
    else alert(res.message || '出库失败')
  } catch (e) { alert('出库失败') }
}

const showSupplierModal = () => {
  isEditSupplier.value = false
  supplierForm.value = { id: null, code: '', name: '', contact_person: '', contact_phone: '', rating: 3 }
  showSupplierModalFlag.value = true
}

const editSupplier = (s) => {
  isEditSupplier.value = true
  supplierForm.value = { ...s }
  showSupplierModalFlag.value = true
}

const saveSupplier = async () => {
  if (!supplierForm.value.code || !supplierForm.value.name) { alert('请填写必填项'); return }
  try {
    const res = isEditSupplier.value
      ? await post(`/api/purchase/suppliers/${supplierForm.value.id}`, supplierForm.value)
      : await post('/api/purchase/suppliers', supplierForm.value)
    if (res.success) { showSupplierModalFlag.value = false; loadSuppliers() }
    else alert(res.message || '保存失败')
  } catch (e) { alert('保存失败') }
}

const exportData = () => {
  alert('导出功能开发中')
}

onMounted(() => {
  loadMaterials()
  loadWarehouses()
  loadTransactions()
})
</script>

<style scoped>
.text-red { color: #dc3545; }
.text-green { color: #28a745; }
.text-center { text-align: center; }
.tabs { display: flex; gap: 5px; margin: 15px 0; }
.tabs button { padding: 8px 20px; border: 1px solid #ddd; background: #f8f9fa; cursor: pointer; }
.tabs button.active { background: #007bff; color: white; border-color: #007bff; }
.form-group { margin-bottom: 10px; }
.form-group label { display: block; margin-bottom: 3px; font-weight: 500; }
.form-group input, .form-group select { width: 100%; padding: 6px 10px; border: 1px solid #ddd; border-radius: 4px; }
.page-header { display: flex; justify-content: space-between; align-items: center; padding-bottom: 10px; border-bottom: 1px solid #eee; margin-bottom: 15px; }
.page-header h2, .page-header h4 { margin: 0; }
</style>
