<template>
  <div class="file-upload-step">
    <div class="form-group">
      <label>模板名称 <span style="color:red">*</span></label>
      <input
        type="text"
        v-model="localTemplateName"
        class="form-control"
        placeholder="例如：运动鞋标签、出货单模板"
        @input="onTemplateNameChange"
      />
      <div class="muted" style="font-size:12px;margin-top:5px;">
        用于区分不同模板，必填
      </div>
    </div>

    <div class="form-group">
      <label>上传文件</label>
      <div
        class="upload-area"
        :class="{ 'has-file': localSelectedFile, 'dragover': isDragover }"
        @dragover.prevent="isDragover = true"
        @dragleave.prevent="isDragover = false"
        @drop.prevent="handleDrop"
        @click="triggerFileInput"
      >
        <input
          ref="fileInput"
          type="file"
          accept=".xlsx,.xls,.png,.jpg,.jpeg,.gif,.bmp"
          style="display:none"
          @change="handleFileSelect"
        />

        <div v-if="!localSelectedFile" class="upload-placeholder">
          <div style="font-size:48px;margin-bottom:10px;">📁</div>
          <div>点击或拖拽上传文件</div>
          <div class="muted" style="font-size:12px;margin-top:5px;">
            支持 Excel (.xlsx, .xls) 或图片 (.png, .jpg, .jpeg)
          </div>
        </div>

        <div v-else class="file-info">
          <div style="font-size:36px;margin-bottom:10px;">{{ getFileIcon() }}</div>
          <div style="font-weight:500;">{{ localSelectedFile.name }}</div>
          <div class="muted" style="font-size:12px;margin-top:5px;">
            {{ formatFileSize(localSelectedFile.size) }}
          </div>
          <button
            type="button"
            class="btn btn-sm btn-danger"
            style="margin-top:10px;"
            @click.stop="clearFile"
          >
            ✕ 删除
          </button>
        </div>
      </div>
    </div>

    <div v-if="recognizedType" class="recognized-type">
      <span class="badge" :class="recognizedType === 'excel' ? 'badge-success' : 'badge-info'">
        已识别类型：{{ recognizedType === 'excel' ? '📋 Excel 模板' : '🏷️ 标签模板' }}
      </span>
      <span v-if="analyzing" class="muted" style="margin-left:10px;">分析中...</span>
    </div>

    <div v-if="analyzeError" class="alert alert-danger" style="margin-top:10px;">
      {{ analyzeError }}
    </div>
  </div>
</template>

<script>
import api from '../../api'

export default {
  name: 'FileUploadStep',
  props: {
    templateName: {
      type: String,
      default: ''
    },
    selectedFile: {
      type: [File, null],
      default: null
    }
  },
  data() {
    return {
      localTemplateName: this.templateName,
      localSelectedFile: this.selectedFile,
      recognizedType: null,
      isDragover: false,
      analyzing: false,
      analyzeError: null
    }
  },
  watch: {
    templateName(val) {
      this.localTemplateName = val
    },
    selectedFile(val) {
      this.localSelectedFile = val
    }
  },
  methods: {
    triggerFileInput() {
      this.$refs.fileInput.click()
    },

    handleFileSelect(event) {
      const file = event.target.files[0]
      if (file) {
        this.selectFile(file)
      }
    },

    handleDrop(event) {
      this.isDragover = false
      const file = event.dataTransfer.files[0]
      if (file) {
        this.selectFile(file)
      }
    },

    selectFile(file) {
      const ext = file.name.split('.').pop().toLowerCase()
      const validExts = ['xlsx', 'xls', 'png', 'jpg', 'jpeg', 'gif', 'bmp']

      if (!validExts.includes(ext)) {
        this.analyzeError = '不支持的文件类型，请上传 Excel 或图片文件'
        return
      }

      this.localSelectedFile = file
      this.$emit('update:selected-file', file)
      this.analyzeError = null
      this.recognizedType = null

      if (ext === 'xlsx' || ext === 'xls') {
        this.recognizedType = 'excel'
      } else {
        this.recognizedType = 'label'
      }

      this.$emit('file-selected', {
        selectedFile: this.localSelectedFile,
        templateName: this.localTemplateName,
        recognizedType: this.recognizedType
      })
    },

    clearFile() {
      this.localSelectedFile = null
      this.$emit('update:selected-file', null)
      this.recognizedType = null
      this.$refs.fileInput.value = ''
      this.analyzeError = null
    },

    onTemplateNameChange() {
      this.$emit('update:template-name', this.localTemplateName)
      this.$emit('file-selected', {
        selectedFile: this.localSelectedFile,
        templateName: this.localTemplateName,
        recognizedType: this.recognizedType
      })
    },

    getFileIcon() {
      if (!this.localSelectedFile) return '📁'
      const ext = this.localSelectedFile.name.split('.').pop().toLowerCase()
      if (['xlsx', 'xls'].includes(ext)) return '📋'
      if (['png', 'jpg', 'jpeg', 'gif', 'bmp'].includes(ext)) return '🖼️'
      return '📄'
    },

    formatFileSize(bytes) {
      if (bytes < 1024) return bytes + ' B'
      if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
      return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
    },

    getData() {
      return {
        templateName: this.localTemplateName,
        selectedFile: this.localSelectedFile,
        recognizedType: this.recognizedType
      }
    },

    validate() {
      if (!this.localTemplateName.trim()) {
        this.analyzeError = '请输入模板名称'
        return false
      }
      if (!this.localSelectedFile) {
        this.analyzeError = '请上传文件'
        return false
      }
      return true
    }
  }
}
</script>

<style scoped>
.file-upload-step {
  padding: 10px 0;
}

.form-group {
  margin-bottom: 20px;
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

.upload-area {
  border: 2px dashed #ddd;
  border-radius: 8px;
  padding: 40px 20px;
  text-align: center;
  cursor: pointer;
  transition: all 0.3s;
  background: #fafafa;
}

.upload-area:hover {
  border-color: #42b983;
  background: #f8fff9;
}

.upload-area.dragover {
  border-color: #42b983;
  background: #e8f5e9;
}

.upload-area.has-file {
  border-style: solid;
  border-color: #42b983;
  background: #f0f7ff;
}

.file-info {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.recognized-type {
  margin-top: 15px;
  padding: 10px;
  background: #f0f7ff;
  border-radius: 4px;
  display: flex;
  align-items: center;
}

.badge {
  display: inline-block;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
}

.badge-success {
  background: #d4edda;
  color: #155724;
}

.badge-info {
  background: #cce5ff;
  color: #004085;
}

.alert {
  padding: 10px 15px;
  border-radius: 4px;
  font-size: 13px;
}

.alert-danger {
  background: #f8d7da;
  color: #721c24;
  border: 1px solid #f5c6cb;
}

.muted {
  color: #6c757d;
}
</style>
