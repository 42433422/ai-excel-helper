<template>
  <div class="file-import-overlay" v-if="modelValue" @click.self="handleClose">
    <div class="file-import-modal">
      <div class="file-import-header">
        <h4>{{ title }}</h4>
        <button class="close-btn" @click="handleClose" title="关闭">
          <i class="fas fa-times"></i>
        </button>
      </div>

      <div class="file-import-body">
        <div 
          class="drop-zone"
          :class="{ 
            'dragover': isDragOver,
            'uploading': uploading 
          }"
          @dragenter.prevent="handleDragEnter"
          @dragover.prevent="handleDragOver"
          @dragleave.prevent="handleDragLeave"
          @drop.prevent="handleDrop"
          @click="triggerFileInput"
        >
          <div class="drop-zone-content">
            <i class="fas fa-cloud-upload-alt"></i>
            <p class="drop-zone-title">点击或拖拽文件到此处</p>
            <p class="drop-zone-hint">{{ hint }}</p>
            <p class="drop-zone-supported">
              支持：Excel、CSV、图片、PDF、Word
            </p>
          </div>
          <input
            ref="fileInputRef"
            type="file"
            class="file-input"
            :accept="acceptFormats"
            :multiple="multiple"
            @change="handleFileChange"
          />
        </div>

        <div class="import-progress" v-if="uploading || progress > 0">
          <div class="progress-header">
            <span class="progress-text">{{ progressText }}</span>
            <span class="progress-percent">{{ progress }}%</span>
          </div>
          <div class="progress-bar">
            <div 
              class="progress-fill" 
              :style="{ width: progress + '%' }"
              :class="{ 'progress-animated': uploading }"
            ></div>
          </div>
        </div>

        <div class="import-status" v-if="status.show" :class="status.type">
          <i :class="statusIcon"></i>
          <span>{{ status.message }}</span>
        </div>

        <div class="file-list" v-if="selectedFiles.length > 0">
          <div class="file-list-header">
            <span>已选择文件 ({{ selectedFiles.length }})</span>
            <button class="clear-btn" @click="clearFiles" v-if="!uploading">
              <i class="fas fa-trash"></i> 清空
            </button>
          </div>
          <div class="file-items">
            <div 
              class="file-item" 
              v-for="(file, index) in selectedFiles" 
              :key="index"
            >
              <i :class="getFileIcon(file.type)" class="file-icon"></i>
              <div class="file-info">
                <span class="file-name">{{ file.name }}</span>
                <span class="file-size">{{ formatFileSize(file.size) }}</span>
              </div>
              <span class="file-type-tag">{{ file.fileType }}</span>
            </div>
          </div>
        </div>
      </div>

      <div class="file-import-footer">
        <button 
          class="btn btn-secondary" 
          @click="handleClose"
          :disabled="uploading"
        >
          取消
        </button>
        <button 
          class="btn btn-primary" 
          @click="handleUpload"
          :disabled="selectedFiles.length === 0 || uploading"
        >
          <i class="fas fa-upload" v-if="!uploading"></i>
          <i class="fas fa-spinner fa-spin" v-else></i>
          {{ uploading ? '上传中...' : '开始导入' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue';
import useFileImport, { FILE_EXTENSIONS } from '../composables/useFileImport';

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false
  },
  title: {
    type: String,
    default: '文件导入'
  },
  purpose: {
    type: String,
    default: 'general',
    validator: (value) => ['general', 'product_import', 'customers_import', 'order_parse', 'materials_import'].includes(value)
  },
  hint: {
    type: String,
    default: '支持 Excel、CSV、图片等格式，自动识别并分析'
  },
  acceptFormats: {
    type: String,
    default: '.xlsx,.xls,.csv,.jpg,.jpeg,.png,.gif,.webp,.pdf,.doc,.docx'
  },
  multiple: {
    type: Boolean,
    default: true
  },
  autoUpload: {
    type: Boolean,
    default: false
  }
});

const emit = defineEmits(['update:modelValue', 'uploaded', 'error', 'progress', 'file-complete']);

const fileInputRef = ref(null);
const isDragOver = ref(false);
const selectedFiles = ref([]);

const {
  uploading,
  progress,
  progressText,
  status,
  detectFileType,
  resetState,
  uploadFile,
  uploadMultipleFiles
} = useFileImport();

