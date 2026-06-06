import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useAppShellStore = defineStore('appShell', () => {
  const appActive = ref(true)
  const chatOwnsInput = ref(true)

  function setAppActive(v: boolean) {
    appActive.value = v
  }

  function setChatOwnsInput(v: boolean) {
    chatOwnsInput.value = v
  }

  return {
    appActive,
    chatOwnsInput,
    setAppActive,
    setChatOwnsInput,
  }
})

