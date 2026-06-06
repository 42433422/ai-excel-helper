<template>
  <div class="approval-flow-management">
    <div class="view-header">
      <h2>审批流程管理</h2>
      <p class="subtitle">创建和管理多级审批流程</p>
    </div>

    <!-- 流程列表 -->
    <div class="flow-list-section">
      <div class="section-header">
        <h3>审批流程列表</h3>
        <button class="btn btn-primary" @click="showCreateModal = true">
          <i class="fa fa-plus"></i> 新建流程
        </button>
      </div>
      <div class="flow-list">
        <div 
          v-for="flow in flowList" 
          :key="flow.id" 
          class="flow-item"
          @click="editFlow(flow)"
        >
          <div class="flow-info">
            <div class="flow-header">
              <h4>{{ flow.flow_name }}</h4>
              <span class="flow-status" :class="{ active: flow.is_active }">
                {{ flow.is_active ? '启用' : '禁用' }}
              </span>
            </div>
            <div class="flow-meta">
              <span class="flow-key">KEY: {{ flow.flow_key }}</span>
              <span class="flow-type">{{ getBusinessTypeLabel(flow.business_type) }}</span>
            </div>
            <div class="flow-nodes">
              <span class="node-badge" v-for="(node, idx) in flow.nodes" :key="node.id">
                {{ idx + 1 }}. {{ node.node_name }}
              </span>
            </div>
            <div class="flow-description">{{ flow.description || '暂无描述' }}</div>
          </div>
          <div class="flow-actions">
            <button 
              class="btn-icon" 
              @click.stop="toggleFlowStatus(flow)"
              :title="flow.is_active ? '禁用' : '启用'"
            >
              <i :class="flow.is_active ? 'fa fa-pause' : 'fa fa-play'"></i>
            </button>
            <button 
              class="btn-icon" 
              @click.stop="deleteFlow(flow.id)"
              title="删除"
            >
              <i class="fa fa-trash"></i>
            </button>
          </div>
        </div>
        <div v-if="flowList.length === 0" class="empty-state">
          <i class="fa fa-folder-open-o"></i>
          <p>暂无审批流程，点击"新建流程"创建第一个</p>
        </div>
      </div>
    </div>

    <!-- 创建/编辑流程弹窗 -->
    <div v-if="showCreateModal" class="modal-overlay" @click="closeModal">
      <div class="modal-content" @click.stop>
        <div class="modal-header">
          <h3>{{ editingFlow ? '编辑流程' : '新建流程' }}</h3>
          <button class="btn-close" @click="closeModal">
            <i class="fa fa-times"></i>
          </button>
        </div>
        <div class="modal-body">
          <!-- 基本信息 -->
          <div class="form-section">
            <h4>基本信息</h4>
            <div class="form-grid">
              <div class="form-group">
                <label>流程名称 *</label>
                <input 
                  v-model="formData.flow_name" 
                  type="text" 
                  placeholder="如：出货单审批流程"
                />
              </div>
              <div class="form-group">
                <label>流程 KEY *</label>
                <input 
                  v-model="formData.flow_key" 
                  type="text" 
                  placeholder="如：shipment_approval"
                />
              </div>
              <div class="form-group">
                <label>业务类型 *</label>
                <select v-model="formData.business_type">
                  <option value="">选择业务类型</option>
                  <option value="shipment">出货单</option>
                  <option value="purchase">采购</option>
                  <option value="expense">费用报销</option>
                  <option value="contract">合同</option>
                  <option value="general">通用</option>
                </select>
              </div>
              <div class="form-group">
                <label>启用状态</label>
                <div class="checkbox-group">
                  <label class="checkbox-label">
                    <input type="checkbox" v-model="formData.is_active" />
                    <span>立即启用此流程</span>
                  </label>
                </div>
              </div>
              <div class="form-group full-width">
                <label>流程描述</label>
                <textarea 
                  v-model="formData.description" 
                  rows="3"
                  placeholder="描述此流程的用途和规则"
                ></textarea>
              </div>
            </div>
          </div>

          <!-- 审批节点 -->
          <div class="form-section">
            <div class="section-header">
              <h4>审批节点</h4>
              <button class="btn btn-sm" @click="addNode">
                <i class="fa fa-plus"></i> 添加节点
              </button>
            </div>
            <div class="nodes-list">
              <div 
                v-for="(node, index) in formData.nodes" 
                :key="index" 
                class="node-item"
              >
                <div class="node-header">
                  <span class="node-order">第 {{ index + 1 }} 级审批</span>
                  <button class="btn-icon btn-sm" @click="removeNode(index)" title="删除">
                    <i class="fa fa-trash"></i>
                  </button>
                </div>
                <div class="node-form">
                  <div class="form-row">
                    <div class="form-group">
                      <label>节点名称</label>
                      <input 
                        v-model="node.node_name" 
                        type="text" 
                        placeholder="如：部门经理审批"
                      />
                    </div>
                    <div class="form-group">
                      <label>节点类型</label>
                      <select v-model="node.node_type">
                        <option value="serial">串行审批</option>
                        <option value="parallel">并行审批</option>
                      </select>
                    </div>
                  </div>
                  <div class="form-row">
                    <div class="form-group">
                      <label>审批人类型</label>
                      <select v-model="node.approver_type">
                        <option value="user">指定用户</option>
                        <option value="role">指定角色</option>
                        <option value="position">指定职位</option>
                        <option value="dynamic">动态审批人</option>
                      </select>
                    </div>
                    <div class="form-group">
                      <label>审批人 ID 列表</label>
                      <input 
                        v-model="node.approver_ids_text" 
                        type="text" 
                        placeholder="多个 ID 用逗号分隔，如：1,2,3"
                      />
                      <small class="help-text">用户 ID/角色 ID/职位 ID，多个用逗号分隔</small>
                    </div>
                  </div>
                </div>
              </div>
              <div v-if="formData.nodes.length === 0" class="empty-node">
                <i class="fa fa-sitemap"></i>
                <p>暂无审批节点，点击"添加节点"按钮添加</p>
              </div>
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn" @click="closeModal">取消</button>
          <button class="btn btn-primary" @click="saveFlow" :disabled="!canSave">
            <i class="fa fa-save"></i> {{ editingFlow ? '保存修改' : '创建流程' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { approvalApi, type ApprovalFlow, type ApprovalFlowNode } from '@/api/approval'
import { appAlert, appConfirm } from '@/utils/appDialog'

// 流程列表
const flowList = ref<ApprovalFlow[]>([])
const showCreateModal = ref(false)
const editingFlow = ref<ApprovalFlow | null>(null)

// 表单数据
const formData = ref({
  flow_name: '',
  flow_key: '',
  business_type: '',
  description: '',
  is_active: true,
  nodes: [] as Array<{
    node_name: string
    node_type: string
    node_order: number
    approver_type: string
    approver_ids: number[]
    approver_ids_text: string
    is_active: boolean
  }>
})

const canSave = computed(() => {
  return (
    formData.value.flow_name &&
    formData.value.flow_key &&
    formData.value.business_type &&
    formData.value.nodes.length > 0
  )
})

// 加载流程列表
const loadFlows = async () => {
  try {
    const res = await approvalApi.getFlowList()
    if (res.success && 'data' in res && res.data) {
      flowList.value = res.data.flows || []
    }
  } catch (error) {
    console.error('加载流程列表失败:', error)
  }
}

// 创建流程
const addNode = () => {
  formData.value.nodes.push({
    node_name: '',
    node_type: 'serial',
    node_order: formData.value.nodes.length + 1,
    approver_type: 'user',
    approver_ids: [],
    approver_ids_text: '',
    is_active: true
  })
}

const removeNode = (index: number) => {
  formData.value.nodes.splice(index, 1)
  // 重新排序
  formData.value.nodes.forEach((node, idx) => {
    node.node_order = idx + 1
  })
}

const resetForm = () => {
  formData.value = {
    flow_name: '',
    flow_key: '',
    business_type: '',
    description: '',
    is_active: true,
    nodes: []
  }
  editingFlow.value = null
}

const closeModal = () => {
  showCreateModal.value = false
  resetForm()
}

const editFlow = (flow: ApprovalFlow) => {
  editingFlow.value = flow
  formData.value = {
    flow_name: flow.flow_name,
    flow_key: flow.flow_key,
    business_type: flow.business_type,
    description: flow.description || '',
    is_active: flow.is_active,
    nodes: (flow.nodes || []).map((node: ApprovalFlowNode) => ({
      ...node,
      approver_ids_text: Array.isArray(node.approver_ids) 
        ? node.approver_ids.join(',') 
        : node.approver_ids || ''
    }))
  }
  showCreateModal.value = true
}

const saveFlow = async () => {
  if (!canSave.value) {
    await appAlert('请填写必填项')
    return
  }

  // 转换审批人 ID
  const nodes = formData.value.nodes.map(node => ({
    node_name: node.node_name,
    node_type: node.node_type,
    node_order: node.node_order,
    approver_type: node.approver_type,
    approver_ids: node.approver_ids_text
      ? node.approver_ids_text.split(',').map(id => parseInt(id.trim())).filter(id => !isNaN(id))
      : [],
    is_active: node.is_active
  }))

  try {
    const flowData = {
      flow_name: formData.value.flow_name,
      flow_key: formData.value.flow_key,
      business_type: formData.value.business_type,
      description: formData.value.description,
      is_active: formData.value.is_active
    }

    let res
    if (editingFlow.value) {
      res = await approvalApi.updateFlow(editingFlow.value.id, { ...flowData })
      if (res?.success) {
        await appAlert('流程更新成功！')
        closeModal()
        loadFlows()
      } else {
        await appAlert('更新失败：' + (res?.message || '未知错误'))
      }
      return
    } else {
      res = await approvalApi.createFlow(flowData, nodes)
    }

    if (res.success) {
      await appAlert('流程创建成功！')
      closeModal()
      loadFlows()
    } else {
      await appAlert('创建失败：' + res.message)
    }
  } catch (error) {
    console.error('创建/更新流程失败:', error)
    await appAlert('操作失败，请重试')
  }
}

const toggleFlowStatus = async (flow: any) => {
  const newActive = !flow.is_active
  const res = await approvalApi.toggleFlowActive(flow.id, newActive)
  if (res?.success) {
    loadFlows()
  } else {
    await appAlert('切换状态失败：' + (res?.message || '未知错误'))
  }
}

const deleteFlow = async (flowId: number) => {
  if (!(await appConfirm('确定要删除此审批流程吗？', { danger: true }))) return
  const res = await approvalApi.deleteFlow(flowId)
  if (res?.success) {
    loadFlows()
  } else {
    await appAlert('删除失败：' + (res?.message || '未知错误'))
  }
}

const getBusinessTypeLabel = (type: string) => {
  const labels: Record<string, string> = {
    shipment: '出货单',
    purchase: '采购',
    expense: '费用报销',
    contract: '合同',
    general: '通用'
  }
  return labels[type] || type
}

onMounted(() => {
  loadFlows()
})
</script>

<style scoped>
.approval-flow-management {
  padding: 24px;
  background: #f5f7fa;
  min-height: 100vh;
}

.view-header {
  margin-bottom: 24px;
}

.view-header h2 {
  font-size: 24px;
  color: #1f2937;
  margin: 0 0 8px 0;
}

.view-header .subtitle {
  font-size: 14px;
  color: #6b7280;
  margin: 0;
}

/* 流程列表 */
.flow-list-section {
  background: white;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.section-header h3 {
  font-size: 18px;
  color: #1f2937;
  margin: 0;
}

.flow-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.flow-item {
  display: flex;
  justify-content: space-between;
  padding: 16px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
}

.flow-item:hover {
  border-color: #2563eb;
  background: #f9fafb;
}

.flow-info {
  flex: 1;
}

.flow-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
}

.flow-header h4 {
  font-size: 16px;
  color: #1f2937;
  margin: 0;
}

.flow-status {
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
  background: #d1fae5;
  color: #059669;
}

.flow-status:not(.active) {
  background: #e5e7eb;
  color: #6b7280;
}

.flow-meta {
  display: flex;
  gap: 16px;
  font-size: 13px;
  color: #6b7280;
  margin-bottom: 8px;
}

.flow-key {
  font-family: monospace;
  background: #f3f4f6;
  padding: 2px 6px;
  border-radius: 4px;
}

.flow-nodes {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 8px;
}

.node-badge {
  background: #dbeafe;
  color: #2563eb;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
}

.flow-description {
  font-size: 14px;
  color: #6b7280;
}

.flow-actions {
  display: flex;
  gap: 8px;
}

.btn-icon {
  width: 32px;
  height: 32px;
  border-radius: 6px;
  border: none;
  background: #f3f4f6;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  color: #6b7280;
}

.btn-icon:hover {
  background: #e5e7eb;
}

.btn-icon.btn-sm {
  width: 24px;
  height: 24px;
  font-size: 12px;
}

/* 按钮 */
.btn {
  padding: 8px 16px;
  border-radius: 6px;
  border: none;
  cursor: pointer;
  font-size: 14px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.btn-primary {
  background: #2563eb;
  color: white;
}

.btn-primary:hover {
  background: #1d4ed8;
}

.btn-sm {
  padding: 4px 8px;
  font-size: 13px;
}

/* 空状态 */
.empty-state {
  text-align: center;
  padding: 40px 20px;
  color: #9ca3af;
}

.empty-state i {
  font-size: 48px;
  margin-bottom: 12px;
}

/* 弹窗 */
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
  width: 900px;
  max-height: 90vh;
  overflow-y: auto;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px;
  border-bottom: 1px solid #e5e7eb;
}

.modal-header h3 {
  margin: 0;
  font-size: 20px;
}

.btn-close {
  background: none;
  border: none;
  font-size: 20px;
  cursor: pointer;
  color: #6b7280;
}

.modal-body {
  padding: 20px;
}

.form-section {
  margin-bottom: 24px;
}

.form-section h4 {
  font-size: 16px;
  color: #1f2937;
  margin: 0 0 12px 0;
  padding-bottom: 8px;
  border-bottom: 1px solid #e5e7eb;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-group.full-width {
  grid-column: 1 / -1;
}

.form-group label {
  font-size: 14px;
  color: #374151;
  font-weight: 500;
}

.form-group input,
.form-group select,
.form-group textarea {
  padding: 8px 12px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 14px;
}

.form-group input:focus,
.form-group select:focus,
.form-group textarea:focus {
  outline: none;
  border-color: #2563eb;
}

.help-text {
  font-size: 12px;
  color: #6b7280;
}

.checkbox-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}

/* 节点列表 */
.nodes-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.node-item {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 16px;
  background: #f9fafb;
}

.node-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.node-order {
  font-size: 14px;
  font-weight: 600;
  color: #2563eb;
}

.node-form {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.form-row {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}

.empty-node {
  text-align: center;
  padding: 30px;
  color: #9ca3af;
}

.empty-node i {
  font-size: 40px;
  margin-bottom: 8px;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 20px;
  border-top: 1px solid #e5e7eb;
}
</style>
