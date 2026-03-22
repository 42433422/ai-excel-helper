import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import HelloWorld from '../../src/components/HelloWorld.vue'

describe('HelloWorld.vue', () => {
  it('renders properly', () => {
    const wrapper = mount(HelloWorld)
    // The starter template text may change; assert on a stable marker.
    expect(wrapper.text()).toContain('count is')
  })
})
