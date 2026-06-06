import { computed } from 'vue'
import { storeToRefs } from 'pinia'
import { useIndustryStore } from '@/stores/industry'
import { useModsStore } from '@/stores/mods'
import { DEFAULT_INDUSTRY_ID } from '@/constants/industryDefaults'
import { isSelectableExtensionModId } from '@/constants/genericModPack'
import { resolveCoreNavLabel } from '@/utils/coreNavLabel'
import { getIndustryPreset } from '@/constants/industryPresets'

type StarterPackItem = {
  label: string
  hint: string
  text: string
}

function str(value: unknown, fallback = ''): string {
  const s = String(value ?? '').trim()
  return s || fallback
}

function stripEntitySuffix(label: string): string {
  return str(label)
    .replace(/(名称|姓名|编号|代码|编码|名)$/u, '')
    .trim()
}

function normalizeStarterPack(rows: unknown): StarterPackItem[] {
  if (!Array.isArray(rows)) return []
  return rows
    .map((row) => {
      if (!row || typeof row !== 'object') return null
      const r = row as Record<string, unknown>
      const label = str(r.label)
      const hint = str(r.hint)
      const text = str(r.text)
      if (!label || !text) return null
      return { label, hint, text }
    })
    .filter((item): item is StarterPackItem => Boolean(item))
}

/**
 * 选定 active mod：
 * 1. 若有 modsForUi 中其 industry.id === industryId，优先返回（保持原语义，让"切行业"决定 UI）
 * 2. 否则若 activeModId 存在且能在 modsForUi 中找到，直接返回该 mod；
 *    这样用户在 Settings 选 Mod 后，即便 server 当前行业还没跟上（backend init 滞后、
 *    或 industry 切换接口暂未受理），侧栏副标题/主单位/意图关键词仍能立刻按 mod 走，
 *    避免扩展模块与当前行业文案脱节。
 */
function activeModForIndustry(mods: any[], activeModId: string, industryId: string) {
  if (activeModId) {
    const direct = mods.find((m) => str(m?.id) === activeModId)
    if (direct) {
      if (isSelectableExtensionModId(activeModId)) return direct
      const ext = mods.find((m) => isSelectableExtensionModId(str(m?.id)))
      if (ext) return ext
    }
  }
  let matched: any = null
  for (const mod of mods) {
    const modIndustryId = str(mod?.industry?.id)
    if (!modIndustryId || modIndustryId !== industryId) continue
    if (!matched) matched = mod
    if (activeModId && str(mod?.id) === activeModId) matched = mod
  }
  return matched
}

