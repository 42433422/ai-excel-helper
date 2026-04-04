<template>
  <div class="qsm-pro-advanced">
    <h1><i class="fa fa-cogs"></i> 奇士美 PRO · 高级功能</h1>
    <p>专业版高级功能配置页面</p>
    
    <div class="qsm-pro-employees" v-if="modWorkflowEmployees.length">
      <h3>AI 业务员</h3>
      <div class="employee-list">
        <div
          v-for="emp in modWorkflowEmployees"
          :key="emp.id"
          class="employee-card"
        >
          <span class="employee-name">{{ emp.label }}</span>
        </div>
      </div>
    </div>

    <div class="qa-package-section">
      <div class="section-header">
        <h3>业务员问答包</h3>
        <button class="btn btn-primary" @click="createNewPackage">
          <i class="fa fa-plus"></i> 新建问答包
        </button>
      </div>
      <p class="section-desc">管理AI业务员使用的问答模板，包括开场白和常用问答对</p>

      <div class="package-list" v-if="packages.length">
        <div
          v-for="pkg in packages"
          :key="pkg.id"
          class="package-card"
          :class="{ active: selectedPackageId === pkg.id }"
          @click="selectPackage(pkg.id)"
        >
          <div class="package-header">
            <h4>{{ pkg.name }}</h4>
            <div class="package-actions">
              <button class="btn-icon" @click.stop="editPackage(pkg)" title="编辑">
                <i class="fa fa-edit"></i>
              </button>
              <button v-if="pkg.id === 'default'" class="btn-icon" @click.stop="resetPackage(pkg.id)" title="重置为默认">
                <i class="fa fa-refresh"></i>
              </button>
              <button v-if="pkg.id !== 'default'" class="btn-icon btn-danger" @click.stop="deletePackage(pkg.id)" title="删除">
                <i class="fa fa-trash"></i>
              </button>
            </div>
          </div>
          <p class="package-desc">{{ pkg.description || '暂无描述' }}</p>
          <div class="package-meta">
            <span><i class="fa fa-comments"></i> {{ pkg.qa_pairs?.length || 0 }} 条问答</span>
            <span><i class="fa fa-clock-o"></i> {{ formatDate(pkg.updated_at) }}</span>
          </div>
        </div>
      </div>

      <div v-else class="empty-state">
        <i class="fa fa-inbox"></i>
        <p>暂无问答包，点击上方按钮创建</p>
      </div>
    </div>

    <div v-if="selectedPackage" class="package-editor">
      <div class="editor-header">
        <h3>{{ isNewPackage ? '新建问答包' : '编辑问答包' }}</h3>
        <button class="btn btn-secondary" @click="closeEditor">关闭</button>
      </div>

      <div class="editor-form">
        <div class="form-group">
          <label>问答包名称</label>
          <input v-model="editingPackage.name" type="text" placeholder="请输入问答包名称" />
        </div>

        <div class="form-group">
          <label>描述</label>
          <textarea v-model="editingPackage.description" placeholder="请输入问答包描述" rows="2"></textarea>
        </div>

        <div class="form-group">
          <label>开场白</label>
          <textarea v-model="editingPackage.opening_line" placeholder="例如：您好这里是深圳奇士美油漆，欢迎订购！请问您是哪个购买单位呢？" rows="3"></textarea>
        </div>

        <div class="qa-pairs-section">
          <div class="section-header">
            <h4>问答对</h4>
            <button class="btn btn-small" @click="addQAPair">
              <i class="fa fa-plus"></i> 添加问答
            </button>
          </div>

          <div v-for="(pair, index) in editingPackage.qa_pairs" :key="index" class="qa-pair-item">
            <div class="qa-pair-header">
              <span class="qa-index">{{ index + 1 }}</span>
              <button class="btn-icon btn-danger" @click="removeQAPair(index)" title="删除">
                <i class="fa fa-times"></i>
              </button>
            </div>
            <div class="qa-pair-content">
              <div class="qa-input-group">
                <label>问</label>
                <textarea v-model="pair.question" placeholder="用户问题" rows="2"></textarea>
              </div>
              <div class="qa-input-group">
                <label>答</label>
                <textarea v-model="pair.answer" placeholder="AI回答" rows="2"></textarea>
              </div>
            </div>
          </div>

          <div v-if="!editingPackage.qa_pairs?.length" class="empty-qa">
            <p>暂无问答对，点击上方按钮添加</p>
          </div>
        </div>

        <div class="form-actions">
          <button class="btn btn-secondary" @click="closeEditor">取消</button>
          <button class="btn btn-primary" @click="savePackage">
            <i class="fa fa-save"></i> 保存
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useModsStore } from '@/stores/mods';

