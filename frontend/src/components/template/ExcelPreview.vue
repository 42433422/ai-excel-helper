<template>
  <div class="excel-preview">
    <div class="fake-excel">
      <div class="excel-toolbar">
        <span class="excel-title">发货单模板预览</span>
      </div>
      <div class="excel-container">
        <div class="excel-headers">
          <div class="row-num-header"></div>
          <div
            v-for="(col, index) in displayColumns"
            :key="'header-' + index"
            class="col-header"
          >
            {{ getColumnHeader(index) }}
          </div>
        </div>
        <div class="excel-body">
          <div
            v-for="(row, rowIndex) in displayRows"
            :key="'row-' + rowIndex"
            class="excel-row"
          >
            <div class="row-num">{{ rowIndex + 1 }}</div>
            <div
              v-for="(col, colIndex) in displayColumns"
              :key="'cell-' + rowIndex + '-' + colIndex"
              class="excel-cell"
              :class="{ 'has-content': getCellContent(rowIndex, colIndex) }"
            >
              <span v-if="getCellContent(rowIndex, colIndex)" class="cell-text">
                {{ getCellContent(rowIndex, colIndex) }}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'ExcelPreview',
  props: {
    fields: {
      type: Array,
      default: () => []
    },
    sampleRows: {
      type: Array,
      default: () => []
    },
    rows: {
      type: Number,
      default: 6
    },
    columns: {
      type: Number,
      default: 5
    }
  },
  computed: {
    displayRows() {
      if (this.sampleRows && this.sampleRows.length > 0) {
        return Math.max(this.rows, this.sampleRows.length)
      }
      return this.rows
    },
    displayColumns() {
      if (this.fields && this.fields.length > 0) {
        return Math.max(this.columns, this.fields.length)
      }
      return this.columns
    },
    columnHeaders() {
      if (this.fields && this.fields.length > 0) {
        return this.fields.map(f => f.label || f.name || '')
      }
      return []
    }
  },
  methods: {
    getColumnHeader(index) {
      if (this.columnHeaders && this.columnHeaders[index]) {
        return this.columnHeaders[index]
      }
      const letters = 'ABCDEFGHIJ'
      return letters[index] || ''
    },

    getCellContent(rowIndex, colIndex) {
      if (this.sampleRows && this.sampleRows[rowIndex]) {
        const row = this.sampleRows[rowIndex]
        const headers = this.columnHeaders
        if (headers && headers[colIndex]) {
          const key = headers[colIndex]
          return row[key] !== undefined ? row[key] : ''
        }
        const values = Object.values(row)
        return values[colIndex] !== undefined ? values[colIndex] : ''
      }

      if (rowIndex === 0) {
        return this.getColumnHeader(colIndex)
      }

      if (rowIndex >= 1 && this.fields && this.fields[colIndex]) {
        const field = this.fields[colIndex]
        return field.value || field.sample || `示例${colIndex + 1}`
      }

      return ''
    }
  }
}
</script>

<style scoped>
.excel-preview {
  width: 100%;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}

.fake-excel {
  border: 1px solid #d4d4d4;
  border-radius: 4px;
  overflow: hidden;
  background: white;
}

.excel-toolbar {
  background: #f5f5f5;
  padding: 8px 12px;
  border-bottom: 1px solid #d4d4d4;
  display: flex;
  align-items: center;
}

.excel-title {
  font-size: 12px;
  color: #666;
}

.excel-container {
  overflow-x: auto;
}

.excel-headers {
  display: flex;
  background: #f0f0f0;
  border-bottom: 2px solid #d4d4d4;
  min-width: fit-content;
}

.row-num-header {
  width: 40px;
  min-width: 40px;
  padding: 6px 8px;
  text-align: center;
  font-weight: 500;
  font-size: 12px;
  color: #666;
  border-right: 1px solid #d4d4d4;
  background: #f5f5f5;
}

.col-header {
  width: 100px;
  min-width: 100px;
  padding: 6px 8px;
  text-align: center;
  font-weight: 500;
  font-size: 12px;
  color: #333;
  border-right: 1px solid #d4d4d4;
}

.excel-body {
  min-width: fit-content;
}

.excel-row {
  display: flex;
  border-bottom: 1px solid #d4d4d4;
}

.excel-row:last-child {
  border-bottom: none;
}

.excel-row:hover {
  background: #f9f9f9;
}

.row-num {
  width: 40px;
  min-width: 40px;
  padding: 8px;
  text-align: center;
  font-size: 12px;
  color: #999;
  border-right: 1px solid #d4d4d4;
  background: #fafafa;
}

.excel-cell {
  width: 100px;
  min-width: 100px;
  height: 32px;
  padding: 4px 8px;
  border-right: 1px solid #d4d4d4;
  font-size: 12px;
  vertical-align: middle;
}

.excel-cell.has-content {
  background: white;
}

.cell-text {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
