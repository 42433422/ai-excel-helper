<template>
  <div class="page-view cs-page" id="view-enterprise-customer-service">
    <div class="page-content">
      <div class="page-header">
        <div>
          <h2>外部客服</h2>
          <p class="page-subtitle">
            企业对接分机（太阳鸟等）· 发起联络后由管理员在「内部客服」收件箱受理
          </p>
        </div>
        <div class="header-actions">
          <button class="btn btn-sm btn-secondary" type="button" @click="refresh">刷新</button>
          <button class="btn btn-sm btn-primary" type="button" @click="goToChat">进入对话</button>
        </div>
      </div>

      <div class="bridge-banner">
        <span class="bridge-label">本企业分机</span>
        <strong>{{ instanceName }}</strong>
        <code class="bridge-id">{{ instanceId }}</code>
      </div>

      <div class="card section-card">
        <div class="section-header">
          <span class="section-title">📞 发起联络</span>
        </div>
        <form class="compose-form" @submit.prevent="submitNewRequest">
          <div class="form-row">
            <label>类型</label>
            <select v-model="compose.request_type">
              <option value="建议">建议</option>
              <option value="问题">问题</option>
            </select>
          </div>
          <div class="form-row">
            <label>标题</label>
            <input v-model="compose.title" type="text" maxlength="256" placeholder="简要说明需管理员协助的事项" required />
          </div>
          <div class="form-row">
            <label>详情</label>
            <textarea v-model="compose.description" rows="3" placeholder="补充背景、期望处理时间等（可选）" />
          </div>
          <div class="form-row">
            <label>优先级</label>
            <select v-model="compose.priority">
              <option value="low">低</option>
              <option value="normal">普通</option>
              <option value="high">高</option>
              <option value="urgent">紧急</option>
            </select>
          </div>
          <div class="form-actions">
            <button class="btn btn-sm btn-primary" type="submit" :disabled="submitting || !compose.title.trim()">
              {{ submitting ? '提交中…' : '呼叫管理员' }}
            </button>
          </div>
        </form>
      </div>

      <div class="card section-card">
        <div class="section-header">
          <span class="section-title">📋 我的联络记录</span>
          <span class="badge badge-warn">{{ pendingCount }}</span>
          <span class="badge">{{ requests.length }}</span>
        </div>
        <div v-if="loadingRequests" class="loading-hint">加载中…</div>
        <div v-else-if="!requests.length" class="empty-hint">暂无联络记录，可在上方发起第一条请求</div>
        <ul v-else class="item-list">
          <li
            v-for="req in requests"
            :key="req.id"
            class="item-row service-request-row"
            @click="openDetail(req)"
          >
            <div class="req-main">
              <span class="req-type-badge" :class="'type-' + req.request_type">{{ requestTypeLabel(req.request_type) }}</span>
              <span class="item-name">{{ req.title }}</span>
              <span class="req-status" :class="'st-' + req.status">{{ statusLabel(req.status) }}</span>
            </div>
            <span class="item-time">{{ formatTime(req.created_at) }}</span>
          </li>
        </ul>
      </div>
    </div>

    <div v-if="detailModal.visible" class="modal-overlay" @click.self="detailModal.visible = false">
      <div class="modal-content">
        <div class="modal-header">
          <h3>联络详情</h3>
          <button class="modal-close" type="button" @click="detailModal.visible = false">&times;</button>
        </div>
        <div class="modal-body">
          <div class="req-detail">
            <p><strong>标题：</strong>{{ detailModal.request?.title }}</p>
            <p><strong>类型：</strong>{{ requestTypeLabel(detailModal.request?.request_type) }}</p>
            <p><strong>状态：</strong>{{ statusLabel(detailModal.request?.status) }}</p>
            <p><strong>优先级：</strong>{{ priorityLabel(detailModal.request?.priority) }}</p>
            <p><strong>描述：</strong>{{ detailModal.request?.description || '无' }}</p>
            <p v-if="detailModal.request?.response">
              <strong>管理员回复：</strong>{{ detailModal.request.response }}
            </p>
            <p v-else-if="detailModal.request?.status === 'pending'" class="hint-pending">
              已送达管理员总机，等待受理…
            </p>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn btn-sm btn-secondary" type="button" @click="detailModal.visible = false">关闭</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useServiceBridge, type ServiceRequestRecord } from '@/composables/useServiceBridge'
import { useServiceBridgeInstance } from '@/composables/useServiceBridgeInstance'

const router = useRouter()
const { instanceId, instanceName, persistInstanceSnapshot } = useServiceBridgeInstance()
const {
  requests,
  loadingRequests,
  submitting,
  loadRequests,
  createEnterpriseContact,
  formatServiceBridgeTime,
  serviceBridgePriorityLabel,
  serviceBridgeStatusLabel,
} = useServiceBridge()

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

const compose = reactive({
  request_type: '建议',
  title: '',
  description: '',
  priority: 'normal',
})

