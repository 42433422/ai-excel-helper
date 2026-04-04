export interface ProductSpec {
  model: string | null
  quantity_tins: number | null
  tin_spec: number | null
}

export interface ShipmentCommand {
  action: 'add' | 'remove' | 'edit' | null
  product?: {
    model_number: string
    quantity_tins: number
    tin_spec: number
  }
  model?: string
}

const CN_NUMBERS: Record<string, number> = {
  '零': 0, '〇': 0, '一': 1, '二': 2, '两': 2, '三': 3,
  '四': 4, '五': 5, '六': 6, '七': 7, '八': 8, '九': 9
}

export function parseCnInt(token: string): number | null {
  const raw = String(token || '').trim()
  if (!raw) return null
  const t = raw.replace(/个/g, '').trim()
  if (!t) return null
  if (/^\d+$/.test(t)) return parseInt(t, 10)
  if (Object.prototype.hasOwnProperty.call(CN_NUMBERS, t)) return CN_NUMBERS[t]
  if (t === '十') return 10
  if (/^[一二两三四五六七八九]十$/.test(t)) return CN_NUMBERS[t[0]] * 10
  if (/^十[一二三四五六七八九]$/.test(t)) return 10 + CN_NUMBERS[t[1]]
  if (/^[一二两三四五六七八九]十[一二三四五六七八九]$/.test(t)) {
    return CN_NUMBERS[t[0]] * 10 + CN_NUMBERS[t[2]]
  }
  return null
}

export function normalizeModel(model: string): string {
  return String(model || '').trim().toUpperCase()
}

export function normalizeProductToken(value: string): string {
  return String(value || '').trim().toUpperCase().replace(/\s+/g, '').replace(/-/g, '')
}

export function toNumber(val: any): number | null {
  const n = Number(val)
  return Number.isFinite(n) ? n : null
}

export function extractModelQtySpec(text: string): ProductSpec | null {
  const t = String(text || '').trim()
  const normalizedText = t.replace(/[，,；;。]/g, ' ').replace(/\s+/g, ' ').trim()
  const q = '(\\d+|[一二两三四五六七八九十零〇]+)'
  const modelToken = '([0-9A-Za-z-]+)'
  const specToken = '(\\d+(?:\\.\\d+)?)'

  const p00 = normalizedText.match(
    new RegExp(`^(?:一?个|1个)?\\s*${q}\\s*桶\\s*${modelToken}\\s*规格\\s*${specToken}$`)
  )
  if (p00) {
    return {
      model: normalizeModel(p00[2]),
      quantity_tins: parseCnInt(p00[1]) || 1,
      tin_spec: Number(p00[3])
    }
  }

  const p00b = normalizedText.match(
    new RegExp(`^(?:一?个|1个)?\\s*${q}\\s*桶\\s*${modelToken}$`)
  )
  if (p00b) {
    return {
      model: normalizeModel(p00b[2]),
      quantity_tins: parseCnInt(p00b[1]) || 1,
      tin_spec: null
    }
  }

  const p00c = normalizedText.match(
    new RegExp(`^${q}\\s*桶\\s*规格\\s*${specToken}$`)
  )
  if (p00c) {
    return {
      model: null,
      quantity_tins: parseCnInt(p00c[1]) || 1,
      tin_spec: Number(p00c[2])
    }
  }

  const p00d = normalizedText.match(new RegExp(`^规格\\s*${specToken}$`))
  if (p00d) {
    return {
      model: null,
      quantity_tins: null,
      tin_spec: Number(p00d[1])
    }
  }

  const p0 = t.match(/([0-9A-Za-z-]+)\s*(?:改成|改为|改)\s*(\d+|[一二两三四五六七八九十零〇]+)\s*桶(?:\s*规格\s*(\d+(?:\.\d+)?))?/)
  if (p0) {
    return {
      model: normalizeModel(p0[1]),
      quantity_tins: parseCnInt(p0[2]) || 1,
      tin_spec: p0[3] ? Number(p0[3]) : null
    }
  }

  const p0b = t.match(/(?:把)?\s*([0-9A-Za-z-]+)\s*规格\s*(?:改成|改为|改)\s*(\d+(?:\.\d+)?)(?:\s*(\d+|[一二两三四五六七八九十零〇]+)\s*桶)?/)
  if (p0b) {
    return {
      model: normalizeModel(p0b[1]),
      quantity_tins: p0b[3] ? (parseCnInt(p0b[3]) || 1) : null,
      tin_spec: Number(p0b[2])
    }
  }

  const p1 = t.match(/(\d+|[一二两三四五六七八九十零〇]+)\s*桶\s*([0-9A-Za-z-]+)\s*规格\s*(\d+(?:\.\d+)?)/)
  if (p1) {
    return {
      model: normalizeModel(p1[2]),
      quantity_tins: parseCnInt(p1[1]) || 1,
      tin_spec: Number(p1[3])
    }
  }

  const p1b = t.match(/(\d+|[一二两三四五六七八九十零〇]+)\s*桶\s*([0-9A-Za-z-]+)/)
  if (p1b) {
    return {
      model: normalizeModel(p1b[2]),
      quantity_tins: parseCnInt(p1b[1]) || 1,
      tin_spec: null
    }
  }

  const p2 = t.match(/([0-9A-Za-z-]+)\s*(\d+|[一二两三四五六七八九十零〇]+)\s*桶(?:\s*规格\s*(\d+(?:\.\d+)?))?/)
  if (p2) {
    return {
      model: normalizeModel(p2[1]),
      quantity_tins: parseCnInt(p2[2]) || 1,
      tin_spec: p2[3] ? Number(p2[3]) : null
    }
  }

  const p3 = t.match(/([0-9A-Za-z-]+)\s*规格\s*(\d+(?:\.\d+)?)/)
  if (p3) {
    return {
      model: normalizeModel(p3[1]),
      quantity_tins: null,
      tin_spec: Number(p3[2])
    }
  }

  const p4 = t.match(/([0-9A-Za-z-]{2,})/)
  if (p4) {
    return { model: normalizeModel(p4[1]), quantity_tins: null, tin_spec: null }
  }

  return null
}