const computedHint = computed(() => {
  if (props.purpose === 'customers_import') {
    return '请上传购买单位列表 .xlsx（需含「单位名称」列），将校验格式并更新联系人/电话/地址';
  }
  if (props.purpose === 'product_import') {
    return '产品导入模式：支持任意文件，自动识别并分析';
  }
  if (props.purpose === 'order_parse') {
    return '订单解析模式：上传后自动提取订单关键信息';
  }
  if (props.purpose === 'materials_import') {
    return '原材料导入模式：支持 Excel/CSV 格式';
  }
  return props.hint;
});

const statusIcon = computed(() => {
  if (status.type === 'success') return 'fas fa-check-circle';
  if (status.type === 'error') return 'fas fa-exclamation-circle';
  return 'fas fa-info-circle';
});

function getFileIcon(fileType) {
  const icons = {
    excel: 'fas fa-file-excel',
    csv: 'fas fa-file-csv',
    image: 'fas fa-file-image',
    pdf: 'fas fa-file-pdf',
    word: 'fas fa-file-word',
    other: 'fas fa-file'
  };
  return icons[fileType] || icons.other;
}

function formatFileSize(bytes) {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

function triggerFileInput() {
  if (!uploading.value && fileInputRef.value) {
    fileInputRef.value.click();
  }
}

function handleDragEnter(e) {
  if (!uploading.value) {
    isDragOver.value = true;
  }
}

function handleDragOver(e) {
  if (!uploading.value) {
    isDragOver.value = true;
  }
}

function handleDragLeave(e) {
  if (e.relatedTarget === null || !e.currentTarget.contains(e.relatedTarget)) {
    isDragOver.value = false;
  }
}

function handleDrop(e) {
  isDragOver.value = false;
  if (uploading.value) return;
  
  const files = e.dataTransfer.files;
  if (files.length > 0) {
    handleFiles(files);
  }
}

function handleFileChange(e) {
  const files = e.target.files;
  if (files.length > 0) {
    handleFiles(files);
  }
}

function handleFiles(fileList) {
  const newFiles = [];
  for (let i = 0; i < fileList.length; i++) {
    const file = fileList[i];
    const fileType = detectFileType(file);
    newFiles.push({
      ...file,
      fileType
    });
  }
  
  if (props.multiple) {
    selectedFiles.value = [...selectedFiles.value, ...newFiles];
  } else {
    selectedFiles.value = [newFiles[0]];
  }
  
  if (props.autoUpload && newFiles.length > 0) {
    handleUpload();
  }
}

function clearFiles() {
  selectedFiles.value = [];
  resetState();
}

async function handleUpload() {
  if (selectedFiles.value.length === 0 || uploading.value) return;
  
  const filesToUpload = selectedFiles.value.map(f => {
    const newFile = new File([f], f.name, { type: f.type });
    return newFile;
  });
  
  try {
    if (filesToUpload.length === 1) {
      const result = await uploadFile(filesToUpload[0], props.purpose, (percent, fileName) => {
        emit('progress', { percent, fileName, totalFiles: 1 });
      });
      
      if (result) {
        emit('uploaded', {
          file: selectedFiles.value[0],
          result
        });
      } else {
        emit('error', {
          file: selectedFiles.value[0],
          error: status.message
        });
      }
    } else {
      const results = await uploadMultipleFiles(filesToUpload, props.purpose, (fileResult, completed, total) => {
        emit('file-complete', {
          file: fileResult,
          completed,
          total
        });
      });
      
      emit('uploaded', {
        files: selectedFiles.value,
        results
      });
    }
  } catch (err) {
    console.error('Upload error:', err);
    emit('error', {
      error: err.message
    });
  }
}

function handleClose() {
  if (!uploading.value) {
    emit('update:modelValue', false);
    selectedFiles.value = [];
    resetState();
  }
}

watch(() => props.modelValue, (newVal) => {
  if (!newVal) {
    selectedFiles.value = [];
    resetState();
  }
});
</script>

<style scoped>
.file-import-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
  animation: fadeIn 0.3s ease;
}

