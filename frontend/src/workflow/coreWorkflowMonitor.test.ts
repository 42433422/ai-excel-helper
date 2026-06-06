import { describe, expect, it } from 'vitest'
import { STAR_REFRESH_STORAGE_KEY } from '@/workflow/coreWorkflowPrefs'
import {
  buildCoreWorkflowMonitorLine,
  buildCoreWorkflowStepsForEmployee,
  computeCoreWorkflowProgressState,
  computeCoreWorkflowStageLine,
} from '@/workflow/coreWorkflowMonitor'

describe('coreWorkflowMonitor', () => {
  it('shipment_mgmt monitor line without audit', () => {
    const line = buildCoreWorkflowMonitorLine('shipment_mgmt')
    expect(line).toContain('开始打印')
  })

  it('label_print steps when signal present', () => {
    const steps = buildCoreWorkflowStepsForEmployee('label_print', {
      lastLabelPrint: { at: Date.now(), line: '测试：打印 10 张' },
    })
    expect(steps.some((s) => s.status === 'active')).toBe(true)
  })

  it('wechat_msg progress idle without lastWechat', () => {
    const steps = buildCoreWorkflowStepsForEmployee('wechat_msg', {})
    const prog = computeCoreWorkflowProgressState('wechat_msg', steps, {})
    expect(prog.workflowProgressStarted).toBe(false)
    expect(prog.progressPct).toBe(0)
  })

  it('receipt_confirm stage when feedback received', () => {
    const prev = localStorage.getItem(STAR_REFRESH_STORAGE_KEY)
    localStorage.setItem(STAR_REFRESH_STORAGE_KEY, '1')
    try {
      const stage = computeCoreWorkflowStageLine('receipt_confirm', {
        lastReceiptFeedback: { at: 1, line: '已收货' },
      })
      expect(stage).toContain('已收客户')
    } finally {
      if (prev == null) localStorage.removeItem(STAR_REFRESH_STORAGE_KEY)
      else localStorage.setItem(STAR_REFRESH_STORAGE_KEY, prev)
    }
  })
})
