<template>
  <div class="page-view" id="view-create-order">
    <div class="page-content">
      <div class="page-header">
        <h2>新建发货单</h2>
        <button class="btn btn-secondary" @click="$router.push('/orders')">返回列表</button>
      </div>

      <div v-if="status.message" :class="['status', status.type]" style="display: block; margin-bottom: 20px;">
        {{ status.message }}
      </div>

      <div class="card">
        <h3>选择发货单模板</h3>
        <div class="form-row">
          <div class="form-col">
            <label>发货单模板</label>
            <select v-model="form.templateName" @change="onTemplateChange">
              <option value="">-- 请选择模板 --</option>
              <option v-for="t in templates" :key="t.name" :value="t.name">{{ t.name }}</option>
            </select>
          </div>
          <div class="form-col" style="flex: 0;">
            <label>&nbsp;</label>
            <button class="btn" @click="loadTemplates">刷新模板列表</button>
          </div>
        </div>
      </div>

      <div class="card header-section">
        <h3>基础信息</h3>
        <div class="form-row">
          <div class="form-col">
            <label>购买单位 *</label>
            <div style="display: flex; gap: 10px;">
              <select v-model="form.purchaseUnit" @change="onPurchaseUnitChange" style="flex: 1;">
                <option value="">-- 选择购买单位 --</option>
                <option v-for="u in purchaseUnits" :key="u.unit_name" :value="u.unit_name">
                  {{ u.unit_name }}{{ u.contact_person ? ` (${u.contact_person})` : '' }}
                </option>
              </select>
              <a href="/purchase-units" class="btn btn-secondary" style="white-space: nowrap; text-decoration: none; display: inline-flex; align-items: center;">+ 新建</a>
            </div>
          </div>
          <div class="form-col">
            <label>联系人</label>
            <input type="text" v-model="form.contactPerson" placeholder="联系人姓名">
          </div>
        </div>
        <div class="form-row">
          <div class="form-col">
            <label>日期 *</label>
            <input type="date" v-model="form.purchaseDate" @change="onDateChange">
          </div>
          <div class="form-col">
            <label>订单编号</label>
            <input type="text" v-model="form.orderNumber" placeholder="订单编号" readonly style="background-color: #f0f0f0;">
          </div>
        </div>
      </div>

      <div class="card">
        <h3>产品信息</h3>
        <div style="margin-bottom: 15px;">
          <button class="btn btn-success" @click="addProductRow"><i class="fa fa-plus" aria-hidden="true"></i> 添加产品</button>
          <button class="btn" @click="showProductSelector = true"><i class="fa fa-search" aria-hidden="true"></i> 选择产品名称</button>
          <a href="/product-names" class="btn btn-secondary" style="text-decoration: none;"><i class="fa fa-cubes" aria-hidden="true"></i> 管理产品库</a>
        </div>

        <div v-if="products.length === 0" class="empty-products">
          暂无产品，请点击"添加产品"或"选择产品名称"添加产品
        </div>

        <div v-for="(product, index) in products" :key="product.id" class="product-row">
          <div class="product-cell">
            <label>产品型号 *</label>
            <input type="text" v-model="product.model" placeholder="产品型号" @input="onProductModelChange(product, index)">
          </div>
          <div class="product-cell">
            <label>产品名称 *</label>
            <select v-model="product.nameId" @change="onProductNameSelect(product, index)">
              <option value="">-- 请选择产品 --</option>
              <option v-for="p in allProducts" :key="p.id" :value="p.id">
                {{ p.name }}{{ p.model_number ? ` (${p.model_number})` : '' }}
              </option>
            </select>
            <input type="hidden" v-model="product.name">
          </div>
          <div class="product-cell">
            <label>数量/件</label>
            <input type="number" v-model.number="product.quantityBox" min="0" step="1" @input="calculateKg(index)">
          </div>
          <div class="product-cell">
            <label>规格/KG</label>
            <input type="number" v-model.number="product.specification" min="0" step="0.01" @input="calculateKg(index)">
          </div>
          <div class="product-cell">
            <label>数量/KG</label>
            <input type="number" v-model.number="product.quantityKg" min="0" step="0.01" @input="calculateAmount(index)">
          </div>
          <div class="product-cell">
            <label>单价/元</label>
            <input type="number" v-model.number="product.unitPrice" min="0" step="0.01" @input="calculateAmount(index)">
          </div>
          <div class="product-cell">
            <label>金额/元</label>
            <input type="number" v-model.number="product.amount" readonly style="background-color: #f0f0f0;">
          </div>
          <div class="product-cell">
            <label>&nbsp;</label>
            <button class="btn btn-danger" @click="removeProductRow(index)" style="padding: 8px 15px;">删除</button>
          </div>
        </div>
      </div>

      <div class="card">
        <h3>操作</h3>
        <div style="text-align: center;">
          <button class="btn btn-success" @click="generateShipment" style="padding: 15px 40px; font-size: 18px;">
            <i class="fa fa-rocket" aria-hidden="true"></i> 生成发货单
          </button>
          <button class="btn btn-secondary" @click="resetForm" style="padding: 15px 40px; font-size: 18px;">
            <i class="fa fa-refresh" aria-hidden="true"></i> 重置
          </button>
          <button class="btn" @click="$router.push({ path: '/template-preview', query: { scope: 'orders' } })" style="padding: 15px 40px; font-size: 18px;">
            <i class="fa fa-edit" aria-hidden="true"></i> 模板编辑
          </button>
        </div>
      </div>

      <div v-if="result" class="card" style="margin-top: 20px;">
        <h3><i class="fa fa-check-circle-o" aria-hidden="true"></i> 生成结果</h3>
        <div style="text-align: center; padding: 20px;">
          <p style="margin-bottom: 15px;">文件名: {{ result.output_filename }}</p>
          <a :href="`/download/${result.output_filename}`" class="btn btn-success" download style="padding: 15px 30px; font-size: 16px;">
            <i class="fa fa-download" aria-hidden="true"></i> 下载发货单
          </a>
          <button class="btn" @click="resetForm" style="padding: 15px 30px; font-size: 16px;">
            <i class="fa fa-plus-square-o" aria-hidden="true"></i> 新建发货单
          </button>
        </div>
      </div>
    </div>

    <div v-if="showProductSelector" class="modal-overlay" @click.self="showProductSelector = false">
      <div class="modal-content" style="width: 80%; max-width: 800px;">
        <div class="modal-header">
          <h3>选择产品</h3>
          <button class="close-btn" @click="showProductSelector = false">&times;</button>
        </div>
        <div class="modal-body">
          <div style="margin-bottom: 15px;">
            <input type="text" v-model="productSearchQuery" placeholder="搜索产品名称或型号..." style="width: 70%;">
            <button class="btn" @click="searchProductsForSelection">搜索</button>
          </div>
          <div style="max-height: 400px; overflow-y: auto;">
            <div v-if="searchingProducts" class="loading">加载中...</div>
            <div v-else-if="filteredProductsForSelection.length === 0" class="no-products">未找到产品</div>
            <div
              v-else
              v-for="(product, index) in filteredProductsForSelection"
              :key="product.id"
              class="product-item"
              @click="selectProductForAdd(product)"
            >
              <div style="font-weight: 600; font-size: 16px;">{{ product.name || '' }}</div>
              <div style="margin-top: 5px; color: #666; font-size: 14px;">
                {{ product.model_number ? `型号: ${product.model_number}` : '' }}
                {{ product.purchase_unit_name ? ` | 单位: ${product.purchase_unit_name}` : '' }}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import api from '../api/index'