const detailModal = reactive({
  visible: false,
  request: null as ServiceRequestRecord | null,
})

const pendingCount = computed(() => requests.value.filter((r) => r.status === 'pending').length)

const formatTime = formatServiceBridgeTime
const priorityLabel = serviceBridgePriorityLabel
const statusLabel = serviceBridgeStatusLabel

async function refresh() {
  persistInstanceSnapshot()
  await loadRequests({ source_instance_id: instanceId.value })
}

async function submitNewRequest() {
  if (!compose.title.trim()) return
  persistInstanceSnapshot()
  await createEnterpriseContact({
    source_instance_id: instanceId.value,
    source_instance_name: instanceName.value,
    request_type: compose.request_type,
    title: compose.title.trim(),
    description: compose.description.trim() || undefined,
    priority: compose.priority,
  })
  compose.title = ''
  compose.description = ''
  await refresh()
}

function openDetail(req: ServiceRequestRecord) {
  detailModal.request = req
  detailModal.visible = true
}

function goToChat() {
  router.push({ name: 'chat' })
}

onMounted(refresh)
</script>

<style scoped>
.cs-page .page-header { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; }
.page-subtitle { margin: 4px 0 0; font-size: 13px; color: #6c757d; font-weight: 400; }
.bridge-banner {
  display: flex; align-items: center; flex-wrap: wrap; gap: 8px;
  padding: 10px 14px; margin-bottom: 16px;
  background: linear-gradient(90deg, #eef3ff, #f8f9fa);
  border-radius: 8px; border: 1px solid #dce4f7;
  font-size: 13px;
}
.bridge-label { color: #5c6bc0; font-weight: 600; }
.bridge-id { font-size: 11px; color: #888; background: #fff; padding: 2px 6px; border-radius: 4px; }
.header-actions { display: flex; gap: 8px; flex-shrink: 0; }
.section-card { margin-bottom: 16px; }
.section-header { display: flex; align-items: center; gap: 8px; margin-bottom: 12px; font-weight: 600; }
.section-title { font-size: 14px; }
.badge { background: #e9ecef; color: #495057; padding: 2px 8px; border-radius: 12px; font-size: 12px; }
.badge-warn { background: #fff3cd; color: #856404; }
.compose-form { display: flex; flex-direction: column; gap: 10px; }
.form-row { display: flex; flex-direction: column; gap: 4px; }
.form-row label { font-size: 12px; font-weight: 500; color: #555; }
.form-row input, .form-row select, .form-row textarea {
  border: 1px solid #ddd; border-radius: 6px; padding: 8px; font-size: 13px; box-sizing: border-box;
}
.form-actions { display: flex; justify-content: flex-end; }
.item-list { list-style: none; padding: 0; margin: 0; }
.service-request-row { cursor: pointer; }
.service-request-row:hover { background: #f8f9fa; }
.item-row { display: flex; align-items: center; gap: 10px; padding: 8px 4px; border-bottom: 1px solid #f0f0f0; font-size: 13px; }
.item-row:last-child { border-bottom: none; }
.req-main { display: flex; align-items: center; gap: 8px; flex: 1; min-width: 0; }
.item-name { font-weight: 500; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.item-time { color: #999; font-size: 12px; white-space: nowrap; }
.req-type-badge { font-size: 11px; padding: 1px 6px; border-radius: 8px; background: #e8f4fd; color: #1976d2; white-space: nowrap; }
.type-建议 { background: #e8f5e9; color: #2e7d32; }
.type-问题 { background: #fce4ec; color: #c62828; }
.type-general { background: #f5f5f5; color: #616161; }
.req-status { font-size: 11px; padding: 1px 6px; border-radius: 8px; white-space: nowrap; }
.st-pending { background: #fff3cd; color: #856404; }
.st-processing { background: #ffe0b2; color: #e65100; }
.st-resolved { background: #e8f5e9; color: #2e7d32; }
.st-closed { background: #f5f5f5; color: #757575; }
.loading-hint, .empty-hint { color: #999; font-size: 13px; padding: 8px 0; }
.hint-pending { color: #e65100; }
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.4); display: flex; align-items: center; justify-content: center; z-index: 1000; }
.modal-content { background: #fff; border-radius: 12px; width: 480px; max-width: 90vw; box-shadow: 0 8px 32px rgba(0,0,0,0.15); }
.modal-header { display: flex; align-items: center; justify-content: space-between; padding: 16px 20px; border-bottom: 1px solid #eee; }
.modal-header h3 { margin: 0; font-size: 16px; }
.modal-close { background: none; border: none; font-size: 20px; cursor: pointer; color: #999; }
.modal-body { padding: 20px; }
.modal-footer { display: flex; justify-content: flex-end; padding: 12px 20px; border-top: 1px solid #eee; }
.req-detail { padding: 12px; background: #f8f9fa; border-radius: 8px; }
.req-detail p { margin: 4px 0; font-size: 13px; }
</style>
