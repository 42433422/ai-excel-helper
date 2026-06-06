import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createRouter, createMemoryHistory } from 'vue-router'
import MainLayout from './MainLayout.vue'

vi.mock('./Sidebar.vue', () => ({
  default: {
    name: 'Sidebar',
    template: '<nav class="sidebar-stub">Sidebar</nav>',
    props: ['activeView', 'isProMode'],
    emits: ['change-view', 'toggle-pro-mode'],
  },
}))

vi.mock('./PaneResizeHandle.vue', () => ({
  default: { template: '<span />' },
}))

describe('MainLayout.vue', () => {
  it('mounts shell with sidebar stub', () => {
    const pinia = createPinia()
    setActivePinia(pinia)
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: '/', name: 'chat', component: { template: '<div>Chat</div>' } },
      ],
    })

    const wrapper = mount(MainLayout, {
      global: {
        plugins: [pinia, router],
        stubs: {
          RouterView: { template: '<div class="router-view-stub" />' },
          RouterLink: { template: '<a><slot /></a>' },
        },
      },
      props: { isProMode: false },
    })

    expect(wrapper.find('.sidebar-stub').exists()).toBe(true)
    expect(wrapper.find('.main-container').exists()).toBe(true)
    wrapper.unmount()
  })
})
