<template>
  <div class="approval-workspace-view">
    <div class="view-header">
      <h2>审批工作台</h2>
      <p class="subtitle">处理待审批事项，跟踪审批进度</p>
    </div>

    <!-- 统计卡片 -->
    <div class="stats-cards">
      <div class="stat-card pending">
        <div class="stat-icon">
          <i class="fa fa-clock-o"></i>
        </div>
        <div class="stat-info">
          <div class="stat-value">{{ stats.pending }}</div>
          <div class="stat-label">待审批</div>
        </div>
      </div>
      <div class="stat-card initiated">
        <div class="stat-icon">
          <i class="fa fa-paper-plane"></i>
        </div>
        <div class="stat-info">
          <div class="stat-value">{{ stats.initiated }}</div>
          <div class="stat-label">我发起的</div>
        </div>
      </div>
      <div class="stat-card approved">
        <div class="stat-icon">
          <i class="fa fa-check-circle"></i>
        </div>
        <div class="stat-info">
          <div class="stat-value">{{ stats.approved }}</div>
          <div class="stat-label">已通过</div>
        </div>
      </div>
      <div class="stat-card rejected">
        <div class="stat-icon">
          <i class="fa fa-times-circle"></i>
        </div>
        <div class="stat-info">
          <div class="stat-value">{{ stats.rejected }}</div>
          <div class="stat-label">已拒绝</div>
        </div>
      </div>
    </div>

    <!-- 待审批列表 -->
    <div class="section">
      <div class="section-header">
        <h3>待我审批</h3>
        <button class="btn-link" @click="viewAll('pending')">查看全部</button>
      </div>
      <div class="request-list">
        <div 
          v-for="item in pendingRequests" 
          :key="item.id" 
          class="request-item"
          @click="viewDetails(item.id)"
        >
          <div class="request-left">
            <div class="request-icon">
              <i :class="getBusinessIcon(item.business_type)"></i>
            </div>
            <div class="request-info">
              <div class="request-title">{{ item.title }}</div>
              <div class="request-meta">
                <span class="request-no">{{ item.request_no }}</span>
                <span class="request-time">{{ formatTime(item.created_at) }}</span>
              </div>
            </div>
          </div>
          <div class="request-actions">
            <button 
              class="btn-approve" 
              @click.stop="approve(item.id)"
              title="通过"
            >
              <i class="fa fa-check"></i>
            </button>
            <button 
              class="btn-reject" 
              @click.stop="reject(item.id)"
              title="拒绝"
            >
              <i class="fa fa-times"></i>
            </button>
          </div>
        </div>
        <div v-if="pendingRequests.length === 0" class="empty-state">
          <i class="fa fa-check-circle-o"></i>
          <p>暂无待审批事项</p>
        </div>
      </div>
    </div>

    <!-- 我发起的列表 -->
    <div class="section">
      <div class="section-header">
        <h3>我发起的</h3>
        <div class="section-actions">
          <button
            class="btn-link btn-cleanup"
            :disabled="cleanupLoading || completedInitiatedCount === 0"
            :title="completedInitiatedCount === 0 ? '暂无可清理的已完成记录' : `清理 ${completedInitiatedCount} 条已完成记录`"
            @click="cleanupCompleted"
          >
            <i class="fa" :class="cleanupLoading ? 'fa-spinner fa-spin' : 'fa-trash-o'"></i>
            清理
            <span v-if="completedInitiatedCount > 0" class="count-badge">{{ completedInitiatedCount }}</span>
          </button>
          <button class="btn-link" @click="viewAll('initiated')">查看全部</button>
        </div>
      </div>
      <div class="request-list">
        <div 
          v-for="item in initiatedRequests" 
          :key="item.id" 
          class="request-item"
          @click="viewDetails(item.id)"
        >
          <div class="request-left">
            <div class="request-icon">
              <i :class="getBusinessIcon(item.business_type)"></i>
            </div>
            <div class="request-info">
              <div class="request-title">{{ item.title }}</div>
              <div class="request-meta">
                <span class="request-status" :class="item.status">
                  {{ getStatusLabel(item.status) }}
                </span>
                <span class="request-time">{{ formatTime(item.created_at) }}</span>
              </div>
            </div>
          </div>
          <div class="request-right">
            <div class="request-current-node" v-if="item.current_node_name">
              <i class="fa fa-map-marker"></i>
              {{ item.current_node_name }}
            </div>
            <button
              v-if="isFinalStatus(item.status)"
              class="btn-delete"
              title="删除此条记录"
              @click.stop="deleteSingle(item)"
            >
              <i class="fa fa-trash-o"></i>
            </button>
          </div>
        </div>
        <div v-if="initiatedRequests.length === 0" class="empty-state">
          <i class="fa fa-paper-plane-o"></i>
          <p>暂无发起的审批</p>
        </div>
      </div>
    </div>

    <!-- 审批详情弹窗 -->
    <div v-if="showDetails" class="modal-overlay" @click="closeDetails">
      <div class="modal-content" @click.stop>
        <div class="modal-header">
          <h3>审批详情</h3>
          <button class="btn-close" @click="closeDetails">
            <i class="fa fa-times"></i>
          </button>
        </div>
        <div class="modal-body">
          <div v-if="selectedRequest" class="request-detail">
            <div class="detail-section">
              <h4>基本信息</h4>
              <div class="detail-grid">
                <div class="detail-item">
                  <label>申请编号：</label>
                  <span>{{ selectedRequest.request_no }}</span>
                </div>
                <div class="detail-item">
                  <label>审批标题：</label>
                  <span>{{ selectedRequest.title }}</span>
                </div>
                <div class="detail-item">
                  <label>业务类型：</label>
                  <span>{{ getBusinessLabel(selectedRequest.business_type) }}</span>
                </div>
                <div class="detail-item">
                  <label>当前状态：</label>
                  <span class="status-tag" :class="selectedRequest.status">
                    {{ getStatusLabel(selectedRequest.status) }}
                  </span>
                </div>
                <div class="detail-item full-width">
                  <label>申请描述：</label>
                  <p>{{ selectedRequest.description }}</p>
                </div>
              </div>
            </div>

            <div class="detail-section">
              <h4>审批记录</h4>
              <div class="timeline">
                <div 
                  v-for="record in selectedRequest.records" 
                  :key="record.id" 
                  class="timeline-item"
                >
                  <div class="timeline-dot" :class="record.action">
                    <i :class="getActionIcon(record.action)"></i>
                  </div>
                  <div class="timeline-content">
                    <div class="timeline-header">
                      <span class="node-name">{{ record.node_name }}</span>
                      <span class="time">{{ formatTime(record.created_at) }}</span>
                    </div>
                    <div class="timeline-body">
                      <div class="approver">审批人：{{ record.approver_name || '系统' }}</div>
                      <div class="opinion">{{ record.opinion }}</div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
        <div class="modal-footer" v-if="canApprove && selectedRequest">
          <button class="btn btn-reject" @click="reject(selectedRequest.id)">
            <i class="fa fa-times"></i> 拒绝
          </button>
          <button class="btn btn-approve" @click="approve(selectedRequest.id)">
            <i class="fa fa-check"></i> 通过
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { approvalApi, type ApprovalRequest } from '@/api/approval'
import { appAlert, appConfirm, appPrompt } from '@/utils/appDialog'

