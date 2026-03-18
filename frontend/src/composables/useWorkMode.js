import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useWorkModeStore } from '@/stores/workMode'

export function useWorkMode() {
  const store = useWorkModeStore()
  
  const loading = computed(() => store.loading)
  const error = computed(() => store.error)
  const isActive = computed(() => store.isActive)
  const contacts = computed(() => store.contacts)
  const starredContacts = computed(() => store.starredContacts)
  const unreadContacts = computed(() => store.unreadContacts)
  const isTaskAcquisition = computed(() => store.isTaskAcquisition)
  const currentOrder = computed(() => store.currentOrder)
  
  const startWorkMode = async () => {
    await store.startWorkMode()
  }
  
  const stopWorkMode = async () => {
    await store.stopWorkMode()
  }
  
  const loadContacts = async () => {
    await store.loadContacts()
  }
  
  const sendMessage = async (contactId, message) => {
    await store.sendMessage(contactId, message)
  }
  
  const sendOpeningMessage = async (contactId) => {
    await store.sendOpeningMessage(contactId)
  }
  
  const refreshMessages = async () => {
    await store.refreshMessagesCache()
  }
  
  const resetTaskAcquisition = () => {
    store.resetTaskAcquisition()
  }
  
  const downloadOrder = async (orderId) => {
    await store.downloadOrder(orderId)
  }
  
  onUnmounted(() => {
    store.stopPolling()
  })
  
  return {
    loading,
    error,
    isActive,
    contacts,
    starredContacts,
    unreadContacts,
    isTaskAcquisition,
    currentOrder,
    startWorkMode,
    stopWorkMode,
    loadContacts,
    sendMessage,
    sendOpeningMessage,
    refreshMessages,
    resetTaskAcquisition,
    downloadOrder
  }
}