const router = useRouter()

function handleAIFillOrder(data) {
  if (!data) return

  if (data.purchaseUnit) {
    const matchedUnit = purchaseUnits.value.find(u => u.unit_name === data.purchaseUnit)
    if (matchedUnit) {
      form.purchaseUnit = data.purchaseUnit
      form.contactPerson = data.contactPerson || matchedUnit.contact_person || ''
    } else {
      form.purchaseUnit = data.purchaseUnit
      form.contactPerson = data.contactPerson || ''
    }
  }

  if (data.contactPerson && !form.contactPerson) {
    form.contactPerson = data.contactPerson
  }

  if (data.date) {
    form.purchaseDate = data.date
    generateOrderNumber()
  }

  if (data.autoPrint !== undefined) {
    form.autoPrint = data.autoPrint
  }

  if (data.products && Array.isArray(data.products) && data.products.length > 0) {
    products.value = []
    data.products.forEach(p => {
      const nameId = p.nameId || ''
      const matchedProduct = nameId ? allProducts.value.find(ap => ap.id == nameId) : null

      products.value.push({
        id: ++productIdCounter,
        nameId: nameId,
        name: p.name || matchedProduct?.name || '',
        model: p.model || '',
        quantityBox: p.quantityBox || 1,
        specification: p.specification || matchedProduct?.specification || 0,
        quantityKg: p.quantityKg || 0,
        unitPrice: p.unitPrice || matchedProduct?.price || 0,
        amount: p.amount || 0
      })

      const idx = products.value.length - 1
      if (products.value[idx].specification && !p.quantityKg) {
        calculateKg(idx)
      }
      if (products.value[idx].unitPrice && !p.amount) {
        calculateAmount(idx)
      }
    })
  }

  showStatus('AI 数据已自动填充', 'success')
}

