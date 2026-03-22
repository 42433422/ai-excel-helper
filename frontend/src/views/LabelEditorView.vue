<template>
  <div class="label-editor-page">
    <div class="editor-header">
      <h2>🏷️ 标签模板编辑器</h2>
      <div class="header-actions">
        <button class="btn btn-secondary" @click="goBack">← 返回</button>
        <button class="btn btn-primary" @click="saveTemplate">💾 保存模板</button>
      </div>
    </div>

    <div class="editor-toolbar">
      <div class="toolbar-group">
        <label>缩放：</label>
        <input type="range" v-model="zoom" min="0.5" max="2" step="0.1" />
        <span>{{ Math.round(zoom * 100) }}%</span>
      </div>
      <div class="toolbar-group">
        <button class="btn btn-sm" :class="showGrid ? 'btn-primary' : 'btn-secondary'" @click="showGrid = !showGrid">
          📏 网格线
        </button>
        <button class="btn btn-sm" :class="showMerge ? 'btn-primary' : 'btn-secondary'" @click="showMerge = !showMerge">
          🔗 合并单元格
        </button>
      </div>
    </div>

    <div class="editor-content">
      <div class="canvas-wrapper" :style="{ transform: `scale(${zoom})` }">
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

      <div class="fields-panel">
        <div class="panel-header">
          <h3>📋 字段列表</h3>
          <button class="btn btn-sm btn-primary" @click="addField">➕ 添加字段</button>
        </div>

        <div class="fields-list">
          <div
            v-for="(field, index) in fields"
            :key="field.id"
            :class="['field-item', { selected: selectedFieldId === field.id }]"
            @click="selectField(field)"
          >
            <div class="field-info">
              <span class="field-label">{{ field.label }}</span>
              <span class="field-value">{{ field.value || '(空)' }}</span>
              <span class="field-type" :class="field.type">{{ field.type === 'fixed' ? '固定' : '可变' }}</span>
            </div>
            <div class="field-actions">
              <button class="btn-icon" @click.stop="deleteField(index)" title="删除">🗑️</button>
            </div>
          </div>
        </div>

        <div v-if="fields.length === 0" class="empty-fields">
          <p>暂无字段</p>
          <p class="hint">上传标签图片自动识别或手动添加</p>
        </div>

        <div class="panel-section" v-if="selectedField">
          <h4>⚙️ 选中字段属性</h4>

          <div class="property-form">
            <div class="form-group">
              <label>字段名</label>
              <input type="text" v-model="selectedField.label" @input="onFieldChange" />
            </div>
            <div class="form-group">
              <label>字段值</label>
              <input type="text" v-model="selectedField.value" @input="onFieldChange" />
            </div>
            <div class="form-group">
              <label>类型</label>
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
            <div class="form-group">
              <label>位置</label>
              <div class="position-inputs">
                <input type="number" v-model.number="selectedField.position.left" @input="onFieldChange" placeholder="X" />
                <input type="number" v-model.number="selectedField.position.top" @input="onFieldChange" placeholder="Y" />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div v-if="showUploadModal" class="modal-overlay" @click.self="showUploadModal = false">
      <div class="modal-content">
        <div class="modal-header">
          <h3>📤 上传标签图片</h3>
          <button class="modal-close" @click="showUploadModal = false">×</button>
        </div>
        <div class="modal-body">
          <div class="upload-area" @click="triggerFileInput">
            <input type="file" ref="fileInput" accept="image/*" @change="onFileSelected" hidden />
            <div class="upload-icon">📁</div>
            <p>点击选择图片或拖拽到此处</p>
            <p class="hint">支持 PNG、JPG 格式</p>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn btn-secondary" @click="showUploadModal = false">取消</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'LabelEditorView',
  data() {
    return {
      canvasWidth: 900,
      canvasHeight: 600,
      scale: 1,
      zoom: 1,
      fields: [],
      grid: null,
      imageSize: { width: 900, height: 600 },
      selectedField: null,
      selectedFieldId: null,
      isDragging: false,
      dragOffset: { x: 0, y: 0 },
      hoverFieldId: null,
      ctx: null,
      showGrid: true,
      showMerge: true,
      showUploadModal: false,
      uploadedImage: null
    }
  },
  mounted() {
    this.initCanvas()

    const gridData = this.$route.query.grid
    const fieldsData = this.$route.query.fields
    const imageData = this.$route.query.image

    if (gridData) {
      try {
        this.grid = JSON.parse(gridData)
      } catch (e) {
        console.error('解析网格数据失败:', e)
      }
    }

    if (fieldsData) {
      try {
        this.fields = JSON.parse(fieldsData)
      } catch (e) {
        console.error('解析字段数据失败:', e)
      }
    } else {
      this.fields = this.getDefaultFields()
    }

    if (imageData) {
      this.uploadedImage = imageData
    }

    this.drawCanvas()
  },
  watch: {
    fields: {
      handler() {
        this.drawCanvas()
      },
      deep: true
    },
    showGrid() {
      this.drawCanvas()
    },
    showMerge() {
      this.drawCanvas()
    },
    zoom() {
      this.drawCanvas()
    }
  },
  methods: {
    initCanvas() {
      if (this.$refs.labelCanvas) {
        this.ctx = this.$refs.labelCanvas.getContext('2d')
      }
    },

    getDefaultFields() {
      return [
        {
          id: 1,
          label: '产品名称',
          value: '示例产品',
          type: 'fixed',
          position: { left: 50, top: 50, width: 200, height: 30 }
        },
        {
          id: 2,
          label: '规格',
          value: 'XXX',
          type: 'dynamic',
          position: { left: 300, top: 50, width: 150, height: 30 }
        },
        {
          id: 3,
          label: '数量',
          value: '100',
          type: 'dynamic',
          position: { left: 500, top: 50, width: 100, height: 30 }
        },
        {
          id: 4,
          label: '日期',
          value: '2024-01-01',
          type: 'dynamic',
          position: { left: 50, top: 120, width: 200, height: 30 }
        }
      ]
    },

    drawCanvas() {
      if (!this.ctx) return

      this.ctx.clearRect(0, 0, this.canvasWidth, this.canvasHeight)

      if (this.uploadedImage) {
        const img = new Image()
        img.onload = () => {
          this.ctx.drawImage(img, 0, 0, this.canvasWidth, this.canvasHeight)
          this.drawGridOverlay()
          this.drawFields()
        }
        img.src = this.uploadedImage
      } else {
        this.ctx.fillStyle = '#ffffff'
        this.ctx.fillRect(0, 0, this.canvasWidth, this.canvasHeight)
        this.drawBorder()
        this.drawGridOverlay()
        this.drawFields()
      }
    },

    drawBorder() {
      this.ctx.strokeStyle = '#000000'
      this.ctx.lineWidth = 3
      this.ctx.strokeRect(0, 0, this.canvasWidth, this.canvasHeight)
    },

    drawGridOverlay() {
      if (!this.showGrid || !this.grid) return

      this.ctx.strokeStyle = '#cccccc'
      this.ctx.lineWidth = 1
      this.ctx.setLineDash([5, 5])

      if (this.grid.horizontal_lines) {
        this.grid.horizontal_lines.forEach(y => {
          this.ctx.beginPath()
          this.ctx.moveTo(0, y)
          this.ctx.lineTo(this.canvasWidth, y)
          this.ctx.stroke()
        })
      }

      if (this.grid.vertical_lines) {
        this.grid.vertical_lines.forEach(x => {
          this.ctx.beginPath()
          this.ctx.moveTo(x, 0)
          this.ctx.lineTo(x, this.canvasHeight)
          this.ctx.stroke()
        })
      }

      this.ctx.setLineDash([])
    },

    drawFields() {
      this.fields.forEach(field => {
        this.drawField(field)
      })
    },

    drawField(field) {
      const posX = field.position.left || 0
      const posY = field.position.top || 0
      const width = field.position.width || 100
      const height = field.position.height || 30

      const isSelected = field.id === this.selectedFieldId
      const isHover = field.id === this.hoverFieldId

      if (field.type === 'fixed') {
        this.ctx.fillStyle = isHover ? '#bbdefb' : '#e3f2fd'
      } else {
        this.ctx.fillStyle = isHover ? '#c8e6c9' : '#e8f5e9'
      }

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

      this.ctx.fillRect(posX, posY, width, height)
      this.ctx.strokeRect(posX, posY, width, height)

      this.ctx.fillStyle = '#000000'
      this.ctx.font = 'bold 14px Arial'
      const displayValue = field.type === 'dynamic' && !field.value ? 'X' : (field.value || 'X')
      const text = `${field.label}: ${displayValue}`
      this.ctx.fillText(text, posX + 5, posY + 20)
    },

    getFieldAtPosition(mouseX, mouseY) {
      for (let i = this.fields.length - 1; i >= 0; i--) {
        const field = this.fields[i]
        const posX = field.position.left || 0
        const posY = field.position.top || 0
        const width = field.position.width || 100
        const height = field.position.height || 30

        if (mouseX >= posX && mouseX <= posX + width &&
            mouseY >= posY && mouseY <= posY + height) {
          return field
        }
      }
      return null
    },

    handleCanvasClick(e) {
      const rect = this.$refs.labelCanvas.getBoundingClientRect()
      const x = e.clientX - rect.left
      const y = e.clientY - rect.top

      const field = this.getFieldAtPosition(x, y)

      if (field) {
        this.selectedField = field
        this.selectedFieldId = field.id
        this.drawCanvas()
      } else {
        this.selectedField = null
        this.selectedFieldId = null
        this.drawCanvas()
      }
    },

    handleMouseMove(e) {
      const rect = this.$refs.labelCanvas.getBoundingClientRect()
      const x = e.clientX - rect.left
      const y = e.clientY - rect.top

      const field = this.getFieldAtPosition(x, y)

      if (field && field.id !== this.hoverFieldId) {
        this.hoverFieldId = field ? field.id : null
        this.$refs.labelCanvas.style.cursor = field ? 'pointer' : 'default'
        this.drawCanvas()
      }

      if (this.isDragging && this.selectedField) {
        const newX = Math.max(0, Math.round(x - this.dragOffset.x))
        const newY = Math.max(0, Math.round(y - this.dragOffset.y))

        this.selectedField.position.left = newX
        this.selectedField.position.top = newY

        this.drawCanvas()
      }
    },

    handleMouseDown(e) {
      const rect = this.$refs.labelCanvas.getBoundingClientRect()
      const x = e.clientX - rect.left
      const y = e.clientY - rect.top

      const field = this.getFieldAtPosition(x, y)

      if (field) {
        this.selectedField = field
        this.selectedFieldId = field.id
        this.dragOffset.x = x - (field.position.left || 0)
        this.dragOffset.y = y - (field.position.top || 0)
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
    },

    selectField(field) {
      this.selectedField = field
      this.selectedFieldId = field.id
      this.drawCanvas()
    },

    addField() {
      const newId = Math.max(0, ...this.fields.map(f => f.id)) + 1
      this.fields.push({
        id: newId,
        label: '新字段',
        value: '',
        type: 'dynamic',
        position: { left: 50, top: 50 + newId * 40, width: 150, height: 30 }
      })
      this.drawCanvas()
    },

    deleteField(index) {
      const field = this.fields[index]
      if (field.id === this.selectedFieldId) {
        this.selectedField = null
        this.selectedFieldId = null
      }
      this.fields.splice(index, 1)
      this.drawCanvas()
    },

    triggerFileInput() {
      this.$refs.fileInput.click()
    },

    onFileSelected(e) {
      const file = e.target.files[0]
      if (file) {
        const reader = new FileReader()
        reader.onload = (event) => {
          this.uploadedImage = event.target.result
          this.showUploadModal = false
          this.drawCanvas()
        }
        reader.readAsDataURL(file)
      }
    },

    saveTemplate() {
      const templateData = {
        fields: this.fields,
        grid: this.grid,
        imageSize: this.imageSize
      }

      console.log('保存模板数据:', templateData)

      this.$emit('save', templateData)
      alert('模板保存成功！')
    },

    goBack() {
      this.$router.push('/template-preview')
    }
  }
}
</script>

