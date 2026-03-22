<template>
  <div class="page-view" id="view-template-preview">
    <div class="page-content">
      <div class="page-header">
        <h2>模板预览</h2>
        <p class="muted" style="margin:0;font-size:13px;">支持 Excel / 标签打印 双分类，可继续扩展新模板</p>
      </div>

      <div style="display:flex;gap:8px;align-items:center;margin:12px 0 16px;">
        <button type="button" class="btn btn-sm" :class="activeTab === 'all' ? 'btn-primary' : 'btn-secondary'" @click="activeTab = 'all'">全部</button>
        <button type="button" class="btn btn-sm" :class="activeTab === 'excel' ? 'btn-primary' : 'btn-secondary'" @click="activeTab = 'excel'">Excel</button>
        <button type="button" class="btn btn-sm" :class="activeTab === 'label' ? 'btn-primary' : 'btn-secondary'" @click="activeTab = 'label'">标签打印</button>
        <button type="button" class="btn btn-sm btn-secondary" @click="refreshTemplates">刷新</button>
        <button type="button" class="btn btn-sm btn-primary" @click="openLabelEditor">
          ➕ 创建模板
        </button>
      </div>

      <div v-if="loading" class="muted">模板加载中...</div>
      <div v-else-if="error" class="muted">{{ error }}</div>
      <div v-else-if="filteredTemplates.length === 0" class="muted">当前分类暂无模板</div>

      <div v-else class="template-preview-section">
        <div class="template-preview-grid">
          <div v-for="tpl in filteredTemplates" :key="tpl.id" class="template-preview-card" :data-template-id="tpl.id">
            <div class="template-preview-card-icon">{{ tpl.category === 'label' ? '🏷️' : '📋' }}</div>
            <div class="template-preview-card-title">{{ tpl.name }}</div>

            <div class="template-preview-preview">
              <ExcelPreview
                v-if="tpl.category === 'excel'"
                :fields="getTemplateFields(tpl, 'excel')"
                :sample-rows="getTemplateSampleRows(tpl)"
                :rows="6"
                :columns="6"
              />
              <LabelPreview v-else-if="tpl.category === 'label'" :fields="getTemplateFields(tpl, 'label')" />
            </div>

            <div class="template-preview-card-desc">
              <span>分类：{{ tpl.category === 'label' ? '标签打印' : 'Excel' }}</span>
              <br>
              <span>来源：{{ tpl.source || 'db' }}</span>
              <br v-if="tpl.template_type">
              <span v-if="tpl.template_type">类型：{{ tpl.template_type }}</span>
            </div>
            <div class="template-preview-actions">
              <button
                type="button"
                class="btn btn-primary btn-sm template-preview-action"
                :data-template-action="tpl.category === 'label' ? 'view-labels-export' : 'open-excel-preview'"
                :data-template-id="tpl.id"
                @click="previewTemplate(tpl)"
              >
                查看
              </button>
              <button
                type="button"
                class="btn btn-secondary btn-sm template-preview-action"
                :data-template-action="tpl.category === 'label' ? 'open-print' : 'open-excel-preview'"
                :data-template-id="tpl.id"
                @click="openTemplateTarget(tpl)"
              >
                打开
              </button>
              <button
                type="button"
                class="btn btn-info btn-sm template-preview-action"
                :data-template-id="tpl.id"
                @click="editTemplate(tpl)"
              >
                编辑
              </button>
              <button
                type="button"
                class="btn btn-danger btn-sm template-preview-action"
                :data-template-id="tpl.id"
                @click="confirmDeleteTemplate(tpl)"
              >
                删除
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div v-if="showCreateModal" class="modal-overlay" @click.self="closeCreateModal">
        <div class="modal-content" style="max-width:900px;">
          <div class="modal-header">
            <h3>📁 创建新模板</h3>
            <button type="button" class="modal-close" @click="closeCreateModal">&times;</button>
          </div>
          <div class="modal-body">
            <div v-if="createStep === 1" class="create-step">
              <FileUploadStep
                ref="uploadStep"
                :template-name="templateName"
                :selected-file="selectedFile"
                @update:template-name="templateName = $event"
                @update:selected-file="selectedFile = $event"
                @file-selected="onFileSelected"
              />
            </div>

            <div v-else-if="createStep === 2" class="create-step" style="min-height: 650px;">
              <!-- 标签模板使用可视化编辑器 -->
              <LabelVisualEditor
                v-if="editorTemplateType === 'label'"
                ref="visualEditor"
                :fields="editorFields"
                :grid="editorGrid"
                :image-size="labelImageSize"
                @field-change="onFieldChange"
                @fields-update="onFieldsUpdate"
              />
              <!-- Excel 模板使用字段编辑器 -->
              <FieldEditor
                v-else
                ref="fieldEditor"
                :fields="editorFields"
                :template-type="editorTemplateType"
                @update-field="onUpdateField"
                @delete-field="onDeleteField"
                @add-field="onAddField"
                @fields-change="onFieldsChange"
              />
            </div>
          </div>
          
          <!-- 分析进度条 -->
          <div v-if="analyzing" class="analyzing-progress">
            <div class="progress-info">
              <span>{{ progressMessage }}</span>
              <span>{{ progressPercent }}%</span>
            </div>
            <div class="progress-bar">
              <div class="progress-fill" :style="{ width: progressPercent + '%' }"></div>
            </div>
            <div class="progress-steps">
              <div :class="['step', { active: progressStep >= 1 }]">
                <span class="step-icon">📤</span>
                <span class="step-label">上传</span>
              </div>
              <div :class="['step', { active: progressStep >= 2 }]">
                <span class="step-icon">🔍</span>
                <span class="step-label">检测网格</span>
              </div>
              <div :class="['step', { active: progressStep >= 3 }]">
                <span class="step-icon">👁️</span>
                <span class="step-label">OCR 识别</span>
              </div>
              <div :class="['step', { active: progressStep >= 4 }]">
                <span class="step-icon">✅</span>
                <span class="step-label">完成</span>
              </div>
            </div>
          </div>
          
          <div class="modal-footer">
            <button v-if="createStep > 1" type="button" class="btn btn-secondary" @click="prevStep">← 上一步</button>
            <button type="button" class="btn btn-secondary" @click="closeCreateModal">取消</button>
            <button v-if="createStep === 1" type="button" class="btn btn-primary" @click="nextStep" :disabled="!canProceedStep1 || analyzing">
              <span v-if="analyzing">分析中...</span>
              <span v-else>下一步 →</span>
            </button>
            <button v-else-if="createStep === 2" type="button" class="btn btn-success" @click="saveTemplate">
              ✓ 保存模板
            </button>
          </div>
        </div>
      </div>

    <div v-if="showPreviewModal" class="modal-overlay" @click.self="closePreviewModal">
      <div class="modal-content" style="max-width:800px;">
        <div class="modal-header">
          <h3>📋 模板预览 - {{ previewingTemplate?.name }}</h3>
          <button type="button" class="modal-close" @click="closePreviewModal">&times;</button>
        </div>
        <div class="modal-body">
          <div class="preview-modal-content">
            <ExcelPreview
              v-if="previewingTemplate?.category === 'excel'"
              :fields="getTemplateFields(previewingTemplate, 'excel')"
              :sample-rows="getTemplateSampleRows(previewingTemplate)"
              :rows="8"
              :columns="6"
            />
            <LabelPreview v-else-if="previewingTemplate?.category === 'label'" :fields="getTemplateFields(previewingTemplate, 'label')" :width="400" :height="280" />
          </div>
        </div>
        <div class="modal-footer">
          <button type="button" class="btn btn-secondary" @click="closePreviewModal">关闭</button>
        </div>
      </div>
    </div>

    <div v-if="showEditModal" class="modal-overlay" @click.self="closeEditModal">
      <div class="modal-content">
        <div class="modal-header">
          <h3>编辑模板</h3>
          <button type="button" class="modal-close" @click="closeEditModal">&times;</button>
        </div>
        <div class="modal-body">
          <div class="form-group">
            <label>模板名称</label>
            <input type="text" v-model="editingTemplate.name" class="form-control" />
          </div>
          <div class="form-group">
            <label>分类</label>
            <select v-model="editingTemplate.category" class="form-control">
              <option value="excel">Excel</option>
              <option value="label">标签打印</option>
            </select>
          </div>
        </div>
        <div class="modal-footer">
          <button type="button" class="btn btn-secondary" @click="closeEditModal">取消</button>
          <button type="button" class="btn btn-primary" @click="saveTemplateEdit">保存</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import api from '../api'
