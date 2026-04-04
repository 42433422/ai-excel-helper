<template>
  <Teleport to="body">
    <div v-if="modelValue" class="input-dialog-overlay" @click.self="handleCancel">
      <div class="input-dialog" :style="{ maxWidth: maxWidth }">
        <div class="input-dialog-header">
          <h3>{{ title }}</h3>
        </div>
        <div class="input-dialog-body">
          <p v-if="message">{{ message }}</p>
          <input
            ref="inputRef"
            v-model="inputValue"
            :type="inputType"
            :placeholder="placeholder"
            class="input-field"
            @keyup.enter="handleConfirm"
          >
        </div>
        <div class="input-dialog-footer">
          <button
            class="btn btn-secondary"
            @click="handleCancel"
          >
            取消
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
import { ref, watch, nextTick } from 'vue'

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false
  },
  title: {
    type: String,
    default: '输入'
  },
  message: {
    type: String,
    default: ''
  },
  placeholder: {
    type: String,
    default: ''
  },
  confirmText: {
    type: String,
    default: '确定'
  },
  confirmClass: {
    type: String,
    default: 'btn-primary'
  },
  maxWidth: {
    type: String,
    default: '400px'
  },
  inputType: {
    type: String,
    default: 'text'
  }
})

const emit = defineEmits([
  'update:modelValue',
  'confirm',
  'cancel'
])

const inputRef = ref(null)
const inputValue = ref('')

watch(() => props.modelValue, async (newVal) => {
  if (newVal) {
    await nextTick()
    inputRef.value?.focus()
  }
})

const handleConfirm = () => {
  emit('confirm', inputValue.value)
  emit('update:modelValue', false)
}

const handleCancel = () => {
  emit('cancel')
  emit('update:modelValue', false)
}

const reset = () => {
  inputValue.value = ''
}

defineExpose({ reset })
</script>

<style scoped>
.input-dialog-overlay {
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

.input-dialog {
  background: white;
  border-radius: 8px;
  width: 90%;
  max-width: 400px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
}

.input-dialog-header {
  padding: 16px 20px;
  border-bottom: 1px solid #e0e0e0;
}

.input-dialog-header h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #333;
}

.input-dialog-body {
  padding: 20px;
}

.input-dialog-body p {
  margin: 0 0 12px 0;
  color: #666;
  line-height: 1.5;
}

.input-field {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 14px;
  outline: none;
  transition: border-color 0.2s;
  box-sizing: border-box;
}

.input-field:focus {
  border-color: #42b983;
}

.input-dialog-footer {
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
  background-color: #42b983;
  color: white;
}

.btn-primary:hover {
  background-color: #3aa876;
}

.btn-secondary {
  background-color: #95a5a6;
  color: white;
}

.btn-secondary:hover {
  background-color: #7f8c8d;
}
</style>