<style scoped>
.label-editor-page {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: #f5f5f5;
}

.editor-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 24px;
  background: white;
  border-bottom: 1px solid #e0e0e0;
}

.editor-header h2 {
  margin: 0;
  font-size: 20px;
}

.header-actions {
  display: flex;
  gap: 12px;
}

.editor-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 24px;
  background: white;
  border-bottom: 1px solid #e0e0e0;
}

.toolbar-group {
  display: flex;
  align-items: center;
  gap: 12px;
}

.toolbar-group label {
  font-weight: 500;
}

.toolbar-group input[type="range"] {
  width: 120px;
}

.editor-content {
  display: flex;
  flex: 1;
  overflow: hidden;
}

.canvas-wrapper {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #e0e0e0;
  padding: 24px;
  overflow: auto;
  transform-origin: center center;
}

.canvas-wrapper canvas {
  background: white;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
  cursor: default;
}

.fields-panel {
  width: 350px;
  background: white;
  border-left: 1px solid #e0e0e0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  border-bottom: 1px solid #e0e0e0;
}

.panel-header h3 {
  margin: 0;
  font-size: 16px;
}

.fields-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.field-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px;
  margin-bottom: 8px;
  background: #f8f9fa;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
  border: 2px solid transparent;
}

.field-item:hover {
  background: #e9ecef;
}

