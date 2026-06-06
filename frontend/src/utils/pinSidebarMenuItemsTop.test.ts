import { describe, expect, it } from 'vitest'
import { pinSidebarMenuItemsTop } from './pinSidebarMenuItemsTop'

describe('pinSidebarMenuItemsTop', () => {
  it('moves chat to the front without dropping other items', () => {
    const items = [
      { key: 'products', name: '人员' },
      { key: 'other-tools', name: '工作流' },
      { key: 'chat', name: '智能对话' },
      { key: 'orders', name: '考勤单' },
    ]
    expect(pinSidebarMenuItemsTop(items).map((i) => i.key)).toEqual([
      'chat',
      'products',
      'other-tools',
      'orders',
    ])
  })
})