const FINAL_STATUSES = ['approved', 'rejected', 'withdrawn', 'cancelled'] as const

const isFinalStatus = (status: string) =>
  (FINAL_STATUSES as readonly string[]).includes(status)

// 统计数据
const stats = ref({
  pending: 0,
  initiated: 0,
  approved: 0,
  rejected: 0
})

// 请求列表
const pendingRequests = ref<ApprovalRequest[]>([])
const initiatedRequests = ref<ApprovalRequest[]>([])

// 详情弹窗
const showDetails = ref(false)
const selectedRequest = ref<ApprovalRequest | null>(null)
const canApprove = ref(false)

// 清理
const cleanupLoading = ref(false)
const completedInitiatedCount = computed(
  () => initiatedRequests.value.filter((r) => isFinalStatus(r.status)).length
)

// 获取当前用户 ID（从 localStorage 获取）
const getCurrentUserId = () => {
  const userId = localStorage.getItem('user_id') || '4'
  return parseInt(userId)
}

// 加载数据
const loadData = async () => {
  const userId = getCurrentUserId()

  try {
    const [pendingRes, myRes] = await Promise.all([
      approvalApi.getPendingApprovals(userId),
      approvalApi.getMyRequests(userId),
    ])

    if (pendingRes.success && pendingRes.data) {
      pendingRequests.value = pendingRes.data.requests || []
      stats.value.pending = pendingRequests.value.length
    }

    if (myRes.success && myRes.data) {
      const mine = myRes.data.requests || []
      initiatedRequests.value = mine
      stats.value.initiated = mine.length
      stats.value.approved = mine.filter((r: ApprovalRequest) => r.status === 'approved').length
      stats.value.rejected = mine.filter((r: ApprovalRequest) => r.status === 'rejected').length
    }
  } catch (error) {
    console.error('加载审批数据失败:', error)
  }
}

