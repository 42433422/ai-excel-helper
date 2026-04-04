/**
 * 微信客户消息本地预处理（关键词规则，不调用大模型）。
 * 后续可替换为后端 / LLM 分类接口。
 */
export function inferWechatCustomerIntent(text: string): { label: string; detail: string } {
  const t = String(text || '').trim()
  if (!t) return { label: '空消息', detail: '未识别到文本内容。' }
  if (/价格|多少钱|报价|询价|怎么卖|点数|优惠|折扣|单价|含税/.test(t)) {
    return {
      label: '询价/报价',
      detail: '客户可能在询问价格或优惠，建议在对话中确认型号与数量后再报价。'
    }
  }
  if (/发货|出货|单号|物流|快递|什么时候到|几时发|到货/.test(t)) {
    return {
      label: '发货/物流',
      detail: '与发货、物流进度相关，可核对订单与出库状态。'
    }
  }
  if (/收货|到货|确认|签收|对账|入库/.test(t)) {
    return {
      label: '收货确认',
      detail: '可能与收货、对账有关，建议核实到货与单据。'
    }
  }
  if (/打印|标签|条码|贴纸/.test(t)) {
    return {
      label: '标签/打印',
      detail: '与标签或打印相关，可引导至标签打印或模板流程。'
    }
  }
  if (/^(在吗|你好|您好|哈喽|hi|hello|请问)[\s!！。…]*$/i.test(t) || (t.length < 16 && /在吗|你好|您好/.test(t))) {
    return {
      label: '寒暄/触达',
      detail: '简单问候，可结合上下文判断是否需要跟进展。'
    }
  }
  return {
    label: '待分析',
    detail: '未命中常见关键词，请在对话中结合全文让 AI 进一步理解意图。'
  }
}

/** 星标微信经意图 API 或本地规则后，是否视为「标签/打印」类（用于标签打印工作流是否接收信号）。 */
export function isLabelPrintRelatedWechatIntent(
  text: string,
  ctx?: { intentLabel?: string; primaryIntent?: string; toolKey?: string }
): boolean {
  const label = String(ctx?.intentLabel || '')
  if (/标签\s*\/\s*打印|标签\/打印/.test(label)) return true
  if (label.includes('标签') && label.includes('打印')) return true
  const pi = String(ctx?.primaryIntent || '')
  if (/打印|标签|label|print|条码|贴纸/i.test(pi)) return true
  const tk = String(ctx?.toolKey || '')
  if (/print|label|打印|标签|条码/i.test(tk)) return true
  const t = String(text || '')
  return /打印|标签|条码|贴纸/.test(t)
}

/**
 * 是否视为「收货确认 / 客户侧业务进程」类（对接微信消息预处理，供收货确认工作流接收）。
 * 避免单独「确认」二字误触发货单等场景。
 */
export function isReceiptConfirmRelatedWechatIntent(
  text: string,
  ctx?: { intentLabel?: string; primaryIntent?: string; toolKey?: string }
): boolean {
  const label = String(ctx?.intentLabel || '').trim()
  if (label === '收货确认' || /收货\s*确认|确认\s*收货/.test(label)) return true
  if (/对账|签收|入库|到货|验货|清点|回单|售后|收货/.test(label)) return true

  const pi = String(ctx?.primaryIntent || '')
  if (/receipt|收货|对账|签收|入库|arrival|confirm.*goods/i.test(pi)) return true
  const tk = String(ctx?.toolKey || '')
  if (/receipt|收货|签收|对账|入库/i.test(tk)) return true

  const t = String(text || '')
  if (/收货|到货|签收|对账|入库|验货|清点|回单|售后/.test(t)) return true
  if (/确认/.test(t) && /(收货|到货|签收|验货|对账|入库|单号|回单)/.test(t)) return true
  return false
}
