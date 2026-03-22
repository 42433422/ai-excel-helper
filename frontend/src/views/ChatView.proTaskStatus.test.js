import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'

// Mock chat api to avoid network calls during ChatView mount.
vi.mock('../api/chat', () => {
  return {
    default: {
      getConversation: vi.fn().mockResolvedValue({ success: true, messages: [] }),
      getConversations: vi.fn().mockResolvedValue({ success: true, sessions: [] })
    }
  }
})

import ChatView from './ChatView.vue'

describe('ChatView pro-mode runtime task status', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    // Ensure localStorage exists in jsdom.
    if (!window.localStorage) {
      Object.defineProperty(window, 'localStorage', { value: new Map() })
    }
  })

  afterEach(() => {
    vi.clearAllTimers()
    vi.useRealTimers()
  })

  it('renders running/done status from xcagi:pro-task-status event', async () => {
    const wrapper = mount(ChatView)
    await nextTick()

    expect(wrapper.text()).toContain('暂无任务')

    window.dispatchEvent(new CustomEvent('xcagi:pro-task-status', {
      detail: {
        current_task: '执行工具',
        current_tool: 'shipment_generate',
        status: 'running',
        updated_at: new Date().toISOString()
      }
    }))

    await nextTick()
    expect(wrapper.text()).toContain('进行中')

    window.dispatchEvent(new CustomEvent('xcagi:pro-task-status', {
      detail: {
        current_task: '执行工具',
        current_tool: 'shipment_generate',
        status: 'done',
        updated_at: new Date().toISOString()
      }
    }))

    await nextTick()
    expect(wrapper.text()).toContain('已完成')

    // done/failed/error should clear after 4.5s
    vi.advanceTimersByTime(4600)
    await nextTick()
    expect(wrapper.text()).toContain('暂无任务')
  })

  it('does not override confirm task when currentTask exists', async () => {
    const wrapper = mount(ChatView)
    await nextTick()

    // Force a confirm task card to be visible.
    wrapper.vm.currentTask = { title: '确认任务', description: 'desc', items: [] }
    await nextTick()
    expect(wrapper.text()).toContain('确认任务')

    window.dispatchEvent(new CustomEvent('xcagi:pro-task-status', {
      detail: {
        current_task: '执行工具',
        current_tool: 'shipment_generate',
        status: 'running',
        updated_at: new Date().toISOString()
      }
    }))

    await nextTick()
    // Should still show the confirm card (and not show runtime status).
    expect(wrapper.text()).toContain('确认任务')
    expect(wrapper.text()).not.toContain('进行中')
    expect(wrapper.vm.proRuntimeTask).toBe(null)
  })
})