// 查看详情
const viewDetails = async (requestId: number) => {
  try {
    const res = await approvalApi.getRequestDetails(requestId)
    if (res.success) {
      selectedRequest.value = res.data
      showDetails.value = true
      
      // 判断当前用户是否可以审批
      const userId = getCurrentUserId()
      canApprove.value = res.data.current_approvers?.includes(userId) || false
    }
  } catch (error) {
    console.error('加载详情失败:', error)
  }
}

const closeDetails = () => {
  showDetails.value = false
  selectedRequest.value = null
  canApprove.value = false
}

// 审批操作
const approve = async (requestId: number) => {
  const opinion = await appPrompt('请输入审批意见：', '同意', { title: '审批通过' })
  if (opinion === null || !String(opinion).trim()) return

  const userId = getCurrentUserId()
  try {
    const res = await approvalApi.approve(requestId, userId, String(opinion).trim())
    if (res.success) {
      await appAlert('审批通过！')
      loadData()
      closeDetails()
    } else {
      await appAlert('审批失败：' + res.message)
    }
  } catch (error) {
    console.error('审批失败:', error)
    await appAlert('审批失败，请重试')
  }
}

const reject = async (requestId: number) => {
  const reason = await appPrompt('请输入拒绝原因：', '', { title: '拒绝审批' })
  if (reason === null || !String(reason).trim()) return

  const userId = getCurrentUserId()
  try {
    const res = await approvalApi.reject(requestId, userId, String(reason).trim())
    if (res.success) {
      await appAlert('已拒绝')
      loadData()
      closeDetails()
    } else {
      await appAlert('拒绝失败：' + res.message)
    }
  } catch (error) {
    console.error('拒绝失败:', error)
    await appAlert('拒绝失败，请重试')
  }
}

// 查看全部
const viewAll = (type: string) => {
  // TODO: 跳转到完整列表页
  console.log('查看全部:', type)
}

// 删除单条已完成记录
const deleteSingle = async (item: ApprovalRequest) => {
  if (!isFinalStatus(item.status)) {
    await appAlert('进行中的审批不能直接删除，请先撤回')
    return
  }
  const ok = await appConfirm(
    `确定删除这条审批记录吗？\n\n${item.title}\n状态：${getStatusLabel(item.status)}\n\n删除后不可恢复。`,
    { title: '删除确认', confirmText: '删除', cancelText: '取消' }
  )
  if (!ok) return

  const userId = getCurrentUserId()
  try {
    const res = await approvalApi.deleteRequest(item.id, userId)
    if (res.success) {
      initiatedRequests.value = initiatedRequests.value.filter((r) => r.id !== item.id)
      await loadData()
    } else {
      await appAlert('删除失败：' + (res.message || '未知错误'))
    }
  } catch (error) {
    console.error('删除失败:', error)
    await appAlert('删除失败，请重试')
  }
}

