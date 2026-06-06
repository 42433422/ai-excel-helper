import { ref } from 'vue'
import { readBuildEdition, type HostEdition } from '@/constants/genericModPack'
import {
  markHostPackAcknowledged,
  markProductFlowCompleted,
  parseFlowStepQuery,
  readHostPackAcknowledged,
  readProductFlowCompleted,
  type ProductFlowStepId,
} from '@/constants/productFlow'
import { isShellEditionBuild } from '@/constants/platformShellMode'
import type { DeliverableStatus } from '@/constants/platformShell'
import { fetchDeliverableStatus } from '@/utils/platformShellApi'

const deliverableRef = ref<DeliverableStatus | null>(null)
const deliverableLoading = ref(false)

export function useProductFlow() {
  async function refreshDeliverable(force = false) {
    deliverableLoading.value = true
    try {
      deliverableRef.value = await fetchDeliverableStatus(force)
      if (deliverableRef.value?.deliverable) {
        markHostPackAcknowledged()
      }
      return deliverableRef.value
    } finally {
      deliverableLoading.value = false
    }
  }

  function edition(): HostEdition {
    return readBuildEdition()
  }

  function needsProductFlow(): boolean {
    if (!isShellEditionBuild()) return false
    return !readProductFlowCompleted()
  }

  function resolveEntryStep(queryStep?: unknown): ProductFlowStepId {
    const q = parseFlowStepQuery(queryStep)
    if (q !== 'welcome') return q
    if (!readHostPackAcknowledged()) {
      return 'host-pack'
    }
    const st = deliverableRef.value
    if (st && st.deliverable === false) {
      return 'host-pack'
    }
    return 'welcome'
  }

  function completeFlowAndGoChat(router: { replace: (x: { path: string }) => void }) {
    markProductFlowCompleted()
    markHostPackAcknowledged()
    const path =
      typeof window !== 'undefined' && window.location.pathname.startsWith('/mod/')
        ? '/'
        : '/'
    router.replace({ path })
  }

  return {
    deliverable: deliverableRef,
    deliverableLoading,
    refreshDeliverable,
    edition,
    needsProductFlow,
    resolveEntryStep,
    completeFlowAndGoChat,
    markProductFlowCompleted,
    markHostPackAcknowledged,
    readProductFlowCompleted,
  }
}

export function shouldRouteToProductOnboarding(
  toName: string | symbol | null | undefined,
): boolean {
  const name = String(toName || '')
  if (
    name === 'product-onboarding' ||
    name === 'login' ||
    name === 'lan-gate' ||
    name === 'settings' ||
    name === 'mod-store'
  ) {
    return false
  }
  return needsProductFlowStatic()
}

function needsProductFlowStatic(): boolean {
  if (!isShellEditionBuild()) return false
  return !readProductFlowCompleted()
}
