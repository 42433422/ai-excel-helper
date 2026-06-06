import { describe, it, expect, beforeEach, vi } from 'vitest'
import { ref } from 'vue'

// Mock dependencies before importing the module under test.
vi.mock('./useChatMessages', async () => {
  const { ref } = await import('vue')
  return {
    useChatMessages: (sessionId: any) => ({
      messages: ref([]),
      lastMessage: ref(null),
      addMessage: vi.fn(),
      addAndSaveMessage: vi.fn(),
      saveMessage: vi.fn(),
      pushStreamingAiShell: vi.fn(),
      applyPlainTextToMessageIndex: vi.fn(),
      clearMessages: vi.fn(),
      loadMessages: vi.fn(),
      syncFromServer: vi.fn(),
      queueVoice: vi.fn(),
      clearVoiceQueue: vi.fn(),
    }),
  }
})

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn() }),
  useRoute: () => ({}),
}))

vi.mock('@/stores/tutorial', () => ({ useTutorialStore: () => ({}) }))
vi.mock('@/stores/mods', () => ({ useModsStore: () => ({ mods: [], modsForUi: [], setActiveModId: vi.fn() }) }))
vi.mock('@/stores/workflowAiEmployees', () => ({ useWorkflowAiEmployeesStore: () => ({ enabled: {} }) }))

// Other heavy composables used by useChatView can be mocked as no-ops.
vi.mock('./useShipmentTask', () => ({ useShipmentTask: () => ({}) }))
vi.mock('./usePrintService', () => ({ usePrintService: () => ({}) }))
vi.mock('./useExcelAnalysis', async () => {
  const { ref } = await import('vue')
  return {
    useExcelAnalysis: () => ({
      excelAnalyzeUploading: ref(false),
      excelAnalyzeInputRef: ref(null),
      triggerUpload: vi.fn(),
      onExcelAnalyzeFileChange: vi.fn(),
      setOnMultimodalFileChangeCallback: vi.fn(),
    }),
  }
})

import { useChatView } from './useChatView'

describe('useChatView (composable)', () => {
  beforeEach(() => {
    vi.resetAllMocks()
  })

  it('returns core API including sendMessage and isProMode', () => {
    const sessionId = ref('test-session')
    const api = useChatView({ sessionId, proIntentExperienceEnabled: ref(false) })
    expect(api).toBeTruthy()
    expect(typeof api.sendMessage).toBe('function')
    expect(api.isProMode).toBeDefined()
  })
})
