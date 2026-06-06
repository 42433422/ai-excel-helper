<template>
  <div
    class="pane-resize-handle"
    :class="[`pane-resize-handle--${orientation}`, { 'is-disabled': disabled }]"
    role="separator"
    :aria-orientation="orientation"
    :aria-label="label"
    @mousedown.prevent="$emit('resize-start', $event)"
    @dblclick="$emit('reset')"
  >
    <span class="pane-resize-handle__grip" aria-hidden="true"></span>
  </div>
</template>

<script setup lang="ts">
withDefaults(
  defineProps<{
    /** Vertical bar between columns (width); horizontal bar between rows (height). */
    orientation?: 'vertical' | 'horizontal'
    label?: string
    disabled?: boolean
  }>(),
  {
    orientation: 'vertical',
    label: '调整面板尺寸',
    disabled: false,
  }
)

defineEmits(['resize-start', 'reset'])
</script>

<style scoped>
.pane-resize-handle {
  position: absolute;
  z-index: 35;
}

.pane-resize-handle.is-disabled {
  pointer-events: none;
  opacity: 0.45;
}

/* Vertical separator between columns — drag changes width */
.pane-resize-handle--vertical {
  top: 0;
  right: -4px;
  width: 8px;
  height: 100%;
  cursor: col-resize;
}

/* Horizontal separator between rows — drag changes height */
.pane-resize-handle--horizontal {
  left: 0;
  bottom: -4px;
  width: 100%;
  height: 8px;
  cursor: row-resize;
}

.pane-resize-handle__grip {
  position: absolute;
  border-radius: 999px;
  background: rgba(148, 163, 184, 0.42);
  box-shadow: 0 0 0 1px rgba(255, 255, 255, 0.44);
  transition: background 160ms ease, box-shadow 160ms ease;
}

.pane-resize-handle--vertical .pane-resize-handle__grip {
  top: 50%;
  right: 2px;
  transform: translateY(-50%);
  width: 4px;
  height: 64px;
}

.pane-resize-handle--horizontal .pane-resize-handle__grip {
  left: 50%;
  bottom: 2px;
  transform: translateX(-50%);
  width: 64px;
  height: 4px;
}

.pane-resize-handle:hover .pane-resize-handle__grip {
  background: rgba(59, 130, 246, 0.72);
  box-shadow: 0 0 0 1px rgba(191, 219, 254, 0.88);
}
</style>