const modsStore = useModsStore();

const modWorkflowEmployees = computed(() => {
  return (modsStore.mods || []).flatMap((m) => m.workflow_employees || []);
});

const packages = ref([]);
const selectedPackageId = ref(null);
const selectedPackage = ref(null);
const editingPackage = ref(null);
const isNewPackage = ref(false);
const loading = ref(false);

const API_BASE = '/api/mod/sz-qsm-pro';

async function fetchPackages() {
  try {
    const response = await fetch(`${API_BASE}/qa-packages`);
    const result = await response.json();
    if (result.success) {
      packages.value = result.data;
    }
  } catch (error) {
    console.error('获取问答包失败:', error);
  }
}

function selectPackage(packageId) {
  selectedPackageId.value = packageId;
  selectedPackage.value = packages.value.find(p => p.id === packageId);
  editPackage(selectedPackage.value);
}

function createNewPackage() {
  isNewPackage.value = true;
  editingPackage.value = {
    name: '',
    description: '',
    opening_line: '',
    qa_pairs: []
  };
}

function editPackage(pkg) {
  isNewPackage.value = false;
  editingPackage.value = JSON.parse(JSON.stringify(pkg));
}

function closeEditor() {
  editingPackage.value = null;
  selectedPackageId.value = null;
  selectedPackage.value = null;
  isNewPackage.value = false;
}

function addQAPair() {
  if (!editingPackage.value.qa_pairs) {
    editingPackage.value.qa_pairs = [];
  }
  editingPackage.value.qa_pairs.push({ question: '', answer: '' });
}

function removeQAPair(index) {
  editingPackage.value.qa_pairs.splice(index, 1);
}

