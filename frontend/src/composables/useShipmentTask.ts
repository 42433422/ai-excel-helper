import { ref, type Ref } from 'vue'
import type { ChatMessageExtras } from './useChatMessages'
import { normalizeModel, toNumber, parseShipmentCommand, extractModelQtySpec } from '../utils/textParser'

export interface ShipmentProduct {
  model_number?: string
  quantity_tins?: number
  tin_spec?: number
  name?: string
  product_name?: string
  unit_price?: number
  price?: number
  '型号'?: string
  '桶数'?: number
  '规格'?: number
  '单价'?: number
  '产品名称'?: string
  '单位'?: string
}

export interface ShipmentTask {
  type: string
  title?: string
  description?: string
  payload?: {
    params?: {
      products?: ShipmentProduct[]
      unit_name?: string
      order_number?: string
    }
  }
  completed?: boolean
  customOrderNumber?: string
  items?: any[]
  order_number?: string
  downloadUrl?: string
  api_url?: string
  method?: string
  switch_view?: string
  data?: any
  document?: any
}

interface ChatMessageLike {
  role: 'user' | 'ai' | 'task'
  content: string
  time: string
}

interface UseChatMessagesReturn {
  addAndSaveMessage: (
    content: string,
    role?: 'user' | 'ai' | 'task',
    extras?: ChatMessageExtras
  ) => Promise<void>
}

const SHIPMENT_PREVIEW_COLUMNS = ['单位', '型号', '产品名称', '桶数', '规格', '单价', '总价']