function setupAIEventListener() {
  window.addEventListener('xcagi:ai-fill-order', (event) => {
    handleAIFillOrder(event.detail)
  })

  window.__VUE_FILL_ORDER__ = handleAIFillOrder
}

onMounted(() => {
  loadTemplates()
  loadPurchaseUnits()
  loadAllProducts()
  generateOrderNumber()
  setupAIEventListener()
})

onUnmounted(() => {
  window.removeEventListener('xcagi:ai-fill-order', handleAIFillOrder)
  if (window.__VUE_FILL_ORDER__ === handleAIFillOrder) {
    delete window.__VUE_FILL_ORDER__
  }
})

const templates = ref([])
const purchaseUnits = ref([])
const allProducts = ref([])
const products = ref([])
let productIdCounter = 0

const status = reactive({
  message: '',
  type: ''
})

const form = reactive({
  templateName: '',
  purchaseUnit: '',
  contactPerson: '',
  purchaseDate: new Date().toISOString().split('T')[0],
  orderNumber: '',
  autoPrint: false
})

const result = ref(null)
const showProductSelector = ref(false)
const productSearchQuery = ref('')
const searchingProducts = ref(false)

const filteredProductsForSelection = computed(() => {
  if (!productSearchQuery.value) return allProducts.value
  const q = productSearchQuery.value.toLowerCase()
  return allProducts.value.filter(p =>
    (p.name && p.name.toLowerCase().includes(q)) ||
    (p.model_number && p.model_number.toLowerCase().includes(q))
  )
})

function showStatus(message, type) {
  status.message = message
  status.type = type
  setTimeout(() => {
    status.message = ''
    status.type = ''
  }, 5000)
}

async function loadTemplates() {
  try {
    const response = await fetch('/templates?action=api', {
      headers: {
        'Accept': 'application/json',
        'X-Requested-With': 'XMLHttpRequest'
      }
    })
    const data = await response.json()
    if (data.success) {
      templates.value = data.templates
      if (data.templates.length > 0 && !form.templateName) {
        form.templateName = data.templates[0].name
      }
    }
  } catch (error) {
    console.error('加载模板失败:', error)
  }
}

function onTemplateChange() {
  console.log('已选择模板:', form.templateName)
}

async function loadPurchaseUnits() {
  try {
    const response = await fetch('/api/purchase_units')
    const data = await response.json()
    if (data.success) {
      purchaseUnits.value = data.data
    }
  } catch (error) {
    console.error('加载购买单位失败:', error)
  }
}

async function onPurchaseUnitChange() {
  if (form.purchaseUnit) {
    try {
      const response = await fetch(`/api/purchase_units/by_name/${encodeURIComponent(form.purchaseUnit)}`)
      const data = await response.json()
      if (data.success) {
        form.contactPerson = data.data.contact_person || ''
      }
    } catch (error) {
      console.error('获取购买单位信息失败:', error)
    }
  }
}

async function loadAllProducts() {
  try {
    const response = await fetch('/api/product_names')
    const data = await response.json()
    if (data.success) {
      allProducts.value = data.data
    }
  } catch (error) {
    console.error('加载产品名称列表失败:', error)
  }
}

