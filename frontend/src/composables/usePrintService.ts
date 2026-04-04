import { ref } from 'vue'

export interface PrintResult {
  success: boolean
  message: string
}

export interface PrintSummary {
  labelSuccess: number
  labelFailed: number
  shipmentPrinted: boolean
  shipmentMarked: boolean
  logs: string[]
}

export function usePrintService() {
  const isPrinting = ref(false)

  async function printLabel(filePath: string, copies: number = 1): Promise<PrintResult> {
    try {
      const resp = await fetch('/api/print/label', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ file_path: filePath, copies })
      })
      const data = await resp.json().catch(() => ({}))

      if (resp.ok && data?.success) {
        return { success: true, message: '标签打印成功' }
      } else {
        return {
          success: false,
          message: data?.message || `HTTP ${resp.status}`
        }
      }
    } catch (e) {
      return {
        success: false,
        message: e?.message || '未知错误'
      }
    }
  }

  async function printDocument(filePath: string): Promise<PrintResult> {
    try {
      const resp = await fetch('/api/print/document', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ file_path: filePath })
      })
      const data = await resp.json().catch(() => ({}))

      if (resp.ok && data?.success) {
        return { success: true, message: '发货单打印成功' }
      } else {
        return {
          success: false,
          message: data?.message || `HTTP ${resp.status}`
        }
      }
    } catch (e) {
      return {
        success: false,
        message: e?.message || '未知错误'
      }
    }
  }

  async function markAsPrinted(filePath: string, orderId?: number): Promise<PrintResult> {
    try {
      const payload: Record<string, any> = { file_path: filePath }
      if (orderId) {
        payload.order_id = orderId
      }

      const resp = await fetch('/api/shipment/print', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      })
      const data = await resp.json().catch(() => ({}))

      if (resp.ok && data?.success && data?.updated !== false) {
        return { success: true, message: '打印状态已更新' }
      } else {
        return {
          success: false,
          message: data?.message || '更新失败'
        }
      }
    } catch (e) {
      return {
        success: false,
        message: e?.message || '未知错误'
      }
    }
  }

  async function executePrintTask(
    labelPaths: string[],
    filePath: string,
    orderId?: number,
    purchaseUnit?: string
  ): Promise<PrintSummary> {
    isPrinting.value = true

    const summary: PrintSummary = {
      labelSuccess: 0,
      labelFailed: 0,
      shipmentPrinted: false,
      shipmentMarked: false,
      logs: []
    }

    for (const lp of labelPaths) {
      const result = await printLabel(lp)
      if (result.success) {
        summary.labelSuccess++
      } else {
        summary.labelFailed++
        summary.logs.push(`标签打印失败：${result.message}`)
      }
    }

    if (filePath) {
      const docResult = await printDocument(filePath)
      summary.shipmentPrinted = docResult.success

      if (!docResult.success) {
        summary.logs.push(`发货单打印失败：${docResult.message}`)
      }

      const markResult = await markAsPrinted(filePath, orderId)
      summary.shipmentMarked = markResult.success

      if (!markResult.success) {
        summary.logs.push(`打印状态更新失败：${markResult.message}`)
      }

      if (!orderId) {
        summary.logs.push('打印状态未落库：缺少记录ID')
      }
    }

    isPrinting.value = false
    return summary
  }

  function buildPrintSummaryMessage(
    summary: PrintSummary,
    labelCount: number,
    filePath?: string,
    purchaseUnit?: string
  ): string {
    const parts = ['打印执行完成']

    parts.push(`标签：${summary.labelSuccess}/${labelCount || 0} 成功`)

    if (filePath) {
      parts.push(`发货单：${summary.shipmentPrinted ? '已发送打印' : '失败'}`)
      parts.push(`状态：${summary.shipmentMarked ? '已标记已打印' : '未更新'}`)
    }

    if (summary.logs.length) {
      parts.push(`详情：${summary.logs.slice(0, 2).join('；')}`)
    }

    return parts.filter(Boolean).join('；')
  }

  return {
    isPrinting,
    printLabel,
    printDocument,
    markAsPrinted,
    executePrintTask,
    buildPrintSummaryMessage
  }
}
