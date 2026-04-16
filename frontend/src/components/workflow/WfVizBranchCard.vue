<template>
  <div 
    class="wf-viz-branch-card" 
    :class="{ 'wf-viz-branch-card--fixed': isFixed }"
  >
    <span 
      class="wf-viz-kind-badge" 
      :class="{ 'wf-viz-kind-badge--sm': size === 'sm' }"
    >
      {{ badgeText }}
    </span>
    
    <div class="wf-viz-branch-title">
      {{ title }}
    </div>
    
    <div class="wf-viz-branch-triggers">
      <slot name="triggers">
        {{ triggersText }}
      </slot>
    </div>
    
    <div v-if="showActions" class="wf-viz-branch-actions">
      <slot name="actions">
        <button 
          class="wf-viz-action-btn" 
          @click="handleConfigure"
          title="配置"
        >
          <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
            <path d="M8 10a2 2 0 100-4 2 2 0 000 4z"/>
            <path fill-rule="evenodd" d="M8 1a7 7 0 100 14A7 7 0 008 1zM0 8a8 8 0 1116 0A8 8 0 010 8z"/>
          </svg>
        </button>
        <button 
          class="wf-viz-action-btn" 
          @click="handleViewDetails"
          title="查看详情"
        >
          <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
            <path d="M8 4a.5.5 0 01.5.5v3h3a.5.5 0 010 1h-3v3a.5.5 0 01-1 0v-3h-3a.5.5 0 010-1h3v-3A.5.5 0 018 4z"/>
          </svg>
        </button>
      </slot>
    </div>
  </div>
</template>

<script lang="ts">
import { defineComponent, computed } from 'vue'

export interface BranchTrigger {
  id: string
  name: string
  status: 'active' | 'inactive' | 'pending'
  description?: string
}

export default defineComponent({
  name: 'WfVizBranchCard',
  props: {
    title: {
      type: String,
      default: '真实电话业务员'
    },
    badgeText: {
      type: String,
      default: '固定扩展'
    },
    size: {
      type: String,
      default: 'sm',
      validator: (value: string) => ['sm', 'md', 'lg'].includes(value)
    },
    isFixed: {
      type: Boolean,
      default: true
    },
    branchId: {
      type: String,
      default: 'real_phone'
    },
    triggers: {
      type: Array as () => BranchTrigger[],
      default: () => []
    },
    showActions: {
      type: Boolean,
      default: true
    }
  },
  emits: ['configure', 'view-details', 'click'],
  setup(props, { emit }) {
    const triggersText = computed(() => {
      if (props.triggers.length > 0) {
        return props.triggers.map(t => t.name).join(' → ')
      }
      return '固定行 id=real_phone；副窗启用 → ADB 设备连通检查 → 来电检测/接听 → 语音转写与回复（与状态轮询同步）'
    })

    const handleConfigure = () => {
      emit('configure', { branchId: props.branchId })
    }

    const handleViewDetails = () => {
      emit('view-details', { branchId: props.branchId })
    }

    const handleClick = () => {
      emit('click', { branchId: props.branchId })
    }

    return {
      triggersText,
      handleConfigure,
      handleViewDetails,
      handleClick
    }
  }
})
</script>

<style scoped>
.wf-viz-branch-card {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 16px;
  background: #ffffff;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  transition: all 0.2s ease;
  min-width: 280px;
  max-width: 400px;
}

.wf-viz-branch-card:hover {
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  border-color: #d1d5db;
}

.wf-viz-branch-card--fixed {
  border-left: 4px solid #3b82f6;
  background: #eff6ff;
}

.wf-viz-kind-badge {
  display: inline-flex;
  align-items: center;
  padding: 4px 8px;
  background: #dbeafe;
  color: #1e40af;
  font-size: 12px;
  font-weight: 500;
  border-radius: 4px;
  align-self: flex-start;
}

.wf-viz-kind-badge--sm {
  padding: 2px 6px;
  font-size: 11px;
}

.wf-viz-branch-title {
  font-size: 16px;
  font-weight: 600;
  color: #111827;
  line-height: 1.5;
}

.wf-viz-branch-triggers {
  font-size: 12px;
  color: #6b7280;
  line-height: 1.6;
  padding: 8px;
  background: #f9fafb;
  border-radius: 4px;
  border-left: 2px solid #e5e7eb;
}

.wf-viz-branch-actions {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px solid #e5e7eb;
}

.wf-viz-action-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  padding: 0;
  background: #ffffff;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s ease;
  color: #6b7280;
}

.wf-viz-action-btn:hover {
  background: #f3f4f6;
  border-color: #9ca3af;
  color: #374151;
}

.wf-viz-action-btn:active {
  background: #e5e7eb;
}
</style>