export function parseShipmentCommand(text: string): ShipmentCommand | null {
  const trimmed = text.trim()

  const addPatterns = [
    /^(?:再加|还要|继续加|再补|加上|增加|再来|再来个|来一桶)\s*(.+)$/,
    /^(?:.*?)(?:再加|还要|继续加|再补|加上|增加|再来|再来个|来一桶)\s*(.+)$/
  ]

  for (const pattern of addPatterns) {
    const match = trimmed.match(pattern)
    if (match) {
      const parsed = extractModelQtySpec(match[1])
      if (parsed && parsed.model) {
        return {
          action: 'add',
          product: {
            model_number: parsed.model,
            quantity_tins: parsed.quantity_tins || 1,
            tin_spec: parsed.tin_spec || 10
          }
        }
      }
    }
  }

  const removePatterns = [
    /^(?:删除|删掉|删|去掉|移除|减去|减)\s*(.+)$/,
    /^(?:把)?\s*([0-9A-Za-z-]+)\s*(?:删掉|删除|删|去掉|移除|减去|减)\s*$/
  ]

  for (const pattern of removePatterns) {
    const match = trimmed.match(pattern)
    if (match) {
      const model = normalizeModel(match[1] || match[2] || '')
      if (model) {
        return { action: 'remove', model }
      }
    }
  }

  const editPatterns = [
    /^(?:改成|改为|修改|改)\s*(.+)$/,
    /^(?:把)?\s*([0-9A-Za-z-]+)\s*规格\s*(?:改成|改为|改)\s*(\d+(?:\.\d+)?)(?:\s*(\d+|[一二两三四五六七八九十零〇]+)\s*桶)?\s*$/,
    /^([0-9A-Za-z-]+)\s*(?:改成|改为|改)\s*(.+)$/,
    /^(?:把)?\s*([0-9A-Za-z-]+)\s*(?:改成|改为|修改|改)\s*(.+)$/
  ]

  for (const pattern of editPatterns) {
    const match = trimmed.match(pattern)
    if (match) {
      const explicitModelMatch = trimmed.match(/^(?:把)?\s*([0-9A-Za-z-]{2,})\s*(?:规格\s*)?(?:改成|改为|修改|改)/)
      const explicitModel = normalizeModel(explicitModelMatch?.[1] || '')
      const editBodyMatch = trimmed.match(/(?:改成|改为|修改|改)\s*(.+)$/)
      const editBody = (editBodyMatch?.[1] || match[1] || match[2] || '').trim().replace(/^(?:一?个|1个)\s*/, '')
      const parsedFromBody = extractModelQtySpec(editBody)
      const parsedFromFull = extractModelQtySpec(trimmed)

      const model = parsedFromBody?.model || parsedFromFull?.model || explicitModel
      if (model) {
        return {
          action: 'edit',
          product: {
            model_number: model,
            quantity_tins: parsedFromBody?.quantity_tins ?? parsedFromFull?.quantity_tins ?? 1,
            tin_spec: parsedFromBody?.tin_spec ?? parsedFromFull?.tin_spec ?? 10
          }
        }
      }
    }
  }

  return { action: null }
}

export function isStartPrintMessage(message: string): boolean {
  const t = String(message || '').trim()
  return /^开始打印(?:吧|一下)?$/.test(t)
}

export function isProTaskMessage(message: string): boolean {
  if (typeof window.isProTaskAcquisitionMessage === 'function') {
    return window.isProTaskAcquisitionMessage(message)
  }
  return false
}

export function detectRuntimeModeCommand(message: string): 'set_work_mode' | 'show_monitor' | null {
  const text = String(message || '').trim().toLowerCase()
  if (!text) return null

  const compact = text.replace(/\s+/g, '')
  const wantsWorkMode = compact === '工作模式'
    || compact === '切换工作模式'
    || compact === '进入工作模式'
    || compact === 'workmode'
    || compact === 'switchtoworkmode'
    || compact === 'enterworkmode'
  const wantsMonitorMode = compact === '监控模式'
    || compact === '切换监控模式'
    || compact === '进入监控模式'
    || compact === 'monitormode'
    || compact === 'switchtomonitormode'
    || compact === 'entermonitormode'

  if (wantsWorkMode) return 'set_work_mode'
  if (wantsMonitorMode) return 'show_monitor'
  return null
}