// 批量清理已完成记录
const cleanupCompleted = async () => {
  if (cleanupLoading.value) return
  const userId = getCurrentUserId()

  cleanupLoading.value = true
  try {
    // 1) 先 dry-run 获取精确待清理数量
    const preview = await approvalApi.cleanupCompleted(userId, {
      statuses: [...FINAL_STATUSES],
      dryRun: true
    })
    const matched = preview.success ? preview.data?.matched ?? 0 : 0
    if (!preview.success) {
      await appAlert('清理检查失败：' + (preview.message || '未知错误'))
      return
    }
    if (matched === 0) {
      await appAlert('暂无可清理的已完成记录')
      return
    }

    // 2) 二次确认
    const ok = await appConfirm(
      `将永久删除 ${matched} 条已完成（通过 / 拒绝 / 撤回 / 取消）的审批记录，删除后不可恢复，确定继续吗？`,
      { title: '清理确认', confirmText: `删除 ${matched} 条`, cancelText: '取消' }
    )
    if (!ok) return

    // 3) 真正执行
    const res = await approvalApi.cleanupCompleted(userId, {
      statuses: [...FINAL_STATUSES],
      dryRun: false
    })
    if (res.success) {
      const deleted = res.data?.deleted ?? 0
      await appAlert(`已清理 ${deleted} 条记录`)
      await loadData()
    } else {
      await appAlert('清理失败：' + (res.message || '未知错误'))
    }
  } catch (error) {
    console.error('清理失败:', error)
    await appAlert('清理失败，请重试')
  } finally {
    cleanupLoading.value = false
  }
}

// 工具函数
const getBusinessIcon = (type: string) => {
  const icons: Record<string, string> = {
    shipment: 'fa-truck',
    purchase: 'fa-shopping-cart',
    expense: 'fa-money',
    contract: 'fa-file-text'
  }
  return `fa ${icons[type] || 'fa-file'}`
}

const getBusinessLabel = (type: string) => {
  const labels: Record<string, string> = {
    shipment: '出货单',
    purchase: '采购',
    expense: '费用',
    contract: '合同'
  }
  return labels[type] || type
}

const getStatusLabel = (status: string) => {
  const labels: Record<string, string> = {
    pending: '待审批',
    in_progress: '审批中',
    approved: '已通过',
    rejected: '已拒绝',
    withdrawn: '已撤回'
  }
  return labels[status] || status
}

const getActionIcon = (action: string) => {
  const icons: Record<string, string> = {
    approve: 'fa-check',
    reject: 'fa-times',
    transfer: 'fa-exchange',
    withdraw: 'fa-undo'
  }
  return `fa ${icons[action] || 'fa-info'}`
}

const formatTime = (isoString: string) => {
  if (!isoString) return ''
  const date = new Date(isoString)
  return date.toLocaleString('zh-CN')
}

onMounted(() => {
  loadData()
})
</script>