export function useIndustryUiText() {
  const industryStore = useIndustryStore()
  const modsStore = useModsStore()
  const { modsForUi } = storeToRefs(modsStore)

  const industryId = computed(() => str(industryStore.currentIndustryId, DEFAULT_INDUSTRY_ID))
  const activeMod = computed(() =>
    activeModForIndustry(modsForUi.value || [], str(modsStore.activeModId), industryId.value),
  )
  /**
   * 计算行业配置：active mod 的 manifest.industry 优先（用户在 Settings 选了
   * 该 mod 就应该看到该 mod 的字段/意图），其次 server 给的 currentConfig。
   * 让"切 mod" 立刻全栈生效，不依赖后端 industry 切换是否被接受。
   */
  const industryConfig = computed(() => {
    const fromMod = activeMod.value?.industry
    if (fromMod && typeof fromMod === 'object') return fromMod
    return industryStore.currentConfig || {}
  })
  /**
   * active mod 的"实际行业 id"——优先用 mod manifest 声明的 industry.id；
   * mod 没声明时回退到当前 industryStore，再不行用默认行业。这里不再硬等
   * industryStore.currentIndustryId，让侧栏副标题可立刻反映 mod 切换。
   */
  const effectiveIndustryId = computed(() => {
    const fromMod = str(activeMod.value?.industry?.id)
    return fromMod || industryId.value
  })
  const uiLabels = computed<Record<string, unknown>>(() => {
    const labels = activeMod.value?.ui_labels
    return labels && typeof labels === 'object' ? labels : {}
  })

  const productFields = computed<Record<string, unknown>>(() => {
    const fields = industryConfig.value?.product_fields
    return fields && typeof fields === 'object' ? fields : {}
  })
  const quantityFields = computed<Record<string, unknown>>(() => {
    const fields = industryConfig.value?.quantity_fields
    return fields && typeof fields === 'object' ? fields : {}
  })
  const orderTypes = computed<Record<string, unknown>>(() => {
    const rows = industryConfig.value?.order_types
    return rows && typeof rows === 'object' ? rows : {}
  })
  const units = computed<Record<string, unknown>>(() => {
    const rows = industryConfig.value?.units
    return rows && typeof rows === 'object' ? rows : {}
  })

  const entityName = computed(() =>
    str(uiLabels.value.entity, stripEntitySuffix(str(productFields.value.name, '业务对象')) || '业务对象'),
  )
  const entityPluralName = computed(() => str(uiLabels.value.entity_plural, entityName.value))
  const modelLabel = computed(() => str(uiLabels.value.model_label, str(productFields.value.model, '编号')))
  const nameLabel = computed(() => str(uiLabels.value.name_label, str(productFields.value.name, `${entityName.value}名称`)))
  const categoryLabel = computed(() => str(uiLabels.value.category_label, str(productFields.value.category, '分类')))
  const priceLabel = computed(() => str(uiLabels.value.price_label, str(productFields.value.price, '单价')))
  const unitLabel = computed(() => str(uiLabels.value.unit_label, str(productFields.value.unit, '单位')))
  const primaryUnit = computed(() => str(uiLabels.value.primary_unit, str(units.value.primary, '次')))
  const primaryQuantityLabel = computed(() =>
    str(uiLabels.value.primary_quantity_label, str(quantityFields.value.primary_label, primaryUnit.value)),
  )
  const shipmentOrderName = computed(() => str(uiLabels.value.shipment_order, str(orderTypes.value.shipment, '业务单')))
  const recordsName = computed(() =>
    str(
      uiLabels.value.records,
      resolveCoreNavLabel('shipment-records', industryId.value, modsForUi.value) || `${shipmentOrderName.value}记录`,
    ),
  )
  const queryTitle = computed(() => str(uiLabels.value.query_title, `${entityName.value}查询`))
  const queryDescription = computed(() =>
    str(uiLabels.value.query_description, `查询与快速修改${entityPluralName.value}资料`),
  )
  const queryPlaceholder = computed(() =>
    str(
      uiLabels.value.query_placeholder,
      `输入${modelLabel.value}或${nameLabel.value}查询${entityName.value}`,
    ),
  )
  const entityListName = computed(() =>
    str(
      uiLabels.value.entity_list,
      resolveCoreNavLabel('products', effectiveIndustryId.value, modsForUi.value) || `${entityName.value}管理`,
    ),
  )
  const assistantSubtitle = computed(() => {
    const mod = activeMod.value
    const modName = str(mod?.name || mod?.id)
    const indId = effectiveIndustryId.value
    if (!modName) return `${indId}系统`
    return `${modName}（${indId}系统）`
  })

  const emptyBeforeSearch = computed(() =>
    str(uiLabels.value.empty_before_search, `请先输入${modelLabel.value}或${nameLabel.value}，再点右侧「查询」。`),
  )
  const keywordChanged = computed(() => str(uiLabels.value.keyword_changed, '关键词已变更，请再点「查询」刷新结果。'))
  const queryFailedPrefix = computed(() => str(uiLabels.value.query_failed_prefix, `${entityName.value}接口请求失败`))
  const searchFailedMessage = computed(
    () => `${queryFailedPrefix.value}。请确认后端已启动、Vite 代理或 VITE_API_BASE_URL 指向正确。`,
  )

  const starterPackPresets = computed<StarterPackItem[]>(() => {
    const fromMod = normalizeStarterPack(activeMod.value?.ui_starter_pack)
    if (fromMod.length) return fromMod
    const preset = getIndustryPreset(effectiveIndustryId.value)
    const fromIndustry = preset.quickButtons
      .filter((b) => b.label !== '测试预览')
      .slice(0, 5)
      .map((b) => ({ label: b.label, hint: b.text, text: b.text }))
    if (fromIndustry.length) return fromIndustry
    return []
  })

  return {
    activeMod,
    industryConfig,
    industryId,
    effectiveIndustryId,
    entityName,
    entityPluralName,
    modelLabel,
    nameLabel,
    categoryLabel,
    priceLabel,
    unitLabel,
    primaryUnit,
    primaryQuantityLabel,
    shipmentOrderName,
    recordsName,
    queryTitle,
    queryDescription,
    queryPlaceholder,
    entityListName,
    assistantSubtitle,
    emptyBeforeSearch,
    keywordChanged,
    searchFailedMessage,
    starterPackPresets,
  }
}
