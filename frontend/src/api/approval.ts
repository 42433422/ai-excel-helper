/**
 * 审批系统 API 服务
 * 对接后端 FastAPI 审批接口
 */

import { api } from './core'
import { resolveApprovalApiPath } from '@/utils/approvalPaths'

const ap = (path: string) => resolveApprovalApiPath(path)

/** 后端 ApprovalListResponse 的 data 为数组，与视图中 data.requests / data.flows 对齐 */
function withRequestList<T extends Record<string, unknown>>(res: T | null | undefined) {
  if (!res || typeof res !== 'object') {
    return { success: false, message: '无效响应', data: { requests: [] as ApprovalRequest[] } }
  }
  const raw = res as { success?: boolean; data?: unknown }
  const list = Array.isArray(raw.data) ? raw.data : []
  return { ...raw, data: { requests: list as ApprovalRequest[] } }
}

function withFlowList<T extends Record<string, unknown>>(res: T | null | undefined) {
  if (!res || typeof res !== 'object') {
    return { success: false, message: '无效响应', data: { flows: [] as ApprovalFlow[] } }
  }
  const raw = res as { success?: boolean; data?: unknown }
  const list = Array.isArray(raw.data) ? raw.data : []
  return { ...raw, data: { flows: list as ApprovalFlow[] } }
}

export interface ApprovalFlow {
  id: number
  flow_key: string
  flow_name: string
  description?: string
  business_type: string
  is_active: boolean
  nodes?: ApprovalFlowNode[]
}

export interface ApprovalFlowNode {
  id: number
  flow_id: number
  node_name: string
  node_order: number
  node_type: string
  approver_type: string
  approver_ids: number[]
  is_active: boolean
}

export interface ApprovalRequest {
  id: number
  request_no: string
  flow_id: number
  business_type: string
  business_id?: number
  title: string
  description?: string
  applicant_id: number
  status: string
  current_node_id?: number
  current_node_name?: string
  current_approvers?: number[]
  created_at: string
  approved_at?: string
  records?: ApprovalRecord[]
}

export interface ApprovalRecord {
  id: number
  request_id: number
  node_id: number
  node_name: string
  approver_id: number
  approver_name?: string
  action: string
  opinion?: string
  created_at: string
}

export interface ApprovalStats {
  pending: number
  initiated: number
  approved: number
  rejected: number
}

/**
 * 审批 API 服务
 */