<style scoped>
.approval-workspace-view {
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

/* 统计卡片 */
.stats-cards {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}

.stat-card {
  background: white;
  border-radius: 8px;
  padding: 20px;
  display: flex;
  align-items: center;
  gap: 16px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.stat-icon {
  width: 48px;
  height: 48px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
}

.stat-card.pending .stat-icon {
  background: #fef3c7;
  color: #d97706;
}

.stat-card.initiated .stat-icon {
  background: #dbeafe;
  color: #2563eb;
}

.stat-card.approved .stat-icon {
  background: #d1fae5;
  color: #059669;
}

.stat-card.rejected .stat-icon {
  background: #fee2e2;
  color: #dc2626;
}

.stat-info {
  flex: 1;
}

.stat-value {
  font-size: 28px;
  font-weight: bold;
  color: #1f2937;
}

.stat-label {
  font-size: 14px;
  color: #6b7280;
  margin-top: 4px;
}

/* 区块 */
.section {
  background: white;
  border-radius: 8px;
  padding: 20px;
  margin-bottom: 24px;
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

.section-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.btn-link {
  background: none;
  border: none;
  color: #2563eb;
  cursor: pointer;
  font-size: 14px;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 8px;
  border-radius: 4px;
  transition: background 0.15s;
}

.btn-link:hover:not(:disabled) {
  background: #eff6ff;
}

.btn-link:disabled {
  color: #9ca3af;
  cursor: not-allowed;
}

.btn-link.btn-cleanup {
  color: #dc2626;
}

.btn-link.btn-cleanup:hover:not(:disabled) {
  background: #fef2f2;
}

.btn-link.btn-cleanup:disabled {
  color: #9ca3af;
}

.count-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 18px;
  height: 18px;
  padding: 0 5px;
  margin-left: 2px;
  background: #fee2e2;
  color: #dc2626;
  border-radius: 9px;
  font-size: 11px;
  font-weight: 600;
  line-height: 1;
}

.btn-link.btn-cleanup:disabled .count-badge {
  background: #f3f4f6;
  color: #9ca3af;
}

/* 请求列表 */
.request-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.request-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
}

.request-item:hover {
  border-color: #2563eb;
  background: #f9fafb;
}

.request-left {
  display: flex;
  gap: 12px;
  align-items: center;
  flex: 1;
}

.request-icon {
  width: 40px;
  height: 40px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f3f4f6;
  color: #6b7280;
  font-size: 18px;
}

.request-info {
  flex: 1;
}

.request-title {
  font-size: 16px;
  color: #1f2937;
  margin-bottom: 4px;
}

.request-meta {
  display: flex;
  gap: 12px;
  font-size: 13px;
  color: #6b7280;
}

.request-no {
  font-family: monospace;
}

.request-status {
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
}

.request-status.pending {
  background: #fef3c7;
  color: #d97706;
}

.request-status.in_progress {
  background: #dbeafe;
  color: #2563eb;
}

.request-status.approved {
  background: #d1fae5;
  color: #059669;
}

.request-status.rejected {
  background: #fee2e2;
  color: #dc2626;
}

.request-actions {
  display: flex;
  gap: 8px;
}

.btn-approve, .btn-reject {
  width: 32px;
  height: 32px;
  border-radius: 6px;
  border: none;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
}

.btn-approve {
  background: #d1fae5;
  color: #059669;
}

.btn-approve:hover {
  background: #059669;
  color: white;
}

.btn-reject {
  background: #fee2e2;
  color: #dc2626;
}

.btn-reject:hover {
  background: #dc2626;
  color: white;
}

.request-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.request-current-node {
  font-size: 13px;
  color: #6b7280;
  display: flex;
  align-items: center;
  gap: 4px;
}

.btn-delete {
  width: 32px;
  height: 32px;
  border-radius: 6px;
  border: 1px solid transparent;
  background: transparent;
  color: #9ca3af;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  transition: all 0.15s;
}

.btn-delete:hover {
  background: #fef2f2;
  border-color: #fecaca;
  color: #dc2626;
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
  width: 800px;
  max-height: 80vh;
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

.detail-section {
  margin-bottom: 24px;
}

.detail-section h4 {
  font-size: 16px;
  color: #1f2937;
  margin: 0 0 12px 0;
  padding-bottom: 8px;
  border-bottom: 1px solid #e5e7eb;
}

.detail-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}

.detail-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.detail-item.full-width {
  grid-column: 1 / -1;
}

.detail-item label {
  font-size: 13px;
  color: #6b7280;
}

.detail-item span, .detail-item p {
  font-size: 14px;
  color: #1f2937;
}

.status-tag {
  display: inline-block;
  padding: 4px 12px;
  border-radius: 4px;
  font-size: 13px;
}

.status-tag.pending {
  background: #fef3c7;
  color: #d97706;
}

.status-tag.in_progress {
  background: #dbeafe;
  color: #2563eb;
}

.status-tag.approved {
  background: #d1fae5;
  color: #059669;
}

.status-tag.rejected {
  background: #fee2e2;
  color: #dc2626;
}

/* 时间轴 */
.timeline {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.timeline-item {
  display: flex;
  gap: 12px;
}

.timeline-dot {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  font-size: 14px;
}

.timeline-dot.approve {
  background: #d1fae5;
  color: #059669;
}

.timeline-dot.reject {
  background: #fee2e2;
  color: #dc2626;
}

.timeline-dot.transfer {
  background: #dbeafe;
  color: #2563eb;
}

.timeline-content {
  flex: 1;
  background: #f9fafb;
  padding: 12px;
  border-radius: 8px;
}

.timeline-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
  font-size: 14px;
}

.node-name {
  font-weight: 500;
  color: #1f2937;
}

.time {
  color: #6b7280;
  font-size: 12px;
}

.timeline-body {
  font-size: 14px;
  color: #4b5563;
}

.opinion {
  margin-top: 4px;
  padding: 8px;
  background: white;
  border-radius: 4px;
  font-style: italic;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 20px;
  border-top: 1px solid #e5e7eb;
}

.btn {
  padding: 10px 20px;
  border-radius: 6px;
  border: none;
  cursor: pointer;
  font-size: 14px;
  display: flex;
  align-items: center;
  gap: 6px;
}

.btn-approve {
  background: #059669;
  color: white;
}

.btn-reject {
  background: #dc2626;
  color: white;
}
</style>
