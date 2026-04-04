/** 打印完成后拉取出货记录并生成「统计 + 审计 + 保存/推送建议」文案（出货管理 AI 员工） */

export type ShipmentRecordRow = {
  id?: number
  purchase_unit?: string
  model_number?: string
  product_name?: string
  quantity_tins?: number
  status?: string
  created_at?: string | null
  printed_at?: string | null
}

function startOfTodayMs(): number {
  const d = new Date()
  d.setHours(0, 0, 0, 0)
  return d.getTime()
}

function parseCreatedMs(row: ShipmentRecordRow): number | null {
  const raw = row?.created_at
  if (!raw) return null
  const t = new Date(String(raw)).getTime()
  return Number.isFinite(t) ? t : null
}

export function summarizeShipmentRecordsForAudit(
  rows: ShipmentRecordRow[],
  purchaseUnit: string,
  orderId: number | null
): {
  total: number
  todayCount: number
  matchedRecord: ShipmentRecordRow | null
  headline: string
  detailLines: string[]
} {
  const unit = String(purchaseUnit || '').trim() || '（未填单位）'
  const list = Array.isArray(rows) ? rows : []
  const total = list.length
  const day0 = startOfTodayMs()
  let todayCount = 0
  for (const r of list) {
    const ms = parseCreatedMs(r)
    if (ms !== null && ms >= day0) todayCount += 1
  }

  let matched: ShipmentRecordRow | null = null
  if (orderId !== null && Number.isFinite(orderId)) {
    matched = list.find((r) => Number(r?.id) === Number(orderId)) || null
  }
  if (!matched && list.length) {
    matched = list[0]
  }

  const headline = `单位「${unit}」出货记录 ${total} 条（当前列表）· 今日新增约 ${todayCount} 条`

  const detailLines: string[] = [
    headline,
    '审计要点：发货单在「确认执行」生成时已写入出货记录表；打印完成表示物理单据/标签已输出，建议在「出货记录」页核对型号、桶数与打印状态是否与现场一致。',
  ]

  if (orderId !== null && Number.isFinite(orderId)) {
    detailLines.push(
      matched && Number(matched.id) === Number(orderId)
        ? `已匹配本次任务 record_id=${orderId}，与列表一致。`
        : `本次任务 record_id=${orderId}；若列表顶部 id 不一致，请在出货记录页按单位筛选后人工核对。`
    )
  } else {
    detailLines.push('本次任务未带回 record_id，请到出货记录页按单位与时间筛选核对。')
  }

  if (matched) {
    const st = String(matched.status || '').trim() || '—'
    const m = String(matched.model_number || '').trim() || '—'
    detailLines.push(`列表最新一条：id=${matched.id ?? '—'}，型号 ${m}，状态 ${st}。`)
  }

  detailLines.push(
    '保存建议：数据库已持久化；若需离线存档请在「出货记录」页导出 Excel。',
    '推送建议：可将导出文件或本段摘要通过微信等渠道发给仓库/财务；亦可在副窗查看本次助手推送。'
  )

  return {
    total,
    todayCount,
    matchedRecord: matched,
    headline,
    detailLines,
  }
}

export async function fetchShipmentRecordsForUnit(purchaseUnit: string): Promise<ShipmentRecordRow[]> {
  const u = String(purchaseUnit || '').trim()
  if (!u) return []
  try {
    const q = encodeURIComponent(u)
    const resp = await fetch(`/api/shipment/shipment-records/records?unit=${q}`)
    const data = await resp.json().catch(() => ({}))
    if (!resp.ok || data?.success === false) return []
    const arr = data?.data
    return Array.isArray(arr) ? arr : []
  } catch {
    return []
  }
}