async function generateOrderNumber() {
  try {
    const response = await fetch('/orders/next_number?suffix=A')
    const data = await response.json()
    if (data.success) {
      form.orderNumber = data.data.order_number
    }
  } catch (error) {
    console.error('获取订单编号失败:', error)
  }
}

function onDateChange() {
  generateOrderNumber()
}

function addProductRow() {
  products.value.push({
    id: ++productIdCounter,
    nameId: '',
    name: '',
    model: '',
    quantityBox: 1,
    specification: 0,
    quantityKg: 0,
    unitPrice: 0,
    amount: 0
  })
}

function removeProductRow(index) {
  products.value.splice(index, 1)
}

function calculateKg(index) {
  const product = products.value[index]
  product.quantityKg = (product.quantityBox || 0) * (product.specification || 0)
  calculateAmount(index)
}

function calculateAmount(index) {
  const product = products.value[index]
  product.amount = (product.quantityKg || 0) * (product.unitPrice || 0)
}

function onProductNameSelect(product, index) {
  const selected = allProducts.value.find(p => p.id == product.nameId)
  if (selected) {
    product.name = selected.name || ''
    if (selected.model_number) {
      product.model = selected.model_number
    }
    if (selected.specification) {
      product.specification = selected.specification
      calculateKg(index)
    }
    if (selected.price) {
      product.unitPrice = selected.price
      calculateAmount(index)
    }
  }
}

function onProductModelChange(product, index) {
  // Auto-fill name when model changes
}

function searchProductsForSelection() {
  searchingProducts.value = true
  setTimeout(() => {
    searchingProducts.value = false
  }, 300)
}

function selectProductForAdd(product) {
  addProductRow()
  const newProduct = products.value[products.value.length - 1]
  newProduct.nameId = product.id
  newProduct.name = product.name || ''
  newProduct.model = product.model_number || ''
  if (product.specification) {
    newProduct.specification = product.specification
    calculateKg(products.value.length - 1)
  }
  if (product.price) {
    newProduct.unitPrice = product.price
    calculateAmount(products.value.length - 1)
  }
  showProductSelector.value = false
}

async function generateShipment() {
  if (!form.templateName) {
    alert('请选择发货单模板')
    return
  }
  if (!form.purchaseUnit) {
    alert('请选择购买单位')
    return
  }
  if (!form.purchaseDate) {
    alert('请选择日期')
    return
  }
  if (products.value.length === 0) {
    alert('请至少添加一个产品')
    return
  }

  showStatus('正在生成发货单...', 'processing')

  const editableData = {
    header_row: {},
    product_rows: [],
    price_row: {}
  }

  const dateStr = form.purchaseDate.replace(/(\d{4})-(\d{2})-(\d{2})/, '$1年$2月$3日')
  editableData.header_row[1] = {
    purchase_unit: form.purchaseUnit,
    contact_person: form.contactPerson,
    purchase_date: dateStr,
    order_number: form.orderNumber
  }

  products.value.forEach((product, index) => {
    const rowNum = index + 4
    const productData = {}
    productData[1] = product.model || ''
    productData[4] = product.name || ''
    productData[5] = product.quantityBox || ''
    productData[6] = product.specification || ''
    productData[7] = product.quantityKg || ''
    productData[8] = product.unitPrice || ''
    productData[9] = product.amount || ''
    editableData.product_rows.push(productData)
  })

  try {
    const response = await fetch('/documents', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        template_name: form.templateName,
        editable_data: editableData,
        // 统一策略：仅使用编号模式，禁用其他模式分支
        number_mode: true,
        custom_mode: false
      })
    })

    const data = await response.json()
    if (data.success) {
      showStatus('发货单生成成功！', 'success')
      result.value = data
    } else {
      showStatus('生成失败: ' + data.message, 'error')
    }
  } catch (error) {
    showStatus('生成失败: ' + error.message, 'error')
  }
}

function resetForm() {
  form.templateName = ''
  form.purchaseUnit = ''
  form.contactPerson = ''
  form.orderNumber = ''
  form.autoPrint = false
  products.value = []
  result.value = null
  form.purchaseDate = new Date().toISOString().split('T')[0]
  generateOrderNumber()
}

