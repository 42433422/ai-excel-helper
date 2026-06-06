import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { storeToRefs } from 'pinia'
import { useWorkflowAiEmployeesStore } from '@/stores/workflowAiEmployees'
import {
  useWorkflowEmployeeSpaceStore,
  type WorkflowEmployeeSession,
  type WorkflowEmployeeSpaceSnapshot,
} from '@/stores/workflowEmployeeSpace'
import { shortNameFromPanelTitle } from '@/utils/workflowEmployeeDisplayName'

export type WorkflowEmployeeDeskRow = {
  empId: string
  panelTitle: string
  shortName: string
  enabled: boolean
  snapshot?: WorkflowEmployeeSpaceSnapshot
  session?: WorkflowEmployeeSession
}

export function formatWorkDurationShort(ms: number): string {
  if (!Number.isFinite(ms) || ms <= 0) return '0m'
  const sec = Math.floor(ms / 1000)
  if (sec < 60) return `${sec}s`
  const min = Math.floor(sec / 60)
  if (min < 60) return `${min}m`
  const hr = Math.floor(min / 60)
  const mr = min % 60
  if (hr < 24) return mr > 0 ? `${hr}h ${mr}m` : `${hr}h`
  const day = Math.floor(hr / 24)
  const hrr = hr % 24
  return hrr > 0 ? `${day}d ${hrr}h` : `${day}d`
}

export function totalWorkMs(session: WorkflowEmployeeSession | undefined, nowMs: number): number {
  if (!session) return 0
  const live = session.enabledAt ? Math.max(0, nowMs - session.enabledAt) : 0
  return Math.max(0, session.lifetimeMs) + live
}

export function useNowMsTicker(intervalMs = 30000) {
  const nowMs = ref(Date.now())
  let timer: number | null = null
  onMounted(() => {
    if (typeof window === 'undefined') return
    nowMs.value = Date.now()
    timer = window.setInterval(() => {
      nowMs.value = Date.now()
    }, Math.max(1000, intervalMs))
  })
  onBeforeUnmount(() => {
    if (timer != null) {
      window.clearInterval(timer)
      timer = null
    }
  })
  return nowMs
}

export function useWorkflowEmployeeDesks() {
  const wfEmp = useWorkflowAiEmployeesStore()
  const spaceStore = useWorkflowEmployeeSpaceStore()
  const { enabled: workflowEnabled, registryEntries } = storeToRefs(wfEmp)
  const { snapshots, sessions } = storeToRefs(spaceStore)

  const employeeIds = computed(() => registryEntries.value.map((e) => e.id))

  function resolvePanelTitle(empId: string): string {
    const entry = registryEntries.value.find((e) => e.id === empId)
    if (entry) return `工作流 · ${entry.label}`
    return `工作流 · ${empId}`
  }

  const desks = computed<WorkflowEmployeeDeskRow[]>(() => {
    return employeeIds.value.map((empId) => {
      const panelTitle = resolvePanelTitle(empId)
      const en = workflowEnabled.value[empId] === true
      const snap = snapshots.value[empId]
      const sess = sessions.value[empId]
      return {
        empId,
        panelTitle,
        shortName: snap?.shortName || shortNameFromPanelTitle(panelTitle),
        enabled: en,
        snapshot: snap,
        session: sess,
      }
    })
  })

  const onDutyDesks = computed<WorkflowEmployeeDeskRow[]>(() =>
    desks.value.filter((d) => d.enabled)
  )

  function statusLine(row: WorkflowEmployeeDeskRow): string {
    if (!row.enabled) return '副窗未启用'
    const s = row.snapshot
    if (!s) return '暂无快照'
    return s.stage || s.progressLabel || s.hintLine || '待命'
  }

  function ariaLabel(row: WorkflowEmployeeDeskRow): string {
    const state = !row.enabled ? '副窗未启用' : row.snapshot ? statusLine(row) : '等待活动'
    return `员工 ${row.shortName}。${state}`
  }

  function isBusy(row: WorkflowEmployeeDeskRow): boolean {
    if (!row.enabled) return false
    const s = row.snapshot
    if (!s) return false
    return s.visuallyBusy === true
  }

  function processedCount(row: WorkflowEmployeeDeskRow): number {
    return row.session?.processedCount ?? 0
  }

  return {
    employeeIds,
    desks,
    onDutyDesks,
    statusLine,
    ariaLabel,
    isBusy,
    processedCount,
  }
}
