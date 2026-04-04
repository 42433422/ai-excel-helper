<template>
  <div class="data-table-wrapper" ref="tableWrapper" @scroll="handleScroll">
    <table class="data-table">
      <thead>
        <tr>
          <th v-if="selectable">
            <input type="checkbox" v-model="localSelectAll" @change.stop="handleSelectAll">
          </th>
          <th v-for="col in columns" :key="col.key">{{ col.label }}</th>
          <th v-if="$slots.actions">操作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-if="loading && localData.length === 0">
          <td :colspan="totalColumns" class="empty-state">加载中...</td>
        </tr>
        <tr v-else-if="localData.length === 0 && !loading">
          <td :colspan="totalColumns" class="empty-state">{{ emptyText }}</td>
        </tr>
        <template v-else>
          <tr v-for="(row, index) in localData" :key="getRowKey(row, index)">
            <td v-if="selectable">
              <input
                type="checkbox"
                :value="getRowId(row)"
                v-model="localSelectedIds"
                @click.stop
                @change="handleCheckboxChange(row, $event)"
              >
            </td>
            <td v-for="col in columns" :key="col.key">
              <slot :name="`cell-${col.key}`" :row="row" :value="getCellValue(row, col)">
                {{ formatCell(row, col) }}
              </slot>
            </td>
            <td v-if="$slots.actions" class="data-table-actions-cell">
              <div class="data-table-actions-inner">
                <slot name="actions" :row="row" :index="index"></slot>
              </div>
            </td>
          </tr>
        </template>
        <tr v-if="loading && localData.length > 0">
          <td :colspan="totalColumns" class="loading-state">加载中...</td>
        </tr>
        <tr v-if="hasMore && !loading && localData.length > 0">
          <td :colspan="totalColumns" class="has-more-tip">滚动加载更多</td>
        </tr>
        <tr v-if="!hasMore && localData.length > 0">
          <td :colspan="totalColumns" class="no-more-tip">没有更多数据了</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick, useSlots } from 'vue'

const props = defineProps({
  columns: {
    type: Array,
    required: true
  },
  data: {
    type: Array,
    default: () => []
  },
  loading: {
    type: Boolean,
    default: false
  },
  selectable: {
    type: Boolean,
    default: false
  },
  selectedIds: {
    type: Array,
    default: () => []
  },
  rowKey: {
    type: String,
    default: 'id'
  },
  emptyText: {
    type: String,
    default: '暂无数据'
  },
  hasMore: {
    type: Boolean,
    default: true
  },
  height: {
    type: String,
    default: '500px'
  }
})

const emit = defineEmits([
  'update:selectedIds',
  'select-change',
  'row-click',
  'load-more'
])

const tableWrapper = ref(null)
const slots = useSlots()

const handleScroll = () => {
  if (!tableWrapper.value || props.loading || !props.hasMore) return
  
  const { scrollTop, scrollHeight, clientHeight } = tableWrapper.value
  const threshold = 100
  
  if (scrollHeight - scrollTop - clientHeight < threshold) {
    emit('load-more')
  }
}

watch(() => props.data, () => {
}, { deep: true })

const localSelectedIds = ref([...props.selectedIds])
const localSelectAll = ref(false)
let isSyncing = false

const totalColumns = computed(() => {
  let count = props.columns.length
  if (props.selectable) count++
  if (slots.actions) count++
  return count
})

const localData = computed(() => props.data)

watch(localSelectedIds, (newVal) => {
  if (isSyncing) return
  isSyncing = true
  emit('update:selectedIds', [...newVal])
  emit('select-change', [...newVal])
  nextTick(() => { isSyncing = false })
}, { deep: true })

watch(() => props.selectedIds, (newVal) => {
  if (isSyncing) return
  isSyncing = true
  localSelectedIds.value = [...newVal]
  nextTick(() => { isSyncing = false })
}, { deep: true })

const getRowId = (row) => {
  return row.id ?? row[props.rowKey] ?? row
}

const getRowKey = (row, index) => {
  return row[props.rowKey] ?? row.id ?? index
}

const getCellValue = (row, col) => {
  if (col.key.includes('.')) {
    return col.key.split('.').reduce((obj, key) => obj?.[key], row)
  }
  return row[col.key]
}

const formatCell = (row, col) => {
  const value = getCellValue(row, col)
  if (value === null || value === undefined) return col.default ?? '-'
  return value
}

const handleSelectAll = () => {
  if (localSelectAll.value) {
    localSelectedIds.value = localData.value.map((row, index) => getRowId(row))
  } else {
    localSelectedIds.value = []
  }
}

const handleCheckboxChange = (row, event) => {
  console.log('[DataTable] checkbox changed:', getRowId(row), event.target.checked)
}

const handleRowClick = (row, index) => {
  emit('row-click', { row, index })
}

defineExpose({
  clearSelection: () => {
    localSelectedIds.value = []
    localSelectAll.value = false
  },
  selectAll: () => {
    localSelectAll.value = true
    localSelectedIds.value = localData.value.map((row, index) => getRowId(row))
  }
})
</script>

<style scoped>
.data-table-wrapper {
  overflow-y: auto;
  overflow-x: auto;
  max-height: v-bind(height);
  border: 1px solid #e0e0e0;
  border-radius: 4px;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
}

.data-table th,
.data-table td {
  padding: 10px 12px;
  text-align: left;
  border-bottom: 1px solid #e0e0e0;
}

/* 不使用 sticky 表头：粘性 th 叠在数据行上会拦截操作列点击（pointer-events 在部分环境下仍不可靠） */
.data-table th {
  background-color: #f8f9fa;
  font-weight: 600;
  color: #333;
}

.data-table-actions-cell {
  position: relative;
  z-index: 2;
  white-space: nowrap;
  vertical-align: middle;
}

.data-table-actions-inner {
  position: relative;
  z-index: 2;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.data-table-actions-inner :deep(.btn) {
  position: relative;
  z-index: 3;
}

.data-table tbody tr:hover {
  background-color: #f5f5f5;
}

.empty-state {
  text-align: center;
  color: #999;
  padding: 40px !important;
}

.loading-state,
.has-more-tip,
.no-more-tip {
  text-align: center;
  color: #999;
  font-size: 14px;
  padding: 12px !important;
}

.has-more-tip {
  color: #666;
}

.no-more-tip {
  color: #ccc;
}
</style>
