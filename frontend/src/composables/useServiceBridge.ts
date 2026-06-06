import { ref } from 'vue'
import { get, post, put } from '@/api'

export type ServiceRequestRecord = {
  id: number
  source_instance_id: string
  source_instance_name: string
  request_type: string
  title: string
  description?: string | null
  priority: string
  status: string
  response?: string | null
  responded_by?: string | null
  responded_at?: string | null
  created_at?: string | null
  updated_at?: string | null
}

export type ServiceBridgeStats = {
  total: number
  pending: number
  processing: number
  resolved: number
}

export type ServiceBridgeInstanceSummary = {
  instance_id: string
  instance_name: string
  total_requests: number
  pending_count: number
}

const PRIORITY_LABELS: Record<string, string> = {
  low: '低',
  normal: '普通',
  high: '高',
  urgent: '紧急',
}

const STATUS_LABELS: Record<string, string> = {
  pending: '待受理',
  processing: '处理中',
  resolved: '已回复',
  closed: '已关闭',
}

export function formatServiceBridgeTime(ts: unknown): string {
  if (!ts) return ''
  try {
    const d =
      typeof ts === 'number'
        ? new Date(ts < 1e12 ? ts * 1000 : ts)
        : new Date(String(ts))
    return d.toLocaleString('zh-CN', {
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return ''
  }
}

export function serviceBridgePriorityLabel(p: string): string {
  return PRIORITY_LABELS[p] || p
}

export function serviceBridgeStatusLabel(status: string): string {
  return STATUS_LABELS[status] || status
}

export function useServiceBridge() {
  const requests = ref<ServiceRequestRecord[]>([])
  const stats = ref<ServiceBridgeStats | null>(null)
  const instances = ref<ServiceBridgeInstanceSummary[]>([])
  const loadingRequests = ref(false)
  const loadingStats = ref(false)
  const loadingInstances = ref(false)
  const submitting = ref(false)

  async function loadRequests(params: Record<string, unknown> = {}) {
    loadingRequests.value = true
    try {
      const res = await get('/api/service-bridge/requests', { per_page: 50, ...params })
      requests.value = (res?.data || []) as ServiceRequestRecord[]
    } catch {
      requests.value = []
    } finally {
      loadingRequests.value = false
    }
  }

  async function loadStats() {
    loadingStats.value = true
    try {
      const res = await get('/api/service-bridge/stats')
      stats.value = (res?.data || null) as ServiceBridgeStats | null
    } catch {
      stats.value = null
    } finally {
      loadingStats.value = false
    }
  }

  async function loadInstances() {
    loadingInstances.value = true
    try {
      const res = await get('/api/service-bridge/instances')
      instances.value = (res?.data || []) as ServiceBridgeInstanceSummary[]
    } catch {
      instances.value = []
    } finally {
      loadingInstances.value = false
    }
  }

  async function createRequest(payload: {
    source_instance_id: string
    source_instance_name: string
    request_type?: string
    title: string
    description?: string
    priority?: string
  }) {
    submitting.value = true
    try {
      const res = await post('/api/service-bridge/requests', payload)
      return res?.data as ServiceRequestRecord | undefined
    } finally {
      submitting.value = false
    }
  }

  /** 企业/太阳鸟发起联络：子实例走 outbox 转发主服务器，同机宿主直写 requests */
  async function createEnterpriseContact(payload: {
    source_instance_id: string
    source_instance_name: string
    request_type?: string
    title: string
    description?: string
    priority?: string
  }) {
    submitting.value = true
    try {
      try {
        const cfg = await get('/api/service-bridge/config')
        if (cfg?.data?.instance_id) {
          const res = await post('/api/service-bridge/outbox', {
            request_type: payload.request_type || 'general',
            title: payload.title,
            description: payload.description,
            priority: payload.priority || 'normal',
          })
          return res?.data as ServiceRequestRecord | undefined
        }
      } catch {
        /* 无 outbox 配置则直写宿主库 */
      }
      return await createRequest(payload)
    } finally {
      submitting.value = false
    }
  }

  async function respondToRequest(
    requestId: number,
    payload: { response: string; status: string; responded_by?: string },
  ) {
    submitting.value = true
    try {
      const res = await put(`/api/service-bridge/requests/${requestId}/respond`, payload)
      return res?.data as ServiceRequestRecord | undefined
    } finally {
      submitting.value = false
    }
  }

  return {
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
    createRequest,
    createEnterpriseContact,
    respondToRequest,
    formatServiceBridgeTime,
    serviceBridgePriorityLabel,
    serviceBridgeStatusLabel,
  }
}
