<template>
  <div class="visual-editor">
    <div class="editor-layout">
      <!-- 上：标签预览区 -->
      <div class="preview-section">
        <h4 class="section-title"><i class="fa fa-file-text-o" aria-hidden="true"></i> 标签预览</h4>
        <div class="canvas-container">
          <canvas
            ref="labelCanvas"
            :width="canvasWidth"
            :height="canvasHeight"
            @click="handleCanvasClick"
            @mousemove="handleMouseMove"
            @mousedown="handleMouseDown"
            @mouseup="handleMouseUp"
            @mouseleave="handleMouseLeave"
          ></canvas>
        </div>
        <div class="canvas-instructions">
          <span><i class="fa fa-lightbulb-o" aria-hidden="true"></i> 点击字段进行编辑 · 拖拽调整位置</span>
        </div>
      </div>

      <!-- 下：字段属性面板 -->
      <div class="properties-section" v-if="selectedField">
        <h4 class="section-title"><i class="fa fa-cog" aria-hidden="true"></i> 字段属性</h4>
        
        <div class="property-row">
          <div class="property-group half">
            <label class="property-label">字段名</label>
            <input
              type="text"
              class="form-control"
              v-model="selectedField.label"
              @input="onFieldChange"
            />
          </div>
          <div class="property-group half">
            <label class="property-label">字段值</label>
            <input
              type="text"
              class="form-control"
              v-model="selectedField.value"
              @input="onFieldChange"
            />
          </div>
        </div>

        <div class="property-row">
          <div class="property-group">
            <label class="property-label">类型</label>
            <div class="type-buttons">
              <button
                :class="['type-btn', selectedField.type === 'fixed' ? 'active' : '']"
                @click="selectedField.type = 'fixed'; onFieldChange()"
              >固定</button>
              <button
                :class="['type-btn', selectedField.type === 'dynamic' ? 'active' : '']"
                @click="selectedField.type = 'dynamic'; onFieldChange()"
              >可变</button>
            </div>
          </div>
        </div>

        <div class="property-row">
          <div class="property-group">
            <button class="btn btn-danger" @click="deleteSelectedField">
              <i class="fa fa-trash-o" aria-hidden="true"></i> 删除
            </button>
          </div>
        </div>
      </div>

      <!-- 未选择字段时的提示 -->
      <div class="properties-section empty-state" v-else>
        <div class="empty-message">
          <span class="empty-icon"><i class="fa fa-hand-o-up" aria-hidden="true"></i></span>
          <p>点击上方标签中的字段进行编辑</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'LabelVisualEditor',
  props: {
    fields: {
      type: Array,
      default: () => []
    },
    grid: {
      type: Object,
      default: () => ({})
    },
    imageSize: {
      type: Object,
      default: () => ({ width: 900, height: 600 })
    }
  },
  data() {
    return {
      selectedField: null,
      selectedFieldId: null,
      canvasWidth: 900,
      canvasHeight: 600,
      scale: 1,
      isDragging: false,
      dragOffset: { x: 0, y: 0 },
      hoverFieldId: null,
      ctx: null
    }
  },
  watch: {
    fields: {
      handler(newVal) {
        console.log('fields watch triggered - new length:', newVal ? newVal.length : 0)
        this.$nextTick(() => {
          this.drawCanvas()
        })
      },
      deep: true,
      immediate: true
    },
    imageSize: {
      handler(newSize) {
        console.log('imageSize watch triggered:', newSize)
        this.canvasWidth = Math.min(newSize.width, 900)
        this.canvasHeight = Math.min(newSize.height, 600)
        this.scale = Math.min(900 / newSize.width, 600 / newSize.height, 1)
        this.$nextTick(() => {
          this.drawCanvas()
        })
      },
      immediate: true
    }
  },
  mounted() {
    console.log('LabelVisualEditor mounted - canvas ref:', this.$refs.labelCanvas)
    console.log('LabelVisualEditor mounted - canvas exists:', !!this.$refs.labelCanvas)
    if (this.$refs.labelCanvas) {
      this.ctx = this.$refs.labelCanvas.getContext('2d')
      console.log('LabelVisualEditor - ctx:', this.ctx)
    }
    console.log('LabelVisualEditor mounted - fields:', this.fields)
    console.log('LabelVisualEditor mounted - grid:', this.grid)
    console.log('LabelVisualEditor mounted - imageSize:', this.imageSize)
    this.drawCanvas()
  },
  methods: {
    drawCanvas() {
      if (!this.ctx) {
        console.error('Canvas context is null')
        return
      }
      console.log('drawCanvas - fields count:', this.fields ? this.fields.length : 0)

      // 清空画布
      this.ctx.clearRect(0, 0, this.canvasWidth, this.canvasHeight)

      // 绘制背景
      this.ctx.fillStyle = '#ffffff'
      this.ctx.fillRect(0, 0, this.canvasWidth, this.canvasHeight)

      // 绘制标签外边框
      this.ctx.strokeStyle = '#000000'
      this.ctx.lineWidth = 2
      this.ctx.strokeRect(0, 0, this.canvasWidth, this.canvasHeight)

      // 绘制网格线（如果有的话）
      if (this.grid && this.grid.horizontal_lines && this.grid.vertical_lines) {
        this.ctx.strokeStyle = '#000000'
        this.ctx.lineWidth = 1

        // 水平线
        this.grid.horizontal_lines.forEach(y => {
          const scaledY = y * this.scale
          this.ctx.beginPath()
          this.ctx.moveTo(0, scaledY)
          this.ctx.lineTo(this.canvasWidth, scaledY)
          this.ctx.stroke()
        })

        // 垂直线
        this.grid.vertical_lines.forEach(x => {
          const scaledX = x * this.scale
          this.ctx.beginPath()
          this.ctx.moveTo(scaledX, 0)
          this.ctx.lineTo(scaledX, this.canvasHeight)
          this.ctx.stroke()
        })
      }

      // 绘制字段
      this.fields.forEach(field => {
        this.drawField(field)
      })
    },

    drawField(field) {
      // 兼容 position 格式：{x, y, width, height} 或 {left, top, width, height}
      const posX = field.position.x !== undefined ? field.position.x : (field.position.left || 0)
      const posY = field.position.y !== undefined ? field.position.y : (field.position.top || 0)
      const width = field.position.width || 100
      const height = field.position.height || 30
      
      const x = posX * this.scale
      const y = posY * this.scale
      const fieldWidth = width * this.scale
      const fieldHeight = height * this.scale

      const isSelected = field.id === this.selectedFieldId
      const isHover = field.id === this.hoverFieldId

      // 字段背景色
      if (field.type === 'fixed') {
        this.ctx.fillStyle = isHover ? '#bbdefb' : '#e3f2fd'
      } else {
        this.ctx.fillStyle = isHover ? '#c8e6c9' : '#e8f5e9'
      }

      // 字段边框
      if (isSelected) {
        this.ctx.strokeStyle = '#ff9800'
        this.ctx.lineWidth = 3
      } else if (field.type === 'fixed') {
        this.ctx.strokeStyle = '#2196f3'
        this.ctx.lineWidth = 2
      } else {
        this.ctx.strokeStyle = '#4caf50'
        this.ctx.lineWidth = 2
      }

      // 绘制字段矩形
      this.ctx.fillRect(x, y, fieldWidth, fieldHeight)
      this.ctx.strokeRect(x, y, fieldWidth, fieldHeight)

      // 绘制字段文本（字体大小也按比例缩放）
      this.ctx.fillStyle = '#000000'
      const fontSize = Math.max(12, Math.min(16, 14 * this.scale))
      this.ctx.font = `bold ${fontSize}px Arial`
      
      // 显示值（可变字段用 X 占位）
      const displayValue = field.type === 'dynamic' && !field.value ? 'X' : (field.value || 'X')
      const text = `${field.label}: ${displayValue}`
      
      // 文本基线位置（也按比例缩放）
      const textY = y + Math.min(25, 20 * this.scale)
      const lineHeight = Math.max(16, 18 * this.scale)
      
      // 文本换行处理
      this.wrapText(text, x + 5, textY, fieldWidth - 10, lineHeight)
    },

    wrapText(text, x, y, maxWidth, lineHeight) {
      const words = text.split('')
      let line = ''
      let currentY = y

      for (let i = 0; i < words.length; i++) {
        const testLine = line + words[i]
        const metrics = this.ctx.measureText(testLine)
        
        if (metrics.width > maxWidth && i > 0) {
          this.ctx.fillText(line, x, currentY)
          line = words[i]
          currentY += lineHeight
        } else {
          line = testLine
        }
      }
      this.ctx.fillText(line, x, currentY)
    },

    getFieldAtPosition(mouseX, mouseY) {
      const rect = this.$refs.labelCanvas.getBoundingClientRect()
      const x = (mouseX - rect.left) * (this.canvasWidth / rect.width)
      const y = (mouseY - rect.top) * (this.canvasHeight / rect.height)

      // 从后往前查找（选中最上层的字段）
      for (let i = this.fields.length - 1; i >= 0; i--) {
        const field = this.fields[i]
        // 兼容 position 格式
        const posX = field.position.x !== undefined ? field.position.x : (field.position.left || 0)
        const posY = field.position.y !== undefined ? field.position.y : (field.position.top || 0)
        const fw = (field.position.width || 100) * this.scale
        const fh = (field.position.height || 30) * this.scale
        
        const fx = posX * this.scale
        const fy = posY * this.scale

        if (x >= fx && x <= fx + fw && y >= fy && y <= fy + fh) {
          return field
        }
      }
      return null
    },

    handleCanvasClick(e) {
      const field = this.getFieldAtPosition(e.clientX, e.clientY)
      
      if (field) {
        this.selectedField = field
        this.selectedFieldId = field.id
        this.$emit('field-selected', field)
        this.drawCanvas()
      } else {
        this.selectedField = null
        this.selectedFieldId = null
        this.drawCanvas()
      }
    },

    handleMouseMove(e) {
      const field = this.getFieldAtPosition(e.clientX, e.clientY)
      
      if (field && field.id !== this.hoverFieldId) {
        this.hoverFieldId = field ? field.id : null
        this.drawCanvas()
        
        // 设置鼠标样式
        this.$refs.labelCanvas.style.cursor = field ? 'pointer' : 'default'
      }

      // 拖拽中
      if (this.isDragging && this.selectedField) {
        const rect = this.$refs.labelCanvas.getBoundingClientRect()
        const x = (e.clientX - rect.left) * (this.canvasWidth / rect.width)
        const y = (e.clientY - rect.top) * (this.canvasHeight / rect.height)

        // 兼容 position 格式
        if (this.selectedField.position.x !== undefined) {
          this.selectedField.position.x = Math.max(0, Math.round((x - this.dragOffset.x) / this.scale))
          this.selectedField.position.y = Math.max(0, Math.round((y - this.dragOffset.y) / this.scale))
        } else {
          this.selectedField.position.left = Math.max(0, Math.round((x - this.dragOffset.x) / this.scale))
          this.selectedField.position.top = Math.max(0, Math.round((y - this.dragOffset.y) / this.scale))
        }
        
        this.drawCanvas()
      }
    },

    handleMouseDown(e) {
      const field = this.getFieldAtPosition(e.clientX, e.clientY)

      if (field) {
        this.selectedField = field
        this.selectedFieldId = field.id
        this.$emit('field-selected', field)

        const rect = this.$refs.labelCanvas.getBoundingClientRect()
        const x = (e.clientX - rect.left) * (this.canvasWidth / rect.width)
        const y = (e.clientY - rect.top) * (this.canvasHeight / rect.height)

        const posX = field.position.x !== undefined ? field.position.x : (field.position.left || 0)
        const posY = field.position.y !== undefined ? field.position.y : (field.position.top || 0)
        this.dragOffset.x = x - (posX * this.scale)
        this.dragOffset.y = y - (posY * this.scale)
        this.isDragging = true

        this.drawCanvas()
      }
    },

    handleMouseUp() {
      if (this.isDragging) {
        this.isDragging = false
        this.onFieldChange()
      }
    },

    handleMouseLeave() {
      this.hoverFieldId = null
      this.isDragging = false
      this.drawCanvas()
    },

    onFieldChange() {
      this.drawCanvas()
      this.$emit('field-change', this.selectedField)
      this.$emit('fields-update', this.fields)
    },

    deleteSelectedField() {
      if (!this.selectedField) return

      const index = this.fields.findIndex(f => f.id === this.selectedFieldId)
      if (index > -1) {
        this.fields.splice(index, 1)
        this.selectedField = null
        this.selectedFieldId = null
        this.drawCanvas()
        this.$emit('fields-update', this.fields)
      }
    },

    getFields() {
      return this.fields
    }
  }
}
</script>

