<template>
  <div class="field-editor">
    <div class="editor-layout">
      <div class="preview-section">
        <h4 style="margin-top:0;">📋 预览</h4>
        <div class="preview-container">
          <ExcelPreview v-if="templateType === 'excel'" :fields="fields" />
          <LabelPreview v-else-if="templateType === 'label'" :fields="fields" />
        </div>
      </div>

      <div class="fields-section">
        <h4 style="margin-top:0;">📝 字段列表</h4>

        <div class="fields-list">
          <div
            v-for="(field, index) in fields"
            :key="index"
            class="field-item"
            :class="{ 'active': editingIndex === index }"
            @click="selectField(index)"
          >
            <div class="field-main">
              <div class="field-label-input">
                <input
                  type="text"
                  v-model="field.label"
                  class="form-control-sm"
                  placeholder="字段名"
                  @click.stop
                  @change="onFieldChange"
                />
                <span class="separator">：</span>
                <input
                  type="text"
                  v-model="field.value"
                  class="form-control-sm value-input"
                  placeholder="示例值"
                  @click.stop
                  @change="onFieldChange"
                />
              </div>
            </div>

            <div class="field-actions">
              <span
                class="type-badge"
                :class="field.type === 'fixed' ? 'badge-fixed' : 'badge-dynamic'"
                @click.stop="toggleType(index)"
                title="点击切换类型"
              >
                {{ field.type === 'fixed' ? '固定' : '可变' }}
              </span>
              <button
                type="button"
                class="btn-icon"
                @click.stop="editField(index)"
                title="编辑"
              >
                ✏️
              </button>
              <button
                type="button"
                class="btn-icon btn-danger"
                @click.stop="deleteField(index)"
                title="删除"
              >
                🗑️
              </button>
            </div>
          </div>

          <div v-if="fields.length === 0" class="empty-fields">
            暂无字段，请添加或上传文件自动识别
          </div>
        </div>

        <div class="add-field-actions">
          <button type="button" class="btn btn-secondary btn-sm" @click="addField">
            ➕ 添加字段
          </button>
        </div>
      </div>
    </div>

    <div v-if="editingField" class="field-edit-modal">
      <div class="modal-overlay" @click.self="closeEditModal"></div>
      <div class="modal-content">
        <div class="modal-header">
          <h3>编辑字段</h3>
          <button type="button" class="modal-close" @click="closeEditModal">&times;</button>
        </div>
        <div class="modal-body">
          <div class="form-group">
            <label>字段标签</label>
            <input
              type="text"
              v-model="editingField.label"
              class="form-control"
              placeholder="例如：品名"
            />
          </div>
          <div class="form-group">
            <label>示例值</label>
            <input
              type="text"
              v-model="editingField.value"
              class="form-control"
              placeholder="例如：运动鞋"
            />
          </div>
          <div class="form-group">
            <label>字段类型</label>
            <div class="type-radio-group">
              <label class="radio-label">
                <input type="radio" v-model="editingField.type" value="fixed" />
                <span class="radio-text">固定词条</span>
                <span class="radio-desc">标签上的标识文字，不可编辑</span>
              </label>
              <label class="radio-label">
                <input type="radio" v-model="editingField.type" value="dynamic" />
                <span class="radio-text">可变词条</span>
                <span class="radio-desc">对应的值，可以修改</span>
              </label>
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button type="button" class="btn btn-secondary" @click="closeEditModal">取消</button>
          <button type="button" class="btn btn-primary" @click="saveFieldEdit">保存</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import ExcelPreview from './ExcelPreview.vue'
import LabelPreview from './LabelPreview.vue'

export default {
  name: 'FieldEditor',
  components: {
    ExcelPreview,
    LabelPreview
  },
  props: {
    fields: {
      type: Array,
      default: () => []
    },
    templateType: {
      type: String,
      default: 'excel'
    }
  },
  data() {
    return {
      editingIndex: null,
      editingField: null
    }
  },
  methods: {
    selectField(index) {
      this.editingIndex = index
    },

    editField(index) {
      this.editingIndex = index
      this.editingField = { ...this.fields[index] }
    },

    closeEditModal() {
      this.editingField = null
    },

    saveFieldEdit() {
      if (this.editingIndex !== null && this.editingField) {
        this.$emit('update-field', this.editingIndex, { ...this.editingField })
        this.closeEditModal()
      }
    },

    toggleType(index) {
      const field = this.fields[index]
      const newType = field.type === 'fixed' ? 'dynamic' : 'fixed'
      this.$emit('update-field', index, { ...field, type: newType })
    },

    deleteField(index) {
      if (confirm('确定要删除这个字段吗？')) {
        this.$emit('delete-field', index)
        if (this.editingIndex === index) {
          this.editingIndex = null
        }
      }
    },

    addField() {
      this.$emit('add-field', {
        label: '新字段',
        value: '示例值',
        type: 'dynamic'
      })
    },

    onFieldChange() {
      this.$emit('fields-change', [...this.fields])
    },

    getFields() {
      return [...this.fields]
    }
  }
}
</script>