onMounted(() => {
  loadTemplates()
  loadPurchaseUnits()
  loadAllProducts()
  generateOrderNumber()
})
</script>

<style scoped>
.page-view {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.page-header h2 {
  margin: 0;
  color: #2c3e50;
}

.form-row {
  display: flex;
  gap: 15px;
  margin-bottom: 15px;
  flex-wrap: wrap;
}

.form-col {
  flex: 1;
  min-width: 200px;
}

.card {
  background-color: #fff;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  padding: 20px;
  margin-bottom: 20px;
  box-shadow: 0 2px 5px rgba(0, 0, 0, 0.05);
}

.card h3 {
  color: #34495e;
  margin: 0 0 15px;
  font-size: 18px;
  border-bottom: 1px solid #e0e0e0;
  padding-bottom: 8px;
}

.header-section {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.header-section h3 {
  color: white;
  border-bottom-color: rgba(255, 255, 255, 0.3);
}

.header-section label {
  color: white;
}

.status {
  margin: 20px 0;
  padding: 15px;
  border-radius: 5px;
  font-weight: 500;
}

.status.success {
  background-color: #d4edda;
  color: #155724;
  border: 1px solid #c3e6cb;
}

.status.error {
  background-color: #f8d7da;
  color: #721c24;
  border: 1px solid #f5c6cb;
}

.status.processing {
  background-color: #d1ecf1;
  color: #0c5460;
  border: 1px solid #bee5eb;
}

.product-row {
  display: grid;
  grid-template-columns: 2fr 2fr 1fr 1fr 1fr 1fr 1fr auto;
  gap: 10px;
  padding: 15px;
  border: 1px solid #e0e0e0;
  border-radius: 5px;
  margin-bottom: 10px;
  background-color: #f9f9f9;
  align-items: end;
}

.product-cell {
  display: flex;
  flex-direction: column;
}

.product-cell label {
  font-size: 12px;
  color: #666;
  margin-bottom: 3px;
}

.product-cell input,
.product-cell select {
  padding: 8px;
  font-size: 13px;
}

.empty-products {
  text-align: center;
  padding: 40px;
  color: #6c757d;
  background-color: #f8f9fa;
  border-radius: 5px;
  border: 2px dashed #dee2e6;
}

.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}

.modal-content {
  background: white;
  border-radius: 8px;
  max-height: 80vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 15px 20px;
  border-bottom: 1px solid #e0e0e0;
}

.modal-header h3 {
  margin: 0;
}

.close-btn {
  background: none;
  border: none;
  font-size: 24px;
  cursor: pointer;
  color: #666;
}

.modal-body {
  padding: 20px;
  overflow-y: auto;
}

.product-item {
  padding: 12px;
  border: 1px solid #e0e0e0;
  border-radius: 5px;
  margin-bottom: 10px;
  cursor: pointer;
  transition: background-color 0.2s;
}

.product-item:hover {
  background-color: #f0f7ff;
  border-color: #3498db;
}

.btn {
  background-color: #3498db;
  color: white;
  border: none;
  padding: 10px 20px;
  border-radius: 5px;
  font-size: 14px;
  cursor: pointer;
  font-weight: 500;
  transition: background-color 0.3s;
}

.btn:hover {
  background-color: #2980b9;
}

.btn-success {
  background-color: #2ecc71;
}

.btn-success:hover {
  background-color: #27ae60;
}

.btn-secondary {
  background-color: #95a5a6;
}

.btn-secondary:hover {
  background-color: #7f8c8d;
}

.btn-danger {
  background-color: #e74c3c;
}

.btn-danger:hover {
  background-color: #c0392b;
}

input, select {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #ddd;
  border-radius: 5px;
  font-size: 14px;
  box-sizing: border-box;
}

input:focus, select:focus {
  outline: none;
  border-color: #3498db;
  box-shadow: 0 0 0 2px rgba(52, 152, 219, 0.2);
}

.loading, .no-products {
  text-align: center;
  padding: 40px;
  color: #6c757d;
}
</style>
