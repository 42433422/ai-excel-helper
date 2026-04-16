import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import HelloWorld from '../../src/components/HelloWorld.vue'

describe('HelloWorld.vue', () => {
  it('renders properly', () => {
    const wrapper = mount(HelloWorld)
    expect(wrapper.text()).toContain('Vite + Vue')
  })
})