<style scoped>
.field-editor {
  width: 100%;
}

.editor-layout {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
  min-height: 350px;
}

.preview-section {
  background: #f8f9fa;
  border-radius: 8px;
  padding: 15px;
}

.preview-container {
  background: white;
  border-radius: 4px;
  padding: 10px;
  min-height: 280px;
  overflow: auto;
}

.fields-section {
  display: flex;
  flex-direction: column;
}

.fields-list {
  flex: 1;
  max-height: 280px;
  overflow-y: auto;
  background: #f8f9fa;
  border-radius: 4px;
  padding: 10px;
}

.field-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 10px;
  margin-bottom: 6px;
  background: white;
  border: 1px solid #e1e4e8;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s;
}

.field-item:hover {
  border-color: #42b983;
  background: #f0f7ff;
}

.field-item.active {
  border-color: #42b983;
  background: #e8f5e9;
}

.field-main {
  flex: 1;
}

.field-label-input {
  display: flex;
  align-items: center;
  gap: 4px;
}

.form-control-sm {
  padding: 4px 8px;
  border: 1px solid #ddd;
  border-radius: 3px;
  font-size: 12px;
  width: 80px;
}

.form-control-sm:focus {
  outline: none;
  border-color: #42b983;
}

.value-input {
  width: 100px;
}

.separator {
  color: #6c757d;
  font-weight: 500;
}

.field-actions {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-left: 10px;
}

.type-badge {
  padding: 2px 6px;
  border-radius: 3px;
  font-size: 10px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.badge-fixed {
  background: #fff3cd;
  color: #856404;
}

.badge-dynamic {
  background: #cce5ff;
  color: #004085;
}

.type-badge:hover {
  opacity: 0.8;
}

.btn-icon {
  background: none;
  border: none;
  cursor: pointer;
  padding: 2px 4px;
  font-size: 14px;
  opacity: 0.6;
  transition: opacity 0.2s;
}

.btn-icon:hover {
  opacity: 1;
}

.btn-icon.btn-danger:hover {
  color: #dc3545;
}

.empty-fields {
  text-align: center;
  padding: 40px;
  color: #6c757d;
}

.add-field-actions {
  margin-top: 10px;
}

.field-edit-modal {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
}

.modal-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
}

.modal-content {
  position: relative;
  background: white;
  border-radius: 8px;
  width: 400px;
  max-width: 90%;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 15px 20px;
  border-bottom: 1px solid #e1e4e8;
}

.modal-header h3 {
  margin: 0;
  font-size: 18px;
}

.modal-close {
  background: none;
  border: none;
  font-size: 24px;
  cursor: pointer;
  color: #6c757d;
}

.modal-close:hover {
  color: #343a40;
}

.modal-body {
  padding: 20px;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding: 15px 20px;
  border-top: 1px solid #e1e4e8;
}

.form-group {
  margin-bottom: 15px;
}

.form-group label {
  display: block;
  font-weight: 500;
  margin-bottom: 6px;
  color: #2c3e50;
}

.form-control {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
}

.form-control:focus {
  outline: none;
  border-color: #42b983;
  box-shadow: 0 0 0 2px rgba(66, 185, 131, 0.2);
}

.type-radio-group {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.radio-label {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 10px;
  background: #f8f9fa;
  border-radius: 4px;
  cursor: pointer;
}

.radio-label:hover {
  background: #e9ecef;
}

.radio-label input[type="radio"] {
  margin-top: 4px;
}

.radio-text {
  font-weight: 500;
}

.radio-desc {
  display: block;
  font-size: 12px;
  color: #6c757d;
  margin-top: 2px;
}

.btn {
  padding: 8px 16px;
  border: none;
  border-radius: 4px;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-secondary {
  background: #6c757d;
  color: white;
}

.btn-secondary:hover {
  background: #5a6268;
}

.btn-primary {
  background: #42b983;
  color: white;
}

.btn-primary:hover {
  background: #359469;
}
</style>
