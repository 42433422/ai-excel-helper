<template>
  <button
    type="button"
    class="workflow-employee-row"
    :aria-pressed="isActive"
    @click="toggleEmployee"
  >
    <span class="workflow-employee-label">
      <slot name="label">{{ label }}</slot>
    </span>
    <div class="toggle-switch workflow-employee-toggle">
      <div 
        class="toggle-slider" 
        :class="{ 'toggle-slider-active': isActive }"
      ></div>
    </div>
  </button>
</template>

<script lang="ts">
import { defineComponent, ref, watch } from 'vue'

export default defineComponent({
  name: 'WorkflowEmployeeRow',
  props: {
    label: {
      type: String,
      default: '真实电话业务员'
    },
    modelValue: {
      type: Boolean,
      default: false
    },
    employeeId: {
      type: String,
      default: 'real_phone'
    }
  },
  emits: ['update:modelValue', 'change', 'toggle'],
  setup(props, { emit }) {
    const isActive = ref(props.modelValue)

    watch(() => props.modelValue, (newValue) => {
      isActive.value = newValue
    })

    const toggleEmployee = () => {
      isActive.value = !isActive.value
      emit('update:modelValue', isActive.value)
      emit('change', isActive.value)
      emit('toggle', { 
        employeeId: props.employeeId, 
        active: isActive.value 
      })
    }

    return {
      isActive,
      toggleEmployee
    }
  }
})
</script>

<style scoped>
.workflow-employee-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  padding: 12px 16px;
  background: #ffffff;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
  font-size: 14px;
  color: #374151;
}

.workflow-employee-row:hover {
  background: #f9fafb;
  border-color: #d1d5db;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.workflow-employee-row[aria-pressed="true"] {
  background: #eff6ff;
  border-color: #3b82f6;
}

.workflow-employee-label {
  font-weight: 500;
  flex: 1;
  text-align: left;
}

.workflow-employee-toggle {
  flex-shrink: 0;
  margin-left: 12px;
}

.toggle-switch {
  position: relative;
  width: 44px;
  height: 24px;
  background: #e5e7eb;
  border-radius: 12px;
  transition: background 0.2s ease;
}

.toggle-slider {
  position: absolute;
  top: 2px;
  left: 2px;
  width: 20px;
  height: 20px;
  background: #ffffff;
  border-radius: 50%;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
  transition: transform 0.2s ease;
}

.toggle-slider-active {
  transform: translateX(20px);
  background: #3b82f6;
}

.toggle-switch:has(.toggle-slider-active) {
  background: #dbeafe;
}
</style>
