<template>
  <div class="product-query-panel">
    <div class="panel-header">
      <h3 class="panel-title">产品查询</h3>
      <div class="header-actions">
        <button class="action-btn export" @click="handleExport">
          导出Excel
        </button>
      </div>
    </div>
    
    <div class="search-bar">
      <input 
        v-model="searchQuery"
        type="text"
        class="search-input"
        placeholder="搜索产品..."
      />
    </div>
    
    <div class="company-filter">
      <button 
        class="filter-btn"
        :class="{ 'active': !selectedCompanyId }"
        @click="selectedCompanyId = null"
      >
        全部
      </button>
      <button 
        v-for="company in companies"
        :key="company.id"
        class="filter-btn"
        :class="{ 'active': selectedCompanyId === company.id }"
        @click="selectedCompanyId = company.id"
      >
        {{ company.name }}
      </button>
    </div>
    
    <div class="products-grid">
      <div 
        v-for="product in filteredProducts"
        :key="product.id"
        class="product-card"
        @click="handleSelect(product)"
      >
        <div class="product-header">
          <div class="product-name">{{ product.name }}</div>
          <div class="product-model">{{ product.model }}</div>
        </div>
        <div class="product-body">
          <div class="product-price">¥{{ product.price }}</div>
          <div class="product-company">{{ product.companyName }}</div>
        </div>
      </div>
      
      <div v-if="filteredProducts.length === 0" class="empty-state">
        <div class="empty-icon"><i class="fa fa-cubes" aria-hidden="true"></i></div>
        <div class="empty-text">暂无产品数据</div>
      </div>
    </div>
    
    <div v-if="selectedProduct" class="product-detail-modal">
      <div class="modal-content">
        <div class="modal-header">
          <h4>产品详情</h4>
          <button class="close-btn" @click="selectedProduct = null">×</button>
        </div>
        
        <div class="modal-body">
          <div class="detail-row">
            <span class="detail-label">产品名称</span>
            <span class="detail-value">{{ selectedProduct.name }}</span>
          </div>
          <div class="detail-row">
            <span class="detail-label">产品型号</span>
            <span class="detail-value">{{ selectedProduct.model }}</span>
          </div>
          <div class="detail-row">
            <span class="detail-label">单价</span>
            <span class="detail-value price">¥{{ selectedProduct.price }}</span>
          </div>
          <div class="detail-row">
            <span class="detail-label">公司</span>
            <span class="detail-value">{{ selectedProduct.companyName }}</span>
          </div>
          <div class="detail-row">
            <span class="detail-label">描述</span>
            <span class="detail-value">{{ selectedProduct.description || '暂无描述' }}</span>
          </div>
        </div>
        
        <div class="modal-footer">
          <button class="btn edit" @click="handleEdit">编辑</button>
          <button class="btn close" @click="selectedProduct = null">关闭</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  products: {
    type: Array,
    default: () => []
  },
  companies: {
    type: Array,
    default: () => []
  }
})

const emit = defineEmits(['select', 'edit', 'export'])

const searchQuery = ref('')
const selectedCompanyId = ref(null)
const selectedProduct = ref(null)

const filteredProducts = computed(() => {
  let result = props.products
  
  if (selectedCompanyId.value) {
    result = result.filter(p => p.companyId === selectedCompanyId.value)
  }
  
  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    result = result.filter(p =>
      p.name?.toLowerCase().includes(query) ||
      p.model?.toLowerCase().includes(query) ||
      p.companyName?.toLowerCase().includes(query)
    )
  }
  
  return result
})

function handleSelect(product) {
  selectedProduct.value = product
  emit('select', product)
}

function handleEdit() {
  emit('edit', selectedProduct.value)
}

function handleExport() {
  emit('export', selectedCompanyId.value)
}
</script>

<style scoped>
.product-query-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.panel-title {
  margin: 0;
  font-size: 18px;
  font-weight: bold;
  color: rgba(0, 255, 255, 0.9);
}

.header-actions {
  display: flex;
  gap: 8px;
}

.action-btn {
  padding: 8px 16px;
  border: 1px solid rgba(255, 204, 0, 0.4);
  border-radius: 6px;
  background: rgba(255, 204, 0, 0.1);
  color: rgba(255, 204, 0, 0.9);
  font-size: 13px;
  cursor: pointer;
  transition: all 0.3s;
}