<style scoped>
.visual-editor {
  width: 100%;
  height: 100%;
}

.editor-layout {
  display: flex;
  flex-direction: column;
  gap: 16px;
  height: 100%;
  min-height: 600px;
}

.preview-section {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: #fff;
  border-radius: 8px;
  padding: 16px;
}

.section-title {
  margin: 0 0 12px 0;
  font-size: 16px;
  font-weight: 600;
  color: #333;
}

.canvas-container {
  flex: 1;
  min-height: 350px;
  border: 2px solid #dee2e6;
  border-radius: 4px;
  overflow: hidden;
  background: #fafafa;
  display: flex;
  align-items: center;
  justify-content: center;
}

.canvas-container canvas {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
}

.canvas-instructions {
  margin-top: 8px;
  padding: 6px 12px;
  background: #e7f3ff;
  border-radius: 4px;
  text-align: center;
  font-size: 12px;
  color: #007bff;
}

.properties-section {
  background: #f8f9fa;
  border-radius: 8px;
  padding: 16px;
}

.property-row {
  display: flex;
  gap: 12px;
  margin-bottom: 12px;
}

.property-group {
  flex: 1;
}

.property-group.half {
  flex: 1;
}

.property-label {
  display: block;
  margin-bottom: 6px;
  font-size: 13px;
  font-weight: 500;
  color: #555;
}

.form-control {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid #ced4da;
  border-radius: 4px;
  font-size: 14px;
}

.form-control:focus {
  outline: none;
  border-color: #007bff;
}

.type-buttons {
  display: flex;
  gap: 8px;
}

.type-btn {
  flex: 1;
  padding: 8px 16px;
  border: 1px solid #ced4da;
  border-radius: 4px;
  background: #fff;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
}

.type-btn.active {
  background: #007bff;
  color: white;
  border-color: #007bff;
}

.btn {
  padding: 8px 16px;
  border: none;
  border-radius: 4px;
  font-size: 14px;
  cursor: pointer;
}

.btn-danger {
  background: #dc3545;
  color: white;
}

.btn-danger:hover {
  background: #c82333;
}

.empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 150px;
}

.empty-message {
  text-align: center;
  color: #6c757d;
}

.empty-icon {
  font-size: 48px;
  display: block;
  margin-bottom: 12px;
}

.empty-message p {
  margin: 0;
  font-size: 14px;
}
</style>
