/**
 * Workflow Employee Module Type Definitions
 */

export interface WorkflowEmployee {
  id: string
  name: string
  label: string
  isActive: boolean
  type: 'real_phone' | 'virtual' | 'hybrid'
  config?: EmployeeConfig
}

export interface EmployeeConfig {
  branchId: string
  triggers: BranchTrigger[]
  adbDeviceCheck: boolean
  callDetection: boolean
  autoAnswer: boolean
  voiceTranscription: boolean
  voiceReply: boolean
  statusPolling: boolean
  pollingInterval?: number
}

export interface BranchTrigger {
  id: string
  name: string
  type: 'fixed' | 'dynamic'
  status: 'active' | 'inactive' | 'pending' | 'error'
  description?: string
  order: number
  dependencies?: string[]
}

export interface WorkflowBranch {
  id: string
  title: string
  kind: 'fixed' | 'extension' | 'dynamic'
  isFixed: boolean
  triggers: BranchTrigger[]
  employees: WorkflowEmployee[]
  metadata?: {
    createdAt: string
    updatedAt: string
    createdBy?: string
  }
}

export interface ToggleEvent {
  employeeId: string
  active: boolean
  timestamp: string
}

export interface BranchActionEvent {
  branchId: string
  action: 'configure' | 'view-details' | 'click'
  timestamp: string
}
