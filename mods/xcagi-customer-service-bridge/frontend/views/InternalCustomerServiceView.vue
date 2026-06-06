<template>
  <div class="page-view cs-page" id="view-internal-customer-service">
    <div class="page-content">
      <div class="page-header">
        <div>
          <h2>内部客服</h2>
          <p class="page-subtitle">管理员总机 · 受理各企业分机发来的联络</p>
        </div>
        <div class="header-actions">
          <button class="btn btn-sm btn-secondary" type="button" @click="refresh">刷新</button>
          <button class="btn btn-sm btn-primary" type="button" @click="goToChat">进入对话</button>
        </div>
      </div>

      <div v-if="stats" class="stats-row">
        <div class="stat-card">
          <span class="stat-num">{{ stats.pending }}</span>
          <span class="stat-label">待受理</span>
        </div>
        <div class="stat-card">
          <span class="stat-num">{{ stats.processing }}</span>
          <span class="stat-label">处理中</span>
        </div>
        <div class="stat-card">
          <span class="stat-num">{{ stats.resolved }}</span>
          <span class="stat-label">已回复</span>
        </div>
        <div class="stat-card muted">
          <span class="stat-num">{{ stats.total }}</span>
          <span class="stat-label">累计</span>
        </div>
      </div>

      <div v-if="instances.length" class="instance-chips">
        <button
          type="button"
          class="chip"
          :class="{ active: !filterInstanceId }"
          @click="filterInstanceId = ''"
        >
          全部企业
        </button>
        <button
          v-for="inst in instances"
          :key="inst.instance_id"
          type="button"
          class="chip"
          :class="{ active: filterInstanceId === inst.instance_id }"
          @click="filterInstanceId = inst.instance_id"
        >
          {{ inst.instance_name }}
          <span v-if="inst.pending_count" class="chip-badge">{{ inst.pending_count }}</span>
        </button>
      </div>

      <div class="card section-card">
        <div class="section-header">
          <span class="section-title">📡 企业联络收件箱</span>
          <span class="badge badge-warn">{{ inboxPendingCount }}</span>
        </div>
        <div class="filter-bar">
          <label>状态</label>
          <select v-model="filterStatus" @change="loadInbox">
            <option value="">全部</option>
            <option value="pending">待受理</option>
            <option value="processing">处理中</option>
            <option value="resolved">已回复</option>
            <option value="closed">已关闭</option>
          </select>
        </div>
        <div v-if="loadingRequests" class="loading-hint">加载中…</div>
        <div v-else-if="!requests.length" class="empty-hint">暂无企业联络</div>
        <ul v-else class="item-list">
          <li v-for="req in requests" :key="req.id" class="item-row service-request-row">
            <div class="req-main">
              <span class="req-source">{{ req.source_instance_name }}</span>
              <span class="req-type-badge" :class="'type-' + req.request_type">{{ requestTypeLabel(req.request_type) }}</span>
              <span class="item-name">{{ req.title }}</span>
              <span class="req-priority" :class="'priority-' + req.priority">{{ priorityLabel(req.priority) }}</span>
            </div>
            <div class="req-actions">
              <span class="req-status" :class="'st-' + req.status">{{ statusLabel(req.status) }}</span>
              <button
                v-if="req.status === 'pending' || req.status === 'processing'"
                class="btn btn-xs btn-primary"
                type="button"
                @click="openRespondModal(req)"
              >
                回复
              </button>
              <button
                v-else
                class="btn btn-xs btn-secondary"
                type="button"
                @click="openRespondModal(req)"
              >
                查看
              </button>
            </div>
          </li>
        </ul>
      </div>

      <div class="card section-card">
        <div class="section-header">
          <span class="section-title">💬 客户微信摘要</span>
          <span class="badge">{{ wechatItems.length }}</span>
        </div>
        <div v-if="loadingWechat" class="loading-hint">加载中…</div>
        <div v-else-if="!wechatItems.length" class="empty-hint">暂无星标消息</div>
        <ul v-else class="item-list compact">
          <li v-for="item in wechatItems.slice(0, 6)" :key="item.id || item.timestamp" class="item-row">
            <span class="item-name">{{ item.nickname || item.contact_name || '联系人' }}</span>
            <span class="item-text">{{ (item.content || item.message || '').slice(0, 50) }}</span>
          </li>
        </ul>
      </div>

      <div class="card section-card">
        <div class="section-header">
          <span class="section-title">✅ 审批待办</span>
          <span class="badge badge-warn">{{ pendingApprovals.length }}</span>
        </div>
        <div v-if="loadingApprovals" class="loading-hint">加载中…</div>
        <div v-else-if="!pendingApprovals.length" class="empty-hint">无待处理审批</div>
        <ul v-else class="item-list compact">
          <li v-for="ap in pendingApprovals.slice(0, 5)" :key="ap.id" class="item-row">
            <span class="item-name">{{ ap.title || ap.request_type || '审批单' }}</span>
            <button class="btn btn-xs btn-primary" type="button" @click="goToApproval">处理</button>
          </li>
        </ul>
      </div>

      <div class="card section-card">
        <div class="section-header">
          <span class="section-title">🖥️ 对接服务器</span>
        </div>
        <div class="server-info">
          <code class="info-code">ssh -o StrictHostKeyChecking=no root@119.27.178.147</code>
          <button class="btn btn-xs btn-secondary" type="button" @click="copySshCmd">复制</button>
          <span class="info-desc">管理员运维预留，用于协助企业侧对接</span>
        </div>
      </div>
    </div>

    <div v-if="respondModal.visible" class="modal-overlay" @click.self="respondModal.visible = false">
      <div class="modal-content">
        <div class="modal-header">
          <h3>{{ respondModal.readOnly ? '联络详情' : '回复企业联络' }}</h3>
          <button class="modal-close" type="button" @click="respondModal.visible = false">&times;</button>
        </div>
        <div class="modal-body">
          <div class="req-detail">
            <p><strong>企业：</strong>{{ respondModal.request?.source_instance_name }}</p>
            <p><strong>分机 ID：</strong><code>{{ respondModal.request?.source_instance_id }}</code></p>
            <p><strong>标题：</strong>{{ respondModal.request?.title }}</p>
            <p><strong>描述：</strong>{{ respondModal.request?.description || '无' }}</p>
          </div>
          <template v-if="!respondModal.readOnly">
            <div class="form-group">
              <label>回复内容</label>
              <textarea v-model="respondModal.response" rows="4" placeholder="输入给企业的回复…" />
            </div>
            <div class="form-group">
              <label>处理状态</label>
              <select v-model="respondModal.status">
                <option value="processing">处理中</option>
                <option value="resolved">已解决</option>
                <option value="closed">已关闭</option>
              </select>
            </div>
          </template>
          <div v-else-if="respondModal.request?.response" class="admin-reply-box">
            <strong>已回复：</strong>{{ respondModal.request.response }}
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn btn-sm btn-secondary" type="button" @click="respondModal.visible = false">关闭</button>
          <button
            v-if="!respondModal.readOnly"
            class="btn btn-sm btn-primary"
            type="button"
            :disabled="submitting || !respondModal.response.trim()"
            @click="submitResponse"
          >
            提交回复
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { get } from '@/api'
import { useServiceBridge, type ServiceRequestRecord } from '@/composables/useServiceBridge'

