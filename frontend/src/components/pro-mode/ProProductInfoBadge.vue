<template>
  <div 
    class="pro-product-info-badge"
    :style="{ 
      transform: `translate(-50%, -50%) scale(${scale})`,
      opacity: show ? 1 : 0
    }"
  >
    <div class="badge-content">
      <div class="badge-header">
        <h3 class="badge-title">产品信息</h3>
        <button class="close-button" @click="handleClose">×</button>
      </div>
      
      <div class="badge-body">
        <div class="form-group">
          <label class="form-label">产品名称</label>
          <input 
            v-model="formData.name"
            type="text"
            class="form-input"
            placeholder="请输入产品名称"
          />
        </div>
        
        <div class="form-group">
          <label class="form-label">产品型号</label>
          <input 
            v-model="formData.model"
            type="text"
            class="form-input"
            placeholder="请输入产品型号"
          />
        </div>
        
        <div class="form-group">
          <label class="form-label">单价（元）</label>
          <input 
            v-model="formData.price"
            type="number"
            step="0.01"
            class="form-input"
            placeholder="请输入单价"
          />
        </div>
        
        <div class="form-group">
          <label class="form-label">描述</label>
          <textarea 
            v-model="formData.description"
            class="form-textarea"
            rows="3"
            placeholder="请输入产品描述"
          ></textarea>
        </div>
      </div>
      
      <div class="badge-footer">
        <button 
          class="badge-button save"
          @click="handleSave"
          :disabled="!isFormValid"
        >
          保存
        </button>
        <button 
          class="badge-button cancel"
          @click="handleCancel"
        >
          取消
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'

const props = defineProps({
  show: {
    type: Boolean,
    default: false
  },
  product: {
    type: Object,
    default: null
  },
  scale: {
    type: Number,
    default: 1
  }
})

const emit = defineEmits(['save', 'close'])

const formData = ref({
  name: '',
  model: '',
  price: '',
  description: ''
})

const isFormValid = computed(() => {
  return formData.value.name.trim() !== '' && 
         formData.value.model.trim() !== '' && 
         formData.value.price !== ''
})

watch(() => props.product, (newProduct) => {
  if (newProduct) {
    formData.value = {
      name: newProduct.name || '',
      model: newProduct.model || '',
      price: newProduct.price || '',
      description: newProduct.description || ''
    }
  }
}, { deep: true })

function handleSave() {
  if (!isFormValid.value) return
  
  emit('save', {
    ...formData.value,
    price: parseFloat(formData.value.price)
  })
}

function handleCancel() {
  emit('close')
}

function handleClose() {
  emit('close')
}
</script>

<style scoped>
.pro-product-info-badge {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 300px;
  background: rgba(10, 14, 39, 0.95);
  border: 1px solid rgba(0, 255, 255, 0.5);
  border-radius: 12px;
  box-shadow: 0 0 20px rgba(0, 255, 255, 0.3);
  backdrop-filter: blur(10px);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  z-index: 100;
}

.badge-content {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.badge-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  border-bottom: 1px solid rgba(0, 255, 255, 0.2);
  margin-bottom: 16px;
}

.badge-title {
  margin: 0;
  font-size: 18px;
  font-weight: bold;
  color: rgba(0, 255, 255, 0.9);
}

.close-button {
  background: transparent;
  border: none;
  color: rgba(0, 255, 255, 0.7);
  font-size: 24px;
  cursor: pointer;
  padding: 0;
  line-height: 1;
  transition: color 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.close-button:hover {
  color: rgba(0, 255, 255, 0.9);
}

.badge-body {
  flex: 1;
  padding: 0 16px 16px;
  overflow-y: auto;
}

.form-group {
  margin-bottom: 16px;
}

.form-label {
  display: block;
  margin-bottom: 8px;
  font-size: 14px;
  color: rgba(0, 255, 255, 0.8);
  font-weight: 500;
}

.form-input,
.form-textarea {
  width: 100%;
  padding: 10px 12px;
  background: rgba(0, 255, 255, 0.1);
  border: 1px solid rgba(0, 255, 255, 0.3);
  border-radius: 6px;
  color: rgba(255, 255, 255, 0.9);
  font-size: 14px;
  outline: none;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  box-sizing: border-box;
}

.form-input:focus,
.form-textarea:focus {
  border-color: rgba(0, 255, 255, 0.6);
  background: rgba(0, 255, 255, 0.15);
  box-shadow: 0 0 10px rgba(0, 255, 255, 0.2);
}

.form-textarea {
  resize: vertical;
  min-height: 80px;
  font-family: inherit;
}

.badge-footer {
  display: flex;
  gap: 12px;
  padding: 16px;
  border-top: 1px solid rgba(0, 255, 255, 0.2);
}

.badge-button {
  flex: 1;
  padding: 12px 24px;
  border: none;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.badge-button.save {
  background: rgba(0, 255, 255, 0.2);
  color: rgba(0, 0, 0, 0.9);
  border: 1px solid rgba(0, 255, 255, 0.4);
}

.badge-button.save:hover:not(:disabled) {
  background: rgba(0, 255, 255, 0.3);
  transform: scale(1.05);
}

.badge-button.save:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.badge-button.cancel {
  background: transparent;
  color: rgba(0, 255, 255, 0.7);
  border: 1px solid rgba(0, 255, 255, 0.3);
}

.badge-button.cancel:hover {
  background: rgba(0, 255, 255, 0.1);
  border-color: rgba(0, 255, 255, 0.5);
}
</style>