.action-btn:hover {
  background: rgba(255, 204, 0, 0.2);
}

.search-bar {
  margin-bottom: 12px;
}

.search-input {
  width: 100%;
  padding: 10px 14px;
  background: rgba(0, 255, 255, 0.1);
  border: 1px solid rgba(0, 255, 255, 0.3);
  border-radius: 8px;
  color: rgba(255, 255, 255, 0.9);
  font-size: 14px;
  outline: none;
}

.search-input:focus {
  border-color: rgba(0, 255, 255, 0.6);
}

.company-filter {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 16px;
}

.filter-btn {
  padding: 6px 12px;
  border: 1px solid rgba(0, 255, 255, 0.3);
  border-radius: 20px;
  background: transparent;
  color: rgba(0, 255, 255, 0.7);
  font-size: 12px;
  cursor: pointer;
  transition: all 0.3s;
}

.filter-btn:hover {
  background: rgba(0, 255, 255, 0.1);
}

.filter-btn.active {
  background: rgba(0, 255, 255, 0.2);
  border-color: rgba(0, 255, 255, 0.6);
  color: rgba(0, 255, 255, 0.9);
}

.products-grid {
  flex: 1;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 12px;
  overflow-y: auto;
  padding-right: 8px;
}

.product-card {
  background: rgba(0, 255, 255, 0.05);
  border: 1px solid rgba(0, 255, 255, 0.2);
  border-radius: 8px;
  padding: 12px;
  cursor: pointer;
  transition: all 0.3s;
}

.product-card:hover {
  background: rgba(0, 255, 255, 0.1);
  border-color: rgba(0, 255, 255, 0.4);
  transform: translateY(-2px);
}

.product-header {
  margin-bottom: 8px;
}

.product-name {
  font-size: 14px;
  font-weight: bold;
  color: rgba(0, 255, 255, 0.9);
  margin-bottom: 4px;
}

.product-model {
  font-size: 12px;
  color: rgba(0, 255, 255, 0.6);
}

.product-body {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.product-price {
  font-size: 16px;
  font-weight: bold;
  color: rgba(255, 204, 0, 0.9);
}

.product-company {
  font-size: 11px;
  color: rgba(0, 255, 255, 0.6);
}

.empty-state {
  grid-column: 1 / -1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px;
}

.empty-icon {
  font-size: 48px;
  margin-bottom: 12px;
  opacity: 0.5;
}

.empty-text {
  font-size: 14px;
  color: rgba(255, 255, 255, 0.6);
}

.product-detail-modal {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1200;
}

.modal-content {
  width: 400px;
  background: rgba(10, 14, 39, 0.98);
  border: 1px solid rgba(0, 255, 255, 0.5);
  border-radius: 12px;
  overflow: hidden;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  border-bottom: 1px solid rgba(0, 255, 255, 0.2);
}

.modal-header h4 {
  margin: 0;
  font-size: 16px;
  color: rgba(0, 255, 255, 0.9);
}

.close-btn {
  background: transparent;
  border: none;
  color: rgba(0, 255, 255, 0.7);
  font-size: 24px;
  cursor: pointer;
}

.modal-body {
  padding: 16px;
}

.detail-row {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 12px;
  padding-bottom: 12px;
  border-bottom: 1px solid rgba(0, 255, 255, 0.1);
}

.detail-row:last-child {
  margin-bottom: 0;
  padding-bottom: 0;
  border-bottom: none;
}

.detail-label {
  font-size: 13px;
  color: rgba(0, 255, 255, 0.7);
}

.detail-value {
  font-size: 14px;
  color: rgba(255, 255, 255, 0.9);
  text-align: right;
}

.detail-value.price {
  font-size: 18px;
  font-weight: bold;
  color: rgba(255, 204, 0, 0.9);
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding: 16px;
  border-top: 1px solid rgba(0, 255, 255, 0.2);
}

.btn {
  padding: 8px 20px;
  border-radius: 6px;
  font-size: 14px;
  cursor: pointer;
}

.btn.edit {
  background: rgba(0, 255, 255, 0.2);
  border: 1px solid rgba(0, 255, 255, 0.4);
  color: rgba(0, 255, 255, 0.9);
}

.btn.close {
  background: transparent;
  border: 1px solid rgba(0, 255, 255, 0.3);
  color: rgba(0, 255, 255, 0.8);
}
</style>
