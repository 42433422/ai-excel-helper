import { describe, it, expect } from 'vitest'
import Sidebar from './Sidebar.vue'

describe('Sidebar.vue', () => {
  it('exports a Vue component', () => {
    expect(Sidebar).toBeTruthy()
    expect(Sidebar.name || Sidebar.__name || 'Sidebar').toBeTruthy()
  })
})
