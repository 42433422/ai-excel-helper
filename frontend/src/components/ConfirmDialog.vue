<template>
  <Teleport to="body">
    <div v-if="modelValue" class="confirm-dialog-overlay" @click.self="handleCancel">
      <div class="confirm-dialog" :style="{ maxWidth: maxWidth }">
        <div class="confirm-dialog-header">
          <h3>{{ title }}</h3>
        </div>
        <div class="confirm-dialog-body">
          <slot>
            <p>{{ message }}</p>
          </slot>
        </div>
        <div class="confirm-dialog-footer">
          <button
            v-if="showCancel"
            class="btn btn-secondary"
            @click="handleCancel"
          >
            {{ cancelText }}
          </button>
          <button
            :class="['btn', confirmClass]"
            @click="handleConfirm"
          >
            {{ confirmText }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false
  },
  title: {
    type: String,
    default: '确认操作'
  },
  message: {
    type: String,
    default: '确定要执行此操作吗？'
  },
  confirmText: {
    type: String,
    default: '确定'
  },
  cancelText: {
    type: String,
    default: '取消'
  },
  confirmClass: {
    type: String,
    default: 'btn-primary'
  },
  showCancel: {
    type: Boolean,
    default: true
  },
  maxWidth: {
    type: String,
    default: '400px'
  }
})

const emit = defineEmits([
  'update:modelValue',
  'confirm',
  'cancel'
])

const handleConfirm = () => {
  emit('confirm')
  emit('update:modelValue', false)
}

const handleCancel = () => {
  emit('cancel')
  emit('update:modelValue', false)
}
</script>

<style scoped>
.confirm-dialog-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 9999;
}

.confirm-dialog {
  background: white;
  border-radius: 8px;
  width: 90%;
  max-width: 400px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
}

.confirm-dialog-header {
  padding: 16px 20px;
  border-bottom: 1px solid #e0e0e0;
}

.confirm-dialog-header h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #333;
}

.confirm-dialog-body {
  padding: 20px;
}

.confirm-dialog-body p {
  margin: 0;
  color: #666;
  line-height: 1.5;
}

.confirm-dialog-footer {
  padding: 16px 20px;
  border-top: 1px solid #e0e0e0;
  display: flex;
  gap: 10px;
  justify-content: flex-end;
}

.btn {
  padding: 8px 16px;
  border: none;
  border-radius: 4px;
  font-size: 14px;
  cursor: pointer;
  transition: background-color 0.2s;
}

.btn-primary {
  background-color: #3498db;
  color: white;
}

.btn-primary:hover {
  background-color: #2980b9;
}

.btn-secondary {
  background-color: #95a5a6;
  color: white;
}

.btn-secondary:hover {
  background-color: #7f8c8d;
}

.btn-danger {
  background-color: #e74c3c;
  color: white;
}

.btn-danger:hover {
  background-color: #c0392b;
}

.btn-success {
  background-color: #2ecc71;
  color: white;
}

.btn-success:hover {
  background-color: #27ae60;
}
</style>