const router = useRouter()

const REQUEST_TYPE_LABELS: Record<string, string> = {
  建议: '建议',
  问题: '问题',
  general: '一般咨询',
  需求: '需求',
  审批: '审批协助',
  资源: '资源申请',
}

function requestTypeLabel(raw: string | undefined): string {
  const key = String(raw || '').trim()
  return REQUEST_TYPE_LABELS[key] || key || '—'
}

const {
  requests,
  stats,
  instances,
  loadingRequests,
  loadingStats,
  loadingInstances,
  submitting,
  loadRequests,
  loadStats,
  loadInstances,
  respondToRequest,
  serviceBridgePriorityLabel,
  serviceBridgeStatusLabel,
} = useServiceBridge()

const filterInstanceId = ref('')
const filterStatus = ref('')
const wechatItems = ref<any[]>([])
const pendingApprovals = ref<any[]>([])
const loadingWechat = ref(false)
const loadingApprovals = ref(false)

const respondModal = reactive({
  visible: false,
  readOnly: false,
  request: null as ServiceRequestRecord | null,
  response: '',
  status: 'resolved',
})

const inboxPendingCount = computed(() => requests.value.filter((r) => r.status === 'pending').length)
const priorityLabel = serviceBridgePriorityLabel
const statusLabel = serviceBridgeStatusLabel

