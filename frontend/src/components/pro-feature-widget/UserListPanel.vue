<template>
  <div class="user-list-panel">
    <div class="panel-header">
      <h3 class="panel-title">客户管理</h3>
      <div class="header-actions">
        <button class="action-btn add" @click="handleAdd">
          <i class="fa fa-plus" aria-hidden="true"></i> 添加客户
        </button>
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
        placeholder="搜索客户..."
      />
    </div>
    
    <div class="customers-list">
      <div 
        v-for="customer in filteredCustomers" 
        :key="customer.id"
        class="customer-item"
        :class="{ 'selected': selectedCustomer?.id === customer.id }"
        @click="handleSelect(customer)"
      >
        <div class="customer-avatar">
          {{ customer.name?.charAt(0) || '?' }}
        </div>
        <div class="customer-info">
          <div class="customer-name">{{ customer.name }}</div>
          <div class="customer-detail">{{ customer.phone || customer.email || '无联系方式' }}</div>
        </div>
        <div class="customer-actions">
          <button class="icon-btn edit" @click.stop="handleEdit(customer)">
            <i class="fa fa-pencil" aria-hidden="true"></i>
          </button>
          <button class="icon-btn delete" @click.stop="handleDelete(customer)">
            <i class="fa fa-times" aria-hidden="true"></i>
          </button>
        </div>
      </div>
      
      <div v-if="filteredCustomers.length === 0" class="empty-state">
        <div class="empty-icon"><i class="fa fa-list-alt" aria-hidden="true"></i></div>
        <div class="empty-text">暂无客户数据</div>
      </div>
    </div>
    
    <div v-if="showEditModal" class="edit-modal">
      <div class="modal-content">
        <div class="modal-header">
          <h4>{{ editingCustomer ? '编辑客户' : '添加客户' }}</h4>
          <button class="close-btn" @click="closeModal">×</button>
        </div>
        
        <div class="modal-body">
          <div class="form-group">
            <label>姓名</label>
            <input v-model="editForm.name" type="text" class="form-input" />
          </div>
          <div class="form-group">
            <label>电话</label>
            <input v-model="editForm.phone" type="text" class="form-input" />
          </div>
          <div class="form-group">
            <label>邮箱</label>
            <input v-model="editForm.email" type="email" class="form-input" />
          </div>
          <div class="form-group">
            <label>公司</label>
            <input v-model="editForm.company" type="text" class="form-input" />
          </div>
          <div class="form-group">
            <label>地址</label>
            <textarea v-model="editForm.address" class="form-textarea" rows="2"></textarea>
          </div>
        </div>
        
        <div class="modal-footer">
          <button class="btn cancel" @click="closeModal">取消</button>
          <button class="btn save" @click="saveCustomer">保存</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  customers: {
    type: Array,
    default: () => []
  }
})

const emit = defineEmits(['add', 'edit', 'delete', 'export'])

const searchQuery = ref('')
const selectedCustomer = ref(null)
const showEditModal = ref(false)
const editingCustomer = ref(null)
const editForm = ref({
  name: '',
  phone: '',
  email: '',
  company: '',
  address: ''
})

const filteredCustomers = computed(() => {
  if (!searchQuery.value) return props.customers
  
  const query = searchQuery.value.toLowerCase()
  return props.customers.filter(c => 
    c.name?.toLowerCase().includes(query) ||
    c.phone?.toLowerCase().includes(query) ||
    c.email?.toLowerCase().includes(query) ||
    c.company?.toLowerCase().includes(query)
  )
})

function handleSelect(customer) {
  selectedCustomer.value = customer
}

function handleAdd() {
  editingCustomer.value = null
  editForm.value = { name: '', phone: '', email: '', company: '', address: '' }
  showEditModal.value = true
}

function handleEdit(customer) {
  editingCustomer.value = customer
  editForm.value = { ...customer }
  showEditModal.value = true
}

function handleDelete(customer) {
  if (confirm(`确定要删除客户 "${customer.name}" 吗？`)) {
    emit('delete', customer)
  }
}

function handleExport() {
  emit('export')
}

function closeModal() {
  showEditModal.value = false
  editingCustomer.value = null
}

function saveCustomer() {
  if (editingCustomer.value) {
    emit('edit', { ...editForm.value, id: editingCustomer.value.id })
  } else {
    emit('add', editForm.value)
  }
  closeModal()
}
</script>

<style scoped>
.user-list-panel {
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
  border: 1px solid rgba(0, 255, 255, 0.4);
  border-radius: 6px;
  background: rgba(0, 255, 255, 0.1);
  color: rgba(0, 255, 255, 0.9);
  font-size: 13px;
  cursor: pointer;
  transition: all 0.3s;
}

.action-btn:hover {
  background: rgba(0, 255, 255, 0.2);
}

.action-btn.export {
  border-color: rgba(255, 204, 0, 0.4);
  background: rgba(255, 204, 0, 0.1);
  color: rgba(255, 204, 0, 0.9);
}

.action-btn.export:hover {
  background: rgba(255, 204, 0, 0.2);
}

.search-bar {
  margin-bottom: 16px;
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

.customers-list {
  flex: 1;
  overflow-y: auto;
}

.customer-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.3s;
}

.customer-item:hover {
  background: rgba(0, 255, 255, 0.1);
}

.customer-item.selected {
  background: rgba(0, 255, 255, 0.15);
  border: 1px solid rgba(0, 255, 255, 0.3);
}

.customer-avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: rgba(0, 255, 255, 0.2);
  border: 1px solid rgba(0, 255, 255, 0.3);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  font-weight: bold;
  color: rgba(0, 255, 255, 0.9);
}

.customer-info {
  flex: 1;
}

.customer-name {
  font-size: 14px;
  font-weight: bold;
  color: rgba(255, 255, 255, 0.9);
  margin-bottom: 4px;
}

.customer-detail {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.6);
}

.customer-actions {
  display: flex;
  gap: 4px;
}

.icon-btn {
  width: 28px;
  height: 28px;
  border-radius: 6px;
  border: none;
  background: transparent;
  color: rgba(255, 255, 255, 0.6);
  font-size: 16px;
  cursor: pointer;
  transition: all 0.3s;
}

.icon-btn:hover {
  background: rgba(0, 255, 255, 0.2);
  color: rgba(0, 255, 255, 0.9);
}

.icon-btn.delete:hover {
  background: rgba(255, 0, 0, 0.2);
  color: rgba(255, 0, 0, 0.9);
}

.empty-state {
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

.edit-modal {
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

.form-group {
  margin-bottom: 12px;
}

.form-group label {
  display: block;
  margin-bottom: 6px;
  font-size: 13px;
  color: rgba(0, 255, 255, 0.8);
}

.form-input,
.form-textarea {
  width: 100%;
  padding: 8px 12px;
  background: rgba(0, 255, 255, 0.1);
  border: 1px solid rgba(0, 255, 255, 0.3);
  border-radius: 6px;
  color: rgba(255, 255, 255, 0.9);
  font-size: 14px;
  outline: none;
  box-sizing: border-box;
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

.btn.cancel {
  background: transparent;
  border: 1px solid rgba(0, 255, 255, 0.3);
  color: rgba(0, 255, 255, 0.8);
}

.btn.save {
  background: rgba(0, 255, 255, 0.2);
  border: 1px solid rgba(0, 255, 255, 0.4);
  color: rgba(0, 255, 255, 0.9);
}
</style>