@keyframes fadeIn {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

.file-import-modal {
  background: white;
  border-radius: 12px;
  width: 90%;
  max-width: 600px;
  max-height: 80vh;
  display: flex;
  flex-direction: column;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
  animation: slideIn 0.3s ease;
}

@keyframes slideIn {
  from {
    transform: translateY(-20px);
    opacity: 0;
  }
  to {
    transform: translateY(0);
    opacity: 1;
  }
}

.file-import-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 24px;
  border-bottom: 1px solid #e0e0e0;
}

.file-import-header h4 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #333;
}

.close-btn {
  background: none;
  border: none;
  font-size: 20px;
  color: #999;
  cursor: pointer;
  padding: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  transition: all 0.2s;
}

.close-btn:hover {
  background: #f5f5f5;
  color: #333;
}

.file-import-body {
  padding: 24px;
  overflow-y: auto;
  flex: 1;
}

.drop-zone {
  border: 2px dashed #ccc;
  border-radius: 8px;
  padding: 40px 20px;
  text-align: center;
  cursor: pointer;
  transition: all 0.3s ease;
  background: #fafafa;
}

.drop-zone:hover {
  border-color: #667eea;
  background: #f0f4ff;
}

.drop-zone.dragover {
  border-color: #667eea;
  background: #e8eeff;
  transform: scale(1.02);
}

.drop-zone.uploading {
  cursor: not-allowed;
  opacity: 0.7;
}

.drop-zone-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}

.drop-zone-content i {
  font-size: 48px;
  color: #667eea;
  margin-bottom: 8px;
}

.drop-zone-title {
  font-size: 16px;
  font-weight: 600;
  color: #333;
  margin: 0;
}

.drop-zone-hint {
  font-size: 13px;
  color: #666;
  margin: 0;
}

.drop-zone-supported {
  font-size: 12px;
  color: #999;
  margin: 0;
}

.file-input {
  display: none;
}

.import-progress {
  margin-top: 20px;
}

.progress-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
  font-size: 13px;
  color: #666;
}

.progress-percent {
  font-weight: 600;
  color: #667eea;
}

.progress-bar {
  height: 8px;
  background: #e0e0e0;
  border-radius: 4px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #667eea, #764ba2);
  transition: width 0.3s ease;
}

.progress-fill.progress-animated {
  animation: progressPulse 1.5s ease-in-out infinite;
}

@keyframes progressPulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.7;
  }
}

.import-status {
  margin-top: 16px;
  padding: 12px 16px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 14px;
  animation: slideDown 0.3s ease;
}

@keyframes slideDown {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.import-status.success {
  background: #d4edda;
  color: #155724;
  border: 1px solid #c3e6cb;
}

.import-status.error {
  background: #f8d7da;
  color: #721c24;
  border: 1px solid #f5c6cb;
}

.file-list {
  margin-top: 20px;
  border: 1px solid #e0e0e0;
  border-radius: 6px;
  overflow: hidden;
}

.file-list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: #f9f9f9;
  border-bottom: 1px solid #e0e0e0;
  font-size: 14px;
  font-weight: 600;
  color: #333;
}

.clear-btn {
  background: none;
  border: none;
  color: #dc3545;
  cursor: pointer;
  font-size: 13px;
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 8px;
  border-radius: 4px;
  transition: all 0.2s;
}

.clear-btn:hover {
  background: #fee;
}

.file-items {
  max-height: 200px;
  overflow-y: auto;
}

.file-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  border-bottom: 1px solid #f0f0f0;
  transition: background 0.2s;
}

.file-item:last-child {
  border-bottom: none;
}

.file-item:hover {
  background: #f9f9f9;
}

.file-icon {
  font-size: 24px;
  color: #667eea;
}

.file-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.file-name {
  font-size: 14px;
  color: #333;
  font-weight: 500;
}

.file-size {
  font-size: 12px;
  color: #999;
}

.file-type-tag {
  font-size: 11px;
  padding: 2px 8px;
  background: #e8eeff;
  color: #667eea;
  border-radius: 4px;
  text-transform: uppercase;
}

.file-import-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 16px 24px;
  border-top: 1px solid #e0e0e0;
}

.btn {
  padding: 10px 20px;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 8px;
  transition: all 0.2s;
  border: none;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-secondary {
  background: #f5f5f5;
  color: #333;
}

.btn-secondary:hover:not(:disabled) {
  background: #e0e0e0;
}

.btn-primary {
  background: linear-gradient(135deg, #667eea, #764ba2);
  color: white;
}

.btn-primary:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
}
</style>