async function loadInbox() {
  const params: Record<string, string> = {}
  if (filterInstanceId.value) params.source_instance_id = filterInstanceId.value
  if (filterStatus.value) params.status = filterStatus.value
  await loadRequests(params)
}

async function loadWechat() {
  loadingWechat.value = true
  try {
    const res = await get('/api/wechat/starred-messages', { limit: 8 })
    wechatItems.value = res?.data || res?.messages || res?.items || []
  } catch {
    wechatItems.value = []
  } finally {
    loadingWechat.value = false
  }
}

async function loadApprovals() {
  loadingApprovals.value = true
  try {
    const res = await get('/api/approval/requests', { status: 'pending', per_page: 8 })
    pendingApprovals.value = res?.data || res?.requests || []
  } catch {
    pendingApprovals.value = []
  } finally {
    loadingApprovals.value = false
  }
}

async function refresh() {
  await Promise.all([loadStats(), loadInstances(), loadInbox(), loadWechat(), loadApprovals()])
}

function openRespondModal(req: ServiceRequestRecord) {
  respondModal.request = req
  respondModal.response = req.response || ''
  respondModal.status = req.status === 'pending' ? 'processing' : 'resolved'
  respondModal.readOnly = req.status === 'resolved' || req.status === 'closed'
  respondModal.visible = true
}

async function submitResponse() {
  if (!respondModal.request || !respondModal.response.trim()) return
  await respondToRequest(respondModal.request.id, {
    response: respondModal.response.trim(),
    status: respondModal.status,
    responded_by: 'admin',
  })
  respondModal.visible = false
  await refresh()
}

function goToChat() {
  router.push({ name: 'chat' })
}

function goToApproval() {
  router.push({ name: 'approval-hub' })
}

async function copySshCmd() {
  try {
    await navigator.clipboard.writeText('ssh -o StrictHostKeyChecking=no root@119.27.178.147')
    alert('已复制到剪贴板')
  } catch {
    alert('复制失败，请手动复制')
  }
}

watch(filterInstanceId, () => {
  void loadInbox()
})

onMounted(refresh)
</script>