async function savePackage() {
  try {
    loading.value = true;
    let response;
    
    if (isNewPackage.value) {
      response = await fetch(`${API_BASE}/qa-packages`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(editingPackage.value)
      });
    } else {
      response = await fetch(`${API_BASE}/qa-packages/${editingPackage.value.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(editingPackage.value)
      });
    }

    const result = await response.json();
    if (result.success) {
      await fetchPackages();
      closeEditor();
      alert(result.message || '保存成功');
    } else {
      alert(result.message || '保存失败');
    }
  } catch (error) {
    console.error('保存失败:', error);
    alert('保存失败，请稍后重试');
  } finally {
    loading.value = false;
  }
}

async function deletePackage(packageId) {
  if (!confirm('确定要删除这个问答包吗？')) return;
  
  try {
    const response = await fetch(`${API_BASE}/qa-packages/${packageId}`, {
      method: 'DELETE'
    });
    const result = await response.json();
    if (result.success) {
      await fetchPackages();
      if (selectedPackageId.value === packageId) {
        closeEditor();
      }
      alert('删除成功');
    } else {
      alert(result.message || '删除失败');
    }
  } catch (error) {
    console.error('删除失败:', error);
    alert('删除失败，请稍后重试');
  }
}

async function resetPackage(packageId) {
  if (!confirm('确定要重置为默认问答包吗？当前修改将丢失。')) return;
  
  try {
    const response = await fetch(`${API_BASE}/qa-packages/${packageId}/reset`, {
      method: 'POST'
    });
    const result = await response.json();
    if (result.success) {
      await fetchPackages();
      if (selectedPackageId.value === packageId) {
        editPackage(result.data);
      }
      alert('重置成功');
    } else {
      alert(result.message || '重置失败');
    }
  } catch (error) {
    console.error('重置失败:', error);
    alert('重置失败，请稍后重试');
  }
}

function formatDate(dateStr) {
  if (!dateStr) return '';
  const date = new Date(dateStr);
  return date.toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit'
  });
}

onMounted(() => {
  fetchPackages();
});
</script>

<style scoped>
.qsm-pro-advanced {
  padding: 20px;
  max-width: 1200px;
}

.qsm-pro-advanced h1 {
  color: #1f2937;
  margin-bottom: 8px;
  font-size: 24px;
}

.qsm-pro-advanced > p {
  color: #6b7280;
  margin-bottom: 24px;
}

.qsm-pro-employees {
  margin-bottom: 32px;
}

.qsm-pro-employees h3 {
  color: #374151;
  margin-bottom: 12px;
  font-size: 16px;
}

.employee-list {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.employee-card {
  background: #f3f4f6;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 12px 16px;
  min-width: 160px;
}

.employee-name {
  color: #1f2937;
  font-weight: 500;
}

.qa-package-section {
  margin-top: 32px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.section-header h3,
.section-header h4 {
  color: #374151;
  margin: 0;
  font-size: 16px;
}

.section-desc {
  color: #6b7280;
  margin-bottom: 16px;
  font-size: 14px;
}

.package-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 16px;
}

.package-card {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 16px;
  cursor: pointer;
  transition: all 0.2s;
}

.package-card:hover {
  border-color: #3b82f6;
  box-shadow: 0 2px 8px rgba(59, 130, 246, 0.1);
}

.package-card.active {
  border-color: #3b82f6;
  background: #eff6ff;
}

.package-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 8px;
}

.package-header h4 {
  color: #1f2937;
  margin: 0;
  font-size: 16px;
}

.package-actions {
  display: flex;
  gap: 4px;
}

.btn-icon {
  background: none;
  border: none;
  color: #6b7280;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 4px;
  transition: all 0.2s;
}

.btn-icon:hover {
  background: #f3f4f6;
  color: #374151;
}

.btn-icon.btn-danger:hover {
  background: #fee2e2;
  color: #dc2626;
}

.package-desc {
  color: #6b7280;
  margin: 0 0 12px 0;
  font-size: 14px;
}

.package-meta {
  display: flex;
  gap: 16px;
  color: #9ca3af;
  font-size: 13px;
}

.package-meta span {
  display: flex;
  align-items: center;
  gap: 4px;
}

.empty-state {
  text-align: center;
  padding: 48px;
  color: #9ca3af;
}

.empty-state i {
  font-size: 48px;
  margin-bottom: 16px;
}

.package-editor {
  margin-top: 32px;
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 24px;
}

.editor-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
  padding-bottom: 16px;
  border-bottom: 1px solid #e5e7eb;
}

.editor-header h3 {
  margin: 0;
  color: #1f2937;
}

.editor-form {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-group label {
  color: #374151;
  font-weight: 500;
  font-size: 14px;
}

.form-group input,
.form-group textarea {
  padding: 10px 12px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 14px;
  transition: border-color 0.2s;
}

.form-group input:focus,
.form-group textarea:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.qa-pairs-section {
  border-top: 1px solid #e5e7eb;
  padding-top: 20px;
}

.qa-pair-item {
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 12px;
}

.qa-pair-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.qa-index {
  background: #3b82f6;
  color: white;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 500;
}

.qa-pair-content {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.qa-input-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.qa-input-group label {
  color: #6b7280;
  font-size: 13px;
  font-weight: 500;
}

.qa-input-group textarea {
  padding: 8px 10px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 14px;
  resize: vertical;
}

.empty-qa {
  text-align: center;
  padding: 24px;
  color: #9ca3af;
  font-size: 14px;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding-top: 16px;
  border-top: 1px solid #e5e7eb;
}

.btn {
  padding: 10px 20px;
  border: none;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.btn-primary {
  background: #3b82f6;
  color: white;
}

.btn-primary:hover {
  background: #2563eb;
}

.btn-secondary {
  background: #f3f4f6;
  color: #374151;
}

.btn-secondary:hover {
  background: #e5e7eb;
}

.btn-small {
  padding: 6px 12px;
  font-size: 13px;
}
</style>
<!-- 4243342 -->