import FileUploadStep from '../components/template/FileUploadStep.vue'
import FieldEditor from '../components/template/FieldEditor.vue'
import LabelVisualEditor from '../components/template/LabelVisualEditor.vue'
import ExcelPreview from '../components/template/ExcelPreview.vue'
import LabelPreview from '../components/template/LabelPreview.vue'

export default {
  name: 'TemplatePreviewView',
  components: {
    FileUploadStep,
    FieldEditor,
    LabelVisualEditor,
    ExcelPreview,
    LabelPreview
  },
  data() {
    return {
      activeTab: 'all',
      templates: [],
      loading: false,
      error: null,
      showCreateModal: false,
      createStep: 1,
      selectedFile: null,
      templateName: '',
      recognizedType: null,
      editorFields: [],
      editorTemplateType: 'excel',
      editorGrid: null,
      labelImageSize: { width: 900, height: 600 },
      showPreviewModal: false,
      previewingTemplate: null,
      showEditModal: false,
      editingTemplate: null,
      // 分析进度
      analyzing: false,
      progressStep: 1,
      progressPercent: 0,
      progressMessage: '准备上传...'
    }
  },
  computed: {
    filteredTemplates() {
      if (this.activeTab === 'all') return this.templates
      return this.templates.filter(t => t.category === this.activeTab)
    },
    canProceedStep1() {
      return this.selectedFile && this.templateName.trim()
    }
  },
  mounted() {
    this.refreshTemplates()
  },
  methods: {
    async refreshTemplates() {
      this.loading = true
      this.error = null
      try {
        const res = await api.get('/api/templates/list')
        if (res && res.success) {
          const templates = res.templates || []

          for (const tpl of templates) {
            if (tpl.category === 'excel' && !tpl.preview_data) {
              try {
                const detailRes = await api.get(`/api/templates/detail/${tpl.id}`)
                if (detailRes && detailRes.success && detailRes.template) {
                  Object.assign(tpl, detailRes.template)
                }
              } catch (e) {
                console.warn(`获取模板 ${tpl.id} 详情失败:`, e)
              }
            }
          }

          this.templates = templates
        } else {
          this.error = (res && res.message) || '加载失败'
        }
      } catch (err) {
        console.error('加载模板列表失败:', err)
        this.error = '加载模板列表失败：' + (err.message || '未知错误')
      } finally {
        this.loading = false
      }
    },

    onFileSelected(data) {
      this.selectedFile = data.selectedFile
      this.templateName = data.templateName
      this.recognizedType = data.recognizedType
    },

    closeCreateModal() {
      this.showCreateModal = false
      this.resetCreateState()
    },

    resetCreateState() {
      this.createStep = 1
      this.selectedFile = null
      this.templateName = ''
      this.recognizedType = null
      this.editorFields = []
      this.editorTemplateType = 'excel'
    },

    prevStep() {
      if (this.createStep > 1) {
        this.createStep--
      }
    },

    async nextStep() {
      console.log('nextStep 调用')
      console.log('createStep:', this.createStep)
      console.log('canProceedStep1:', this.canProceedStep1)
      console.log('selectedFile:', this.selectedFile)
      console.log('templateName:', this.templateName)
      
      if (this.createStep === 1 && this.canProceedStep1) {
        await this.analyzeFile()
        this.createStep = 2
      }
    },

    async analyzeFile() {
      try {
        console.log('分析文件 - selectedFile:', this.selectedFile)
        console.log('分析文件 - templateName:', this.templateName)
        
        if (!this.selectedFile) {
          console.error('没有选择文件！')
          alert('请先选择文件')
          return
        }
        
        // 开始分析，显示进度条
        this.analyzing = true
        this.progressStep = 1
        this.progressPercent = 0
        this.progressMessage = '准备上传文件...'
        
        const formData = new FormData()
        formData.append('file', this.selectedFile)
        formData.append('template_name', this.templateName)

        try {
          // 使用 fetch 上传
          const response = await fetch('/api/templates/analyze', {
            method: 'POST',
            body: formData
          })

          const res = await response.json()
          console.log('分析结果:', res)
          
          if (res && res.success) {
            console.log('分析成功 - template_type:', res.template_type)
            console.log('分析成功 - fields:', res.fields ? res.fields.length : 0, '个字段')
            console.log('分析成功 - preview_data:', res.preview_data ? '有数据' : '无数据')
            
            // 获取任务 ID，开始轮询真实进度
            const taskId = res.task_id
            console.log('开始轮询进度 - taskId:', taskId)
            
            if (taskId) {
              await this.pollProgress(taskId)
              console.log('轮询完成')
            }
            
            // 设置字段和类型
            this.editorFields = res.fields || []
            this.editorTemplateType = res.template_type === 'label' ? 'label' : 'excel'
            console.log('设置 editorTemplateType:', this.editorTemplateType)
            console.log('设置 editorFields:', this.editorFields.length, '个')
            
            // 如果是标签模板，提取网格信息
            if (res.template_type === 'label' && res.preview_data) {
              this.editorGrid = res.preview_data.grid || null
              console.log('设置 editorGrid:', this.editorGrid ? '有网格数据' : '无网格数据')
              if (res.preview_data.image_size) {
                this.labelImageSize = res.preview_data.image_size
                console.log('设置 labelImageSize:', this.labelImageSize)
              }
            }
            
            // 延迟一点再进入下一步，让用户看到完成状态
            await new Promise(resolve => setTimeout(resolve, 300))
          } else {
            console.warn('分析失败，使用默认字段')
            alert(res.message || '分析失败')
            this.editorFields = this.getDefaultFields(this.recognizedType)
            this.editorTemplateType = this.recognizedType || 'excel'
          }
        } catch (fetchErr) {
          throw fetchErr
        }
      } catch (err) {
        console.error('分析文件失败:', err)
        this.analyzing = false
        alert('分析失败：' + err.message)
        this.editorFields = this.getDefaultFields(this.recognizedType)
        this.editorTemplateType = this.recognizedType || 'excel'
      }
    },
    
    async pollProgress(taskId) {
      return new Promise((resolve) => {
        const pollInterval = setInterval(async () => {
          try {
            const response = await fetch(`/api/templates/progress/${taskId}`)
            const data = await response.json()
            
            if (data.success) {
              this.progressPercent = data.progress
              this.progressStep = data.step
              this.progressMessage = data.message || '分析中...'
              
              if (data.completed) {
                clearInterval(pollInterval)
                this.analyzing = false
                resolve()
              }
            }
          } catch (err) {
            console.error('轮询进度失败:', err)
          }
        }, 1000) // 每秒轮询一次
        
        this.progressTimer = pollInterval
      })
    },

    getDefaultFields(type) {
      if (type === 'label') {
        return [
          { label: '品名', value: '示例产品', type: 'fixed' },
          { label: '货号', value: '00000', type: 'dynamic' },
          { label: '颜色', value: '黑色', type: 'dynamic' },
          { label: '码段', value: '00000', type: 'dynamic' },
          { label: '等级', value: '合格品', type: 'fixed' },
          { label: '执行标准', value: 'QB/Txxxx-xxxx', type: 'fixed' },
          { label: '统一零售价', value: '¥0', type: 'dynamic' }
        ]
      }
      return [
        { label: '序号', value: '1', type: 'fixed' },
        { label: '品名', value: '示例产品', type: 'dynamic' },
        { label: '货号', value: '00000', type: 'dynamic' },
        { label: '数量', value: '10', type: 'dynamic' },
        { label: '单价', value: '¥0', type: 'dynamic' }
      ]
    },

    onUpdateField(index, field) {
      this.editorFields.splice(index, 1, field)
    },

    onDeleteField(index) {
      this.editorFields.splice(index, 1)
    },

    onAddField(field) {
      this.editorFields.push(field)
    },

    onFieldsChange(fields) {
      this.editorFields = [...fields]
    },
    
    onFieldChange(field) {
      console.log('字段变化:', field)
    },
    
    onFieldsUpdate(fields) {
      console.log('字段批量更新:', fields)
      this.editorFields = fields
    },

    async saveTemplate() {
      try {
        // 从可视化编辑器获取最新字段
        let fields = this.editorFields
        if (this.editorTemplateType === 'label' && this.$refs.visualEditor) {
          fields = this.$refs.visualEditor.getFields()
        }
        
        const saveData = {
          name: this.templateName,
          category: this.editorTemplateType,
          template_type: this.editorTemplateType === 'label' ? '标签' : '发货单',
          fields: fields,
          source: 'generated'
        }

        const res = await api.post('/api/templates/create', saveData)

        if (res && res.success) {
          alert('模板保存成功！')
          this.closeCreateModal()
          this.refreshTemplates()
        } else {
          throw new Error((res && res.message) || '保存失败')
        }
      } catch (err) {
        alert('保存失败：' + (err.message || '未知错误'))
      }
    },

    previewTemplate(tpl) {
      this.previewingTemplate = tpl
      this.showPreviewModal = true
    },

    closePreviewModal() {
      this.showPreviewModal = false
      this.previewingTemplate = null
    },

    openTemplateTarget(tpl) {
      if (tpl.category === 'label') {
        alert('打印功能开发中...')
      } else {
        alert('打开 Excel 功能开发中...')
      }
    },

    editTemplate(tpl) {
      this.editingTemplate = { ...tpl }
      this.showEditModal = true
    },

    closeEditModal() {
      this.showEditModal = false
      this.editingTemplate = null
    },

    async saveTemplateEdit() {
      if (!this.editingTemplate) return

      try {
        const res = await api.post('/api/templates/update', {
          id: this.editingTemplate.id,
          name: this.editingTemplate.name,
          category: this.editingTemplate.category
        })

        if (res && res.success) {
          alert('更新成功！')
          this.closeEditModal()
          this.refreshTemplates()
        } else {
          throw new Error((res && res.message) || '更新失败')
        }
      } catch (err) {
        alert('更新失败：' + (err.message || '未知错误'))
      }
    },

    openLabelEditor() {
      this.$router.push('/label-editor')
    },

    confirmDeleteTemplate(tpl) {
      if (confirm(`确定要删除模板 "${tpl.name}" 吗？`)) {
        this.deleteTemplate(tpl)
      }
    },

    async deleteTemplate(tpl) {
      try {
        const res = await api.post('/api/templates/delete', { id: tpl.id })

        if (res && res.success) {
          alert('删除成功！')
          this.refreshTemplates()
        } else {
          throw new Error((res && res.message) || '删除失败')
        }
      } catch (err) {
        alert('删除失败：' + (err.message || '未知错误'))
      }
    },

    getTemplateFields(tpl, type) {
      if (tpl.fields && tpl.fields.length > 0) {
        return tpl.fields
      }

      if (type === 'label') {
        return [
          { label: '品名', value: 'XX运动鞋', type: 'fixed' },
          { label: '货号', value: '1635', type: 'dynamic' },
          { label: '颜色', value: '白色', type: 'dynamic' },
          { label: '码段', value: '00001', type: 'dynamic' },
          { label: '等级', value: '合格品', type: 'fixed' },
          { label: '统一零售价', value: '¥199', type: 'dynamic' }
        ]
      }

      return [
        { label: '产品型号', value: '' },
        { label: '产品名称', value: '' },
        { label: '数量', value: '' },
        { label: '单价', value: '' },
        { label: '金额', value: '' }
      ]
    },

    getTemplateSampleRows(tpl) {
      if (tpl.preview_data && tpl.preview_data.sample_rows) {
        return tpl.preview_data.sample_rows
      }
      return []
    },
  }
}
</script>

