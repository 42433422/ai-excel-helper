import { computed } from 'vue'
import { storeToRefs } from 'pinia'
import { useAccountProfileStore } from '@/stores/accountProfile'
import { useModsStore } from '@/stores/mods'
import {
  CLIENT_PRIMARY_ERP_MOD_ID,
  hasInstalledClientPrimaryErpMod,
} from '@/constants/genericModPack'
import { LS_MARKET_USER_JSON, type MarketUserProfile } from '@/api/marketAccount'

const LS_INSTANCE_ID = 'xcagi_service_bridge_instance_id'
const LS_INSTANCE_NAME = 'xcagi_service_bridge_instance_name'

function readMarketUser(): MarketUserProfile | null {
  if (typeof localStorage === 'undefined') return null
  try {
    const raw = localStorage.getItem(LS_MARKET_USER_JSON)
    if (!raw) return null
    const parsed = JSON.parse(raw) as MarketUserProfile
    return parsed && typeof parsed === 'object' ? parsed : null
  } catch {
    return null
  }
}

function marketUserKey(marketUser: MarketUserProfile | null): string {
  const uid = marketUser?.id
  if (uid !== undefined && uid !== null && String(uid).trim()) {
    return String(uid).trim()
  }
  return String(marketUser?.username || '').trim()
}

/** 企业侧 service-bridge 实例标识（太阳鸟场景为 taiyangniao-pro-*，与管理员总机互通） */
export function useServiceBridgeInstance() {
  const accountProfileStore = useAccountProfileStore()
  const modsStore = useModsStore()
  const { companyBrand, displayBrand } = storeToRefs(accountProfileStore)

  const isSunbirdChannel = computed(() => {
    const installed = (modsStore.mods || []).map((m) => String(m.id || '').trim()).filter(Boolean)
    if (hasInstalledClientPrimaryErpMod(installed)) return true
    const active = String(modsStore.activeModId || '').trim()
    return active === CLIENT_PRIMARY_ERP_MOD_ID
  })

  const instanceId = computed(() => {
    const marketUser = readMarketUser()
    const key = marketUserKey(marketUser)
    const prefix = isSunbirdChannel.value ? 'taiyangniao-pro' : 'enterprise'
    if (key) return `${prefix}-${key}`
    if (typeof localStorage !== 'undefined') {
      const cached = localStorage.getItem(LS_INSTANCE_ID)?.trim()
      if (cached) return cached
    }
    return `${prefix}-local`
  })

  const instanceName = computed(() => {
    const brand = companyBrand.value.trim() || displayBrand.value.trim()
    const market = readMarketUser()
    const uname = String(market?.username || '').trim()
    if (isSunbirdChannel.value) {
      if (brand) return `太阳鸟·${brand}`
      if (uname) return `太阳鸟·${uname}`
      return '太阳鸟'
    }
    if (brand) return brand
    const cached =
      typeof localStorage !== 'undefined'
        ? localStorage.getItem(LS_INSTANCE_NAME)?.trim()
        : ''
    if (cached) return cached
    return uname || '本企业'
  })

  function persistInstanceSnapshot() {
    if (typeof localStorage === 'undefined') return
    try {
      localStorage.setItem(LS_INSTANCE_ID, instanceId.value)
      localStorage.setItem(LS_INSTANCE_NAME, instanceName.value)
    } catch {
      /* ignore */
    }
  }

  return {
    instanceId,
    instanceName,
    isSunbirdChannel,
    persistInstanceSnapshot,
  }
}