export function useShipmentTask(
  messages: UseChatMessagesReturn,
  currentTask: Ref<ShipmentTask | null>
) {
  const lastShipmentExecution = ref<{
    filePath: string
    purchaseUnit: string
    orderId: number | null
    labelPaths: string[]
    /** 右侧任务列表中「发货单生成」条目的 id，用于生成后衔接打印再标为 100% */
    taskListId?: string
  } | null>(null)

  async function handleModifyCommand(message: string): Promise<boolean> {
    const task = currentTask.value
    if (!task || task?.type !== 'shipment_generate' || task?.completed) {
      return false
    }

    const command = parseShipmentCommand(message)
    if (!command || !command.action) {
      return false
    }

    const products = [...((task.payload?.params?.products as ShipmentProduct[]) || [])]

    switch (command.action) {
      case 'add':
        return await handleAddProduct(products, command, task)
      case 'remove':
        return handleRemoveProduct(products, command, task)
      case 'edit':
        return handleEditProduct(products, command, task)
      default:
        return false
    }
  }

  async function handleAddProduct(
    products: ShipmentProduct[],
    command: { product?: { model_number: string; quantity_tins: number; tin_spec: number } },
    task: ShipmentTask
  ): Promise<boolean> {
    if (!command.product?.model_number) {
      const tip = '再加格式示例：再加 1桶 9803 规格 28'
      await messages.addAndSaveMessage(tip, 'ai')
      return true
    }

    const productMeta = await fetchProductMetaForPreview({
      model: command.product.model_number,
      unitName: task.payload?.params?.unit_name || ''
    })

    const unitPrice = productMeta?.unit_price
    const newProduct: ShipmentProduct = {
      name: productMeta?.name || '',
      product_name: productMeta?.name || '',
      model_number: command.product.model_number,
      quantity_tins: command.product.quantity_tins,
      tin_spec: command.product.tin_spec || productMeta?.tin_spec || 10,
      ...(unitPrice !== null && typeof unitPrice !== 'undefined'
        ? { unit_price: unitPrice, price: unitPrice }
        : {})
    }

    products.push(newProduct)
    updateShipmentTaskPreview(task, products)

    const pricedText = (unitPrice !== null && typeof unitPrice !== 'undefined')
      ? `，单价${unitPrice.toFixed(2)}`
      : ''
    const tip = `已加入：${command.product.model_number}，${command.product.quantity_tins}桶，规格${newProduct.tin_spec}${pricedText}。`
    await messages.addAndSaveMessage(tip, 'ai')
    return true
  }

  function handleRemoveProduct(
    products: ShipmentProduct[],
    command: { model?: string },
    task: ShipmentTask
  ): boolean {
    const model = command.model || ''
    if (!model) {
      messages.addAndSaveMessage('删除格式示例：删除 9803', 'ai')
      return true
    }

    const idx = products.findIndex(
      (p) => normalizeModel(p?.model_number || p?.型号 || p?.name || '') === model
    )
    if (idx < 0) {
      messages.addAndSaveMessage(`未找到型号 ${model}，请确认后再试。`, 'ai')
      return true
    }

    products.splice(idx, 1)
    updateShipmentTaskPreview(task, products)
    messages.addAndSaveMessage(`已删除型号 ${model}。`, 'ai')
    return true
  }

  function handleEditProduct(
    products: ShipmentProduct[],
    command: { product?: { model_number: string; quantity_tins: number; tin_spec: number } },
    task: ShipmentTask
  ): boolean {
    const model = command.product?.model_number
      || normalizeModel(products[0]?.model_number || '')
    if (!model) {
      messages.addAndSaveMessage('修改格式示例：改成 9803 2桶 规格 28', 'ai')
      return true
    }

    const idx = products.findIndex(
      (p) => normalizeModel(p?.model_number || p?.型号 || p?.name || '') === model
    )
    if (idx < 0) {
      messages.addAndSaveMessage(`未找到型号 ${model}，请先"再加 ${model} ..."后再修改。`, 'ai')
      return true
    }

    const old = products[idx] || {}
    products[idx] = {
      ...old,
      model_number: model,
      quantity_tins: command.product?.quantity_tins || old.quantity_tins || 1,
      tin_spec: command.product?.tin_spec || old.tin_spec || 10
    }

    updateShipmentTaskPreview(task, products)
    const tip = `已更新：${model}，${products[idx].quantity_tins}桶，规格${products[idx].tin_spec}。`
    messages.addAndSaveMessage(tip, 'ai')
    return true
  }

  async function fetchProductMetaForPreview({
    model,
    unitName = ''
  }: {
    model: string
    unitName?: string
  }): Promise<{ name?: string; unit_price?: number; tin_spec?: number } | null> {
    const normalizedModel = normalizeModel(model)
    if (!normalizedModel) return null

    const buildUrl = (unit: string) => {
      const query = new URLSearchParams({
        keyword: normalizedModel,
        model_number: normalizedModel,
        page: '1',
        per_page: '20'
      })
      if (unit) query.set('unit', unit)
      return `/api/products/list?${query.toString()}`
    }

    const requestUrls = unitName ? [buildUrl(unitName), buildUrl('')] : [buildUrl('')]
    for (const url of requestUrls) {
      try {
        const resp = await fetch(url)
        const data = await resp.json().catch(() => ({}))
        if (!resp.ok || !data?.success) continue
        const rows = Array.isArray(data?.data) ? data.data : []
        const best = pickBestProductRecord(rows, normalizedModel)
        if (!best) continue

        return {
          name: String(best?.name || best?.product_name || '').trim(),
          unit_price: toNumber(best?.price ?? best?.unit_price),
          tin_spec: toNumber(best?.tin_spec ?? best?.specification ?? best?.spec)
        }
      } catch (_err) {
        // Ignore network/query errors in preview enrichment.
      }
    }
    return null
  }

  function pickBestProductRecord(records: any[], target: string): any | null {
    if (!Array.isArray(records) || !records.length) return null
    if (!target) return records[0]

    const normalizeProductToken = (value: string) =>
      String(value || '').trim().toUpperCase().replace(/\s+/g, '').replace(/-/g, '')

    const targetNorm = normalizeProductToken(target)

    for (const row of records) {
      const recModel = normalizeProductToken(row?.model_number)
      if (recModel && recModel === targetNorm) return row
    }
    for (const row of records) {
      const recName = normalizeProductToken(row?.name || row?.product_name)
      if (recName && recName.includes(targetNorm)) return row
    }
    for (const row of records) {
      const recModel = normalizeProductToken(row?.model_number)
      if (recModel && recModel.includes(targetNorm)) return row
    }
    return records[0]
  }

  function updateShipmentTaskPreview(task: ShipmentTask, nextProducts: ShipmentProduct[]) {
    const products = Array.isArray(nextProducts) ? nextProducts : []
    task.payload = { ...(task.payload || {}) }
    task.payload.params = { ...(task.payload.params || {}), products }

    const oldItems = Array.isArray(task.items) ? task.items : []
    const oldByModel: Record<string, ShipmentProduct> = {}
    oldItems.forEach((it) => {
      const key = normalizeModel(it?.型号 || it?.model_number || '')
      if (key) oldByModel[key] = it
    })

    const unitName = String(
      task.payload?.params?.unit_name ||
      (oldItems[0] && oldItems[0]['单位']) ||
      ''
    ).trim()

    const nextItems = products.map((p) => {
      const model = normalizeModel(p?.model_number || p?.型号 || p?.name || '')
      const old = oldByModel[model] || {}
      const qty = Number(p?.quantity_tins ?? p?.quantity ?? old['桶数'] ?? 1) || 1
      const spec = Number(p?.tin_spec ?? p?.spec ?? old['规格'] ?? 10) || 10
      const priceNum = toNumber(p?.unit_price ?? p?.price ?? old['单价'])
      const totalNum = priceNum !== null ? priceNum * qty * spec : null

      return {
        单位: unitName,
        型号: model || '-',
        产品名称: p?.name || p?.product_name || old['产品名称'] || '-',
        桶数: qty,
        规格: spec,
        单价: priceNum !== null ? priceNum.toFixed(2) : '-',
        总价: totalNum !== null ? totalNum.toFixed(2) : '-'
      }
    })

    const grandTotal = nextItems.reduce((sum, row) => {
      const n = toNumber(row['总价'])
      return sum + (n !== null ? n : 0)
    }, 0)
    const hasPricedRow = nextItems.some((row) => toNumber(row['总价']) !== null)
    const totalText = hasPricedRow ? `，预估总价 ¥${grandTotal.toFixed(2)}` : ''

    task.items = nextItems
    task.description = `单位：${unitName || '-'}，共 ${nextItems.length} 项${totalText}。确认后将生成并可继续打印。`
  }

  async function fetchNextOrderNumber(): Promise<string> {
    const endpointCandidates = [
      '/api/shipment/orders/next_number?suffix=A',
      '/orders/next_number?suffix=A',
      '/api/orders/next_number?suffix=A'
    ]

    for (const url of endpointCandidates) {
      try {
        const resp = await fetch(url)
        const data = await resp.json().catch(() => ({}))
        const orderNo = String(
          data?.data?.order_number
          || data?.order_number
          || data?.data?.next_number
          || ''
        ).trim()
        // 兼容：部分路由可能省略 success 字段，只要 HTTP 成功且拿到编号即采用
        if (resp.ok && orderNo && (data?.success !== false)) {
          return orderNo
        }
      } catch (_err) {
        // Ignore single endpoint failures, continue trying next candidates.
      }
    }
    return ''
  }

  async function hydrateTaskOrderNumber(task: ShipmentTask, options?: { force?: boolean }): Promise<void> {
    if (!task || task?.type !== 'shipment_generate' || task?.completed) return
    if (!options?.force && String(task?.customOrderNumber || '').trim()) return

    const nextOrderNo = await fetchNextOrderNumber()
    if (!nextOrderNo) return

    if (currentTask.value !== task) return
    if (!options?.force && String(task?.customOrderNumber || '').trim()) return

    task.customOrderNumber = nextOrderNo
    task.payload = { ...(task.payload || {}) }
    task.payload.params = { ...(task.payload?.params || {}), order_number: nextOrderNo }
  }

  async function enrichShipmentPreviewProducts(task: ShipmentTask): Promise<void> {
    const currentProducts = Array.isArray(task?.payload?.params?.products)
      ? [...task.payload.params.products]
      : []
    if (!currentProducts.length) return

    const unitName = String(task?.payload?.params?.unit_name || '').trim()
    let changed = false
    const nextProducts: ShipmentProduct[] = []

    for (const rawProduct of currentProducts) {
      const product: ShipmentProduct = { ...(rawProduct || {}) }
      const model = normalizeModel(product?.model_number || product?.型号 || product?.name || '')
      const name = String(product?.name || product?.product_name || '').trim()
      const price = toNumber(product?.unit_price ?? product?.price)
      const needsName = !name || name === '-'
      const needsPrice = price === null

      if (!model || (!needsName && !needsPrice)) {
        nextProducts.push(product)
        continue
      }

      const productMeta = await fetchProductMetaForPreview({ model, unitName })
      if (productMeta) {
        if (needsName && productMeta?.name) {
          product.name = productMeta.name
          product.product_name = productMeta.name
          changed = true
        }
        if (needsPrice && productMeta?.unit_price !== null && typeof productMeta?.unit_price !== 'undefined') {
          product.unit_price = productMeta.unit_price
          product.price = productMeta.unit_price
          changed = true
        }
        if (!product.tin_spec && productMeta?.tin_spec) {
          product.tin_spec = productMeta.tin_spec
        }
      }
      nextProducts.push(product)
    }

    if (changed) {
      updateShipmentTaskPreview(task, nextProducts)
    }
  }

  function getTaskTableColumns(task: ShipmentTask): string[] {
    const items = Array.isArray(task?.items) ? task.items : []
    if (!items.length) return []

    if (task?.type === 'shipment_generate') {
      return SHIPMENT_PREVIEW_COLUMNS
    }
    return Object.keys(items[0] || {})
  }

  function getTaskTableItems(task: ShipmentTask): any[] {
    const items = Array.isArray(task?.items) ? task.items : []
    if (!items.length) return []

    if (task?.type !== 'shipment_generate') {
      return items
    }

    return items.map((item) => {
      const row: Record<string, any> = {}
      SHIPMENT_PREVIEW_COLUMNS.forEach((col) => {
        const value = item?.[col]
        row[col] = (value === null || typeof value === 'undefined' || value === '') ? '-' : value
      })
      return row
    })
  }

  function getTaskOrderNumber(task: ShipmentTask | null): string {
    if (!task) return ''

    const explicitOrderNo = String(
      task?.order_number ||
      task?.data?.order_number ||
      task?.document?.order_number ||
      ''
    ).trim()
    if (explicitOrderNo) return explicitOrderNo

    if (task?.type === 'shipment_generate' && !task?.completed) {
      return '待生成'
    }
    return ''
  }

  return {
    lastShipmentExecution,
    handleModifyCommand,
    fetchNextOrderNumber,
    hydrateTaskOrderNumber,
    enrichShipmentPreviewProducts,
    updateShipmentTaskPreview,
    getTaskTableColumns,
    getTaskTableItems,
    getTaskOrderNumber
  }
}
