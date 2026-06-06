/** 始终固定在侧栏主菜单顶部的宿主项（优先于 Mod 前置与用户拖拽排序） */
export const SIDEBAR_PINNED_TOP_KEYS = ['chat'] as const

export function pinSidebarMenuItemsTop<T extends { key: string }>(items: T[]): T[] {
  if (!items.length) return items
  const pinSet = new Set<string>(SIDEBAR_PINNED_TOP_KEYS)
  const pinned: T[] = []
  for (const key of SIDEBAR_PINNED_TOP_KEYS) {
    const item = items.find((row) => row.key === key)
    if (item) pinned.push(item)
  }
  const rest = items.filter((row) => !pinSet.has(row.key))
  return [...pinned, ...rest]
}
