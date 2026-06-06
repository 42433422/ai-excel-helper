<template>
  <div class="sidebar-menu-entry">
    <button
      class="menu-item"
      type="button"
      :class="{
        active: isActive,
        pressing: isPressing,
        dragging: isDragging,
        'has-children': hasChildren,
        expanded: isExpanded,
        'nav-reveal-active': navRevealActive,
      }"
      :style="navStaggerStyle"
      :data-view="item.key"
      :aria-label="item.name"
      :aria-current="isActive && !hasActiveChild ? 'page' : undefined"
      :aria-expanded="hasChildren ? isExpanded : undefined"
      :title="item.name"
      @contextmenu.prevent
      @pointerdown="$emit('reorder-pointer-down', $event)"
      @keydown="$emit('keydown', $event)"
      @click="$emit('parent-click')"
    >
      <span class="menu-item-icon" aria-hidden="true">
        <i class="fa" :class="item.iconClass"></i>
      </span>
      <span>{{ item.name }}</span>
      <span v-if="hasChildren" class="menu-item-expand-arrow" aria-hidden="true">
        <i class="fa fa-angle-down"></i>
      </span>
      <SidebarDragHoldProgress v-if="isPressing" :duration-ms="longPressMs" />
    </button>
    <Transition name="submenu-expand">
      <div v-if="hasChildren && isExpanded" class="submenu-expand-grid">
        <div class="submenu-expand-inner">
          <div class="submenu">
            <button
              v-for="child in item.children"
              :key="child.key"
              class="menu-item submenu-item"
              type="button"
              :class="{ active: activeView === child.key }"
              :data-view="child.key"
              :aria-label="child.name"
              :aria-current="activeView === child.key ? 'page' : undefined"
              :title="child.name"
              @click="$emit('select-view', child.key)"
            >
              <span class="menu-item-icon" aria-hidden="true">
                <i class="fa" :class="child.iconClass"></i>
              </span>
              <span>{{ child.name }}</span>
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import SidebarDragHoldProgress from '@/components/SidebarDragHoldProgress.vue'

const props = defineProps({
  item: {
    type: Object,
    required: true,
  },
  activeView: {
    type: String,
    required: true,
  },
  isActive: {
    type: Boolean,
    default: false,
  },
  hasActiveChild: {
    type: Boolean,
    default: false,
  },
  isExpanded: {
    type: Boolean,
    default: false,
  },
  isPressing: {
    type: Boolean,
    default: false,
  },
  isDragging: {
    type: Boolean,
    default: false,
  },
  navRevealActive: {
    type: Boolean,
    default: false,
  },
  navStaggerStyle: {
    type: Object,
    default: () => ({}),
  },
  longPressMs: {
    type: Number,
    default: 1000,
  },
})

defineEmits(['parent-click', 'select-view', 'reorder-pointer-down', 'keydown'])

const hasChildren = computed(() => Boolean(props.item.children?.length))
</script>

<style scoped>
.sidebar-menu-entry {
  display: flex;
  flex-direction: column;
  width: 100%;
  contain: layout style;
}

.menu-item-expand-arrow {
  margin-left: auto;
  padding-left: 4px;
  display: inline-flex;
  align-items: center;
  font-size: 12px;
  transition: transform 0.2s ease;
}

.menu-item.has-children.expanded .menu-item-expand-arrow {
  transform: rotate(180deg);
}

.submenu-expand-grid {
  display: grid;
  grid-template-rows: 1fr;
}

.submenu-expand-inner {
  overflow: hidden;
  min-height: 0;
}

.submenu {
  display: flex;
  flex-direction: column;
}

.submenu-item {
  padding-left: 40px;
  font-size: 13px;
}

.submenu-expand-enter-active,
.submenu-expand-leave-active {
  display: grid;
  grid-template-rows: 1fr;
  overflow: hidden;
  transition: grid-template-rows 0.2s ease, opacity 0.2s ease;
}

.submenu-expand-enter-from,
.submenu-expand-leave-to {
  grid-template-rows: 0fr;
  opacity: 0;
}
</style>
