import { computed, onBeforeUnmount, ref } from 'vue'
import { usePaneLayoutStore, type PaneSizeOptions } from '@/stores/paneLayout'

/** Separator orientation: vertical bar resizes width (tracks pointer X); horizontal bar resizes height (tracks Y). */
type PaneSeparatorOrientation = 'vertical' | 'horizontal'

interface UseResizablePaneOptions extends PaneSizeOptions {
  paneKey: string
  cssVarName: string
  orientation?: PaneSeparatorOrientation
  /**
   * When the dragged separator is on this pane's leading edge (e.g. left edge of a right-hand column),
   * pointer movement toward the flex start shrinks the pane — set true so drag direction matches visual expectation.
   */
  invertDelta?: boolean
  enabled?: () => boolean
  onResizeStart?: () => void
  onResizeEnd?: () => void
}

export function useResizablePane(options: UseResizablePaneOptions) {
  const paneLayoutStore = usePaneLayoutStore()
  const isResizing = ref(false)
  let startPointer = 0
  let startPaneSize = options.defaultSize

  const isEnabled = () => (typeof options.enabled === 'function' ? options.enabled() : true)

  const paneSize = computed(() =>
    paneLayoutStore.getPaneSize(options.paneKey, {
      defaultSize: options.defaultSize,
      minSize: options.minSize,
      maxSize: options.maxSize,
    })
  )

  const paneStyle = computed(() => ({
    [options.cssVarName]: `${paneSize.value}px`,
  }))

  const stopResize = () => {
    if (!isResizing.value) return
    isResizing.value = false
    document.body.style.userSelect = ''
    document.body.style.cursor = ''
    window.removeEventListener('mousemove', onResizeMove)
    window.removeEventListener('mouseup', stopResize)
    options.onResizeEnd?.()
  }

  const onResizeMove = (event: MouseEvent) => {
    if (!isResizing.value) return
    const pointer =
      options.orientation === 'horizontal' ? event.clientY : event.clientX
    const rawDelta = pointer - startPointer
    const delta = options.invertDelta ? -rawDelta : rawDelta
    paneLayoutStore.setPaneSize(options.paneKey, startPaneSize + delta, {
      defaultSize: options.defaultSize,
      minSize: options.minSize,
      maxSize: options.maxSize,
    })
  }

  const startResize = (event: MouseEvent) => {
    if (!isEnabled()) return
    isResizing.value = true
    startPointer =
      options.orientation === 'horizontal' ? event.clientY : event.clientX
    startPaneSize = paneSize.value
    document.body.style.userSelect = 'none'
    document.body.style.cursor =
      options.orientation === 'horizontal' ? 'row-resize' : 'col-resize'
    options.onResizeStart?.()
    window.addEventListener('mousemove', onResizeMove)
    window.addEventListener('mouseup', stopResize)
  }

  const resetSize = () =>
    paneLayoutStore.resetPaneSize(options.paneKey, {
      defaultSize: options.defaultSize,
      minSize: options.minSize,
      maxSize: options.maxSize,
    })

  onBeforeUnmount(() => {
    stopResize()
  })

  return {
    isResizing,
    paneSize,
    paneStyle,
    startResize,
    stopResize,
    resetSize,
  }
}