<style scoped>
.cs-page .page-header { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; }
.page-subtitle { margin: 4px 0 0; font-size: 13px; color: #6c757d; font-weight: 400; }
.stats-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin-bottom: 14px; }
.stat-card { background: #fff; border: 1px solid #e8e8e8; border-radius: 8px; padding: 12px; text-align: center; }
.stat-card.muted { opacity: 0.85; }
.stat-num { display: block; font-size: 22px; font-weight: 700; color: #4a6cf7; }
.stat-label { font-size: 12px; color: #888; }
.instance-chips { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 14px; }
.chip {
  border: 1px solid #dce4f7; background: #f8f9fa; border-radius: 16px;
  padding: 4px 12px; font-size: 12px; cursor: pointer;
}
.chip.active { background: #4a6cf7; color: #fff; border-color: #4a6cf7; }
.chip-badge { margin-left: 4px; background: #ff9800; color: #fff; border-radius: 8px; padding: 0 5px; font-size: 10px; }
.header-actions { display: flex; gap: 8px; flex-shrink: 0; }
.section-card { margin-bottom: 16px; }
.section-header { display: flex; align-items: center; gap: 8px; margin-bottom: 12px; font-weight: 600; }
.filter-bar { display: flex; align-items: center; gap: 8px; margin-bottom: 10px; font-size: 13px; }
.filter-bar select { border: 1px solid #ddd; border-radius: 6px; padding: 4px 8px; }
.badge { background: #e9ecef; color: #495057; padding: 2px 8px; border-radius: 12px; font-size: 12px; }
.badge-warn { background: #fff3cd; color: #856404; }
.item-list { list-style: none; padding: 0; margin: 0; }
.item-list.compact .item-row { padding: 5px 0; }
.item-row { display: flex; align-items: center; gap: 10px; padding: 8px 4px; border-bottom: 1px solid #f0f0f0; font-size: 13px; }
.item-row:last-child { border-bottom: none; }
.req-main { display: flex; align-items: center; gap: 8px; flex: 1; min-width: 0; flex-wrap: wrap; }
.req-source { font-weight: 600; color: #4a6cf7; font-size: 12px; }
.item-name { font-weight: 500; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 200px; }
.item-text { flex: 1; color: #666; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.req-type-badge { font-size: 11px; padding: 1px 6px; border-radius: 8px; background: #e8f4fd; color: #1976d2; }
.type-建议 { background: #e8f5e9; color: #2e7d32; }
.type-问题 { background: #fce4ec; color: #c62828; }
.req-priority { font-size: 11px; padding: 1px 6px; border-radius: 8px; }
.priority-urgent { background: #fce4ec; color: #c62828; font-weight: 600; }
.priority-high { background: #fff3e0; color: #e65100; }
.req-actions { display: flex; align-items: center; gap: 6px; }
.req-status { font-size: 11px; padding: 1px 6px; border-radius: 8px; }
.st-pending { background: #fff3cd; color: #856404; }
.st-processing { background: #ffe0b2; color: #e65100; }
.st-resolved { background: #e8f5e9; color: #2e7d32; }
.st-closed { background: #f5f5f5; color: #757575; }
.loading-hint, .empty-hint { color: #999; font-size: 13px; padding: 8px 0; }
.server-info { display: flex; align-items: center; flex-wrap: wrap; gap: 8px; font-size: 13px; }
.info-code { background: #f5f5f5; padding: 4px 8px; border-radius: 4px; font-family: monospace; }
.info-desc { color: #999; font-size: 12px; width: 100%; }
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.4); display: flex; align-items: center; justify-content: center; z-index: 1000; }
.modal-content { background: #fff; border-radius: 12px; width: 520px; max-width: 92vw; box-shadow: 0 8px 32px rgba(0,0,0,0.15); }
.modal-header { display: flex; align-items: center; justify-content: space-between; padding: 16px 20px; border-bottom: 1px solid #eee; }
.modal-header h3 { margin: 0; font-size: 16px; }
.modal-close { background: none; border: none; font-size: 20px; cursor: pointer; color: #999; }
.modal-body { padding: 20px; }
.modal-footer { display: flex; justify-content: flex-end; gap: 8px; padding: 12px 20px; border-top: 1px solid #eee; }
.req-detail { margin-bottom: 12px; padding: 12px; background: #f8f9fa; border-radius: 8px; }
.req-detail p { margin: 4px 0; font-size: 13px; }
.form-group { margin-bottom: 12px; }
.form-group label { display: block; font-size: 13px; font-weight: 500; margin-bottom: 4px; }
.form-group textarea, .form-group select { width: 100%; border: 1px solid #ddd; border-radius: 6px; padding: 8px; font-size: 13px; box-sizing: border-box; }
.admin-reply-box { padding: 12px; background: #e8f5e9; border-radius: 8px; font-size: 13px; }
.btn-xs { padding: 2px 8px; font-size: 12px; }
</style>
