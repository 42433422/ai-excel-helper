/**
 * 判断微信星标消息是否值得走「发货单预览」接口（避免每条消息都打 /api/tools/execute）。
 */
export function shouldTryWechatShipmentPreview(
  text: string,
  ctx?: { intentLabel?: string; primaryIntent?: string; toolKey?: string }
): boolean {
  const t = String(text || '').trim()
  if (!t) return false

  if (/发货单|出货单|开单|做.?发货|来.?单|要数|配货|拣货|下单|订货/.test(t)) return true
  if (/\d+\s*桶/.test(t) && (/规格|型号|[A-Za-z]\d{2,}/.test(t))) return true

  const pi = String(ctx?.primaryIntent || '')
  if (/发货|出货|开单|shipment|delivery|order|下单/i.test(pi)) return true
  const tk = String(ctx?.toolKey || '')
  if (/shipment|delivery|发货|出货|开单/i.test(tk)) return true

  const label = String(ctx?.intentLabel || '')
  if (label.includes('发货/物流') && /单|桶|规格|型号|件|箱/.test(t)) return true

  return false
}
