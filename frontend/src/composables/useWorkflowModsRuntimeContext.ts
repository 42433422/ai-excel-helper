import { computed } from 'vue'
import { storeToRefs } from 'pinia'
import { useModsStore } from '@/stores/mods'
import {
  isModWorkflowEmployeesActive,
  type WorkflowDocsRuntimeContext,
} from '@/utils/workflowEmployeeDocs'

/** 流程全景 / 员工工作流管理 / 副窗链接等与 Mod 相关的展示统一用同一套运行时上下文 */
export function useWorkflowModsRuntimeContext() {
  const modsStore = useModsStore()
  const { clientModsUiOff, modsForUi, isLoaded, loadError } = storeToRefs(modsStore)

  const ctx = computed<WorkflowDocsRuntimeContext>(() => {
    const err = loadError.value
    return {
      clientModsUiOff: clientModsUiOff.value,
      modsForUi: modsForUi.value,
      isModsListLoaded: isLoaded.value,
      modsDisabledByServer:
        typeof err === 'string' &&
        (err.includes('XCAGI_DISABLE_MODS') || err.includes('Mod 扩展已关闭')),
    }
  })

  const modWorkflowEmployeesActive = computed(() => isModWorkflowEmployeesActive(ctx.value))

  return { ctx, modWorkflowEmployeesActive }
}
