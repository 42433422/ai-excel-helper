import { describe, it, expect, beforeEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useAppShellStore } from './appShell'

describe('appShell store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('toggles appActive and chatOwnsInput', () => {
    const store = useAppShellStore()
    expect(store.appActive).toBe(true)
    expect(store.chatOwnsInput).toBe(true)
    store.setAppActive(false)
    store.setChatOwnsInput(false)
    expect(store.appActive).toBe(false)
    expect(store.chatOwnsInput).toBe(false)
  })
})