export const approvalApi = {
  /**
   * 获取待我审批的请求
   */
  async getPendingApprovals(userId: number) {
    try {
      const data = await api.get(
        ap('/api/approval/requests'),
        { approver_id: userId, page: 1, page_size: 200 },
        { headers: { 'X-User-ID': userId.toString() } }
      )
      return withRequestList(data)
    } catch (error) {
      console.error('获取待审批列表失败:', error)
      return { success: false, message: '获取待审批列表失败', data: { requests: [] as ApprovalRequest[] } }
    }
  },

  /**
   * 获取我发起的审批请求
   */
  async getMyRequests(userId: number) {
    try {
      const data = await api.get(
        ap('/api/approval/requests'),
        { applicant_id: userId, page: 1, page_size: 500 },
        { headers: { 'X-User-ID': userId.toString() } }
      )
      return withRequestList(data)
    } catch (error) {
      console.error('获取我的请求失败:', error)
      return { success: false, message: '获取我的请求失败', data: { requests: [] as ApprovalRequest[] } }
    }
  },

  /**
   * 获取审批请求详情
   */
  async getRequestDetails(requestId: number) {
    try {
      const data = await api.get(ap(`/api/approval/requests/${requestId}`))
      return data
    } catch (error) {
      console.error('获取请求详情失败:', error)
      return { success: false, message: '获取请求详情失败' }
    }
  },

  /**
   * 审批通过
   */
  async approve(requestId: number, approverId: number, opinion: string) {
    try {
      const data = await api.post(
        ap(`/api/approval/requests/${requestId}/approve`),
        {
          approver_id: approverId,
          opinion: opinion
        },
        {
          headers: { 'X-User-ID': approverId.toString() }
        }
      )
      return data
    } catch (error) {
      console.error('审批通过失败:', error)
      return { success: false, message: '审批通过失败' }
    }
  },

  /**
   * 审批拒绝
   */
  async reject(requestId: number, approverId: number, reason: string) {
    try {
      const data = await api.post(
        ap(`/api/approval/requests/${requestId}/reject`),
        {
          approver_id: approverId,
          reason: reason
        },
        {
          headers: { 'X-User-ID': approverId.toString() }
        }
      )
      return data
    } catch (error) {
      console.error('审批拒绝失败:', error)
      return { success: false, message: '审批拒绝失败' }
    }
  },

  /**
   * 创建审批流程
   */
  async createFlow(flowData: {
    flow_name: string
    flow_key: string
    business_type: string
    description?: string
    is_active: boolean
  }, nodes: Array<{
    node_name: string
    node_type: string
    node_order: number
    approver_type: string
    approver_ids: number[]
    is_active: boolean
  }>) {
    try {
      const data = await api.post(ap('/api/approval/flows'), {
        flow: flowData,
        nodes: nodes
      })
      return data
    } catch (error) {
      console.error('创建审批流程失败:', error)
      return { success: false, message: '创建审批流程失败' }
    }
  },

  /**
   * 获取审批流程列表
   */
  async getFlowList() {
    try {
      const data = await api.get(ap('/api/approval/flows'), { is_active: true })
      return withFlowList(data)
    } catch (error) {
      console.error('获取流程列表失败:', error)
      return { success: false, message: '获取流程列表失败' }
    }
  },

  /**
   * 提交审批请求
   */
  async submitRequest(data: {
    flow_key: string
    business_type: string
    business_id?: number
    business_data?: any
    title: string
    description?: string
  }) {
    try {
      const userId = localStorage.getItem('user_id') || '4'
      const result = await api.post(ap('/api/approval/requests'), data, {
        headers: { 'X-User-ID': userId }
      })
      return result
    } catch (error) {
      console.error('提交审批请求失败:', error)
      return { success: false, message: '提交审批请求失败' }
    }
  },

  /**
   * 撤回审批请求
   */
  async withdraw(requestId: number, userId: number) {
    try {
      const data = await api.post(
        ap(`/api/approval/requests/${requestId}/withdraw`),
        {},
        {
          headers: { 'X-User-ID': userId.toString() }
        }
      )
      return data
    } catch (error) {
      console.error('撤回请求失败:', error)
      return { success: false, message: '撤回请求失败' }
    }
  },

  /**
   * 删除单个审批记录（仅申请人本人，且必须为终态）
   */
  async deleteRequest(requestId: number, userId: number) {
    try {
      const data = await api.delete(
        ap(`/api/approval/requests/${requestId}`),
        {},
        {
          headers: { 'X-User-ID': userId.toString() }
        }
      )
      return data as { success: boolean; message?: string; data?: { deleted: number; request_id: number } }
    } catch (error) {
      console.error('删除审批记录失败:', error)
      return { success: false, message: '删除审批记录失败' }
    }
  },

  /**
   * 批量清理已完成的审批记录
   * @param userId   当前用户 ID
   * @param options  清理选项
   *   - statuses: 要清理的状态（默认 approved/rejected/withdrawn/cancelled 全部终态）
   *   - beforeDays: 只清理 N 天之前的记录；0/不传表示不限
   *   - dryRun: true 时仅返回匹配数量，不真正删除
   */
  async updateFlow(flowId: number, data: Partial<ApprovalFlow>) {
    try {
      return await api.put(ap(`/api/approval/flows/${flowId}`), data)
    } catch (error) {
      console.error('更新流程失败:', error)
      return { success: false, message: '更新流程失败' }
    }
  },

  async toggleFlowActive(flowId: number, isActive: boolean) {
    try {
      return await api.patch(ap(`/api/approval/flows/${flowId}/active`), { is_active: isActive })
    } catch (error) {
      console.error('切换流程状态失败:', error)
      return { success: false, message: '切换流程状态失败' }
    }
  },

  async deleteFlow(flowId: number) {
    try {
      return await api.delete(ap(`/api/approval/flows/${flowId}`))
    } catch (error) {
      console.error('删除流程失败:', error)
      return { success: false, message: '删除流程失败' }
    }
  },

  async cleanupCompleted(
    userId: number,
    options: {
      statuses?: string[]
      beforeDays?: number
      dryRun?: boolean
    } = {}
  ) {
    try {
      const data = await api.post(
        ap('/api/approval/requests/cleanup'),
        {
          statuses: options.statuses,
          before_days: options.beforeDays ?? 0,
          dry_run: options.dryRun ?? false,
          scope: 'self'
        },
        {
          headers: { 'X-User-ID': userId.toString() }
        }
      )
      return data as {
        success: boolean
        message?: string
        data?: {
          matched: number
          deleted: number
          dry_run: boolean
          statuses: string[]
          before_days: number | null
        }
      }
    } catch (error) {
      console.error('清理审批记录失败:', error)
      return { success: false, message: '清理审批记录失败' }
    }
  }
}