<style scoped>
.template-preview-section {
  margin-top: 10px;
}

.template-preview-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 20px;
}

.template-preview-card {
  background: white;
  border: 1px solid #e1e4e8;
  border-radius: 8px;
  padding: 16px;
  transition: all 0.2s;
}

.template-preview-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  border-color: #42b983;
}

.template-preview-card-icon {
  font-size: 28px;
  margin-bottom: 8px;
}

.template-preview-card-title {
  font-size: 16px;
  font-weight: 600;
  color: #2c3e50;
  margin-bottom: 12px;
}

.template-preview-preview {
  background: #f8f9fa;
  border-radius: 4px;
  padding: 8px;
  margin-bottom: 12px;
  min-height: 120px;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

.template-preview-card-desc {
  font-size: 12px;
  color: #6c757d;
  margin-bottom: 12px;
  line-height: 1.5;
}

.template-preview-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
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
  border-radius: 8px;
  max-height: 90vh;
  overflow-y: auto;
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
  max-height: 60vh;
  overflow-y: auto;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding: 15px 20px;
  border-top: 1px solid #e1e4e8;
}

.create-step {
  min-height: 300px;
}

.preview-modal-content {
  background: #f8f9fa;
  border-radius: 8px;
  padding: 20px;
  display: flex;
  justify-content: center;
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

.btn {
  padding: 8px 16px;
  border: none;
  border-radius: 4px;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-sm {
  padding: 6px 12px;
  font-size: 13px;
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

.btn-primary:disabled {
  background: #a8d5c2;
  cursor: not-allowed;
}

.btn-success {
  background: #28a745;
  color: white;
}

.btn-success:hover {
  background: #218838;
}

.btn-danger {
  background: #dc3545;
  color: white;
}

.btn-danger:hover {
  background: #c82333;
}

.btn-info {
  background: #17a2b8;
  color: white;
}

.btn-info:hover {
  background: #138496;
}

.muted {
  color: #6c757d;
}

.analyzing-progress {
  margin-top: 16px;
  padding: 20px;
  background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
  border-radius: 8px;
  border: 1px solid #dee2e6;
}

.progress-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  font-size: 14px;
  color: #495057;
  font-weight: 500;
}

.progress-bar {
  width: 100%;
  height: 20px;
  background: #e9ecef;
  border-radius: 10px;
  overflow: hidden;
  margin-bottom: 20px;
  box-shadow: inset 0 1px 2px rgba(0,0,0,0.1);
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #007bff 0%, #0056b3 100%);
  transition: width 0.3s ease;
  border-radius: 10px;
  position: relative;
  overflow: hidden;
}

.progress-fill::after {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  bottom: 0;
  right: 0;
  background: linear-gradient(
    90deg,
    rgba(255,255,255,0) 0%,
    rgba(255,255,255,0.3) 50%,
    rgba(255,255,255,0) 100%
  );
  animation: shimmer 1.5s infinite;
}

@keyframes shimmer {
  0% { transform: translateX(-100%); }
  100% { transform: translateX(100%); }
}

.progress-steps {
  display: flex;
  justify-content: space-between;
  gap: 10px;
}

.progress-steps .step {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 12px 8px;
  background: #fff;
  border-radius: 8px;
  border: 2px solid #dee2e6;
  transition: all 0.3s ease;
  opacity: 0.6;
}

.progress-steps .step.active {
  border-color: #007bff;
  background: #e7f3ff;
  opacity: 1;
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(0,123,255,0.2);
}

.step-icon {
  font-size: 24px;
  margin-bottom: 6px;
}

.step-label {
  font-size: 12px;
  color: #6c757d;
  font-weight: 500;
}

.step.active .step-label {
  color: #007bff;
  font-weight: 600;
}
</style>