.field-item.selected {
  border-color: #007bff;
  background: #e7f3ff;
}

.field-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.field-label {
  font-weight: 600;
  font-size: 14px;
}

.field-value {
  font-size: 12px;
  color: #666;
}

.field-type {
  font-size: 11px;
  padding: 2px 6px;
  border-radius: 4px;
  width: fit-content;
}

.field-type.fixed {
  background: #e3f2fd;
  color: #1976d2;
}

.field-type.dynamic {
  background: #e8f5e9;
  color: #388e3c;
}

.field-actions {
  display: flex;
  gap: 4px;
}

.btn-icon {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 16px;
  padding: 4px;
  opacity: 0.6;
}

.btn-icon:hover {
  opacity: 1;
}

.empty-fields {
  text-align: center;
  padding: 40px 20px;
  color: #999;
}

.empty-fields .hint {
  font-size: 12px;
  margin-top: 8px;
}

.panel-section {
  padding: 16px;
  border-top: 1px solid #e0e0e0;
  background: #fafafa;
}

.panel-section h4 {
  margin: 0 0 16px 0;
  font-size: 14px;
}

.property-form {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-group label {
  font-size: 12px;
  font-weight: 500;
  color: #666;
}

.form-group input[type="text"],
.form-group input[type="number"] {
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
}

.form-group input:focus {
  outline: none;
  border-color: #007bff;
}

.type-buttons {
  display: flex;
  gap: 8px;
}

.type-btn {
  flex: 1;
  padding: 8px;
  border: 1px solid #ddd;
  border-radius: 4px;
  background: white;
  cursor: pointer;
  font-size: 13px;
  transition: all 0.2s;
}

.type-btn.active {
  background: #007bff;
  color: white;
  border-color: #007bff;
}

.position-inputs {
  display: flex;
  gap: 8px;
}

.position-inputs input {
  flex: 1;
}

.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: white;
  border-radius: 12px;
  width: 500px;
  max-width: 90vw;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid #e0e0e0;
}

.modal-header h3 {
  margin: 0;
}

.modal-close {
  background: none;
  border: none;
  font-size: 24px;
  cursor: pointer;
  color: #999;
}

.modal-body {
  padding: 20px;
}

.upload-area {
  border: 2px dashed #ddd;
  border-radius: 12px;
  padding: 40px;
  text-align: center;
  cursor: pointer;
  transition: all 0.2s;
}

.upload-area:hover {
  border-color: #007bff;
  background: #f8f9ff;
}

.upload-icon {
  font-size: 48px;
  margin-bottom: 16px;
}

.upload-area p {
  margin: 8px 0;
}

.upload-area .hint {
  font-size: 12px;
  color: #999;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 16px 20px;
  border-top: 1px solid #e0e0e0;
}

.btn {
  padding: 10px 20px;
  border: none;
  border-radius: 6px;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-primary {
  background: #007bff;
  color: white;
}

.btn-primary:hover {
  background: #0056b3;
}

.btn-secondary {
  background: #6c757d;
  color: white;
}

.btn-secondary:hover {
  background: #5a6268;
}

.btn-sm {
  padding: 6px 12px;
  font-size: 13px;
}
</style>
