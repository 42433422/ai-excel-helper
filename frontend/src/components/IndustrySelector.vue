<template>
  <div class="industry-selector" :class="{ 'is-expanded': isExpanded }">
    <div class="selector-trigger" @click="toggleExpand">
      <span class="industry-icon"><i class="fa fa-industry" aria-hidden="true"></i></span>
      <span class="industry-name">{{ currentIndustryName }}</span>
      <span class="industry-unit">{{ primaryUnit }}</span>
      <span class="expand-icon" :class="{ rotated: isExpanded }">▼</span>
    </div>

    <div v-if="isExpanded" class="selector-dropdown">
      <div class="dropdown-list">
        <div
          v-for="industry in industries"
          :key="industry.id"
          class="dropdown-item"
          :class="{ active: industry.id === currentIndustryId }"
          @click="selectIndustry(industry.id)"
        >
          <span class="item-name">{{ industry.name }}</span>
          <span class="item-unit">{{ getIndustryUnit(industry.id) }}</span>
          <span class="item-check" v-if="industry.id === currentIndustryId"><i class="fa fa-check" aria-hidden="true"></i></span>
        </div>
      </div>
    </div>

    <div v-if="isExpanded" class="dropdown-overlay" @click="closeDropdown"></div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useIndustryStore } from '@/stores/industry'

const industryStore = useIndustryStore()

const isExpanded = ref(false)

const industries = computed(() => industryStore.industries)
const currentIndustryId = computed(() => industryStore.currentIndustryId)
const currentIndustryName = computed(() => industryStore.currentIndustry?.name || '加载中...')
const primaryUnit = computed(() => industryStore.currentConfig?.units?.primary || '')

const getIndustryUnit = (industryId) => {
  const industry = industries.value.find(i => i.id === industryId)
  return ''
}

const toggleExpand = () => {
  isExpanded.value = !isExpanded.value
}

const closeDropdown = () => {
  isExpanded.value = false
}

const selectIndustry = async (industryId) => {
  if (industryId === currentIndustryId.value) {
    closeDropdown()
    return
  }

  const success = await industryStore.switchIndustry(industryId)
  if (success) {
    closeDropdown()
  }
}

onMounted(async () => {
  if (!industryStore.isLoaded) {
    await industryStore.initialize()
  }
})
</script>

<style scoped>
.industry-selector {
  position: relative;
}

.selector-trigger {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 15px;
  cursor: pointer;
  transition: background 0.15s ease;
  user-select: none;
  color: rgba(255, 255, 255, 0.85);
  border-radius: 4px;
  margin: 2px 8px;
}

.selector-trigger:hover {
  background: rgba(255, 255, 255, 0.1);
}

.industry-icon {
  font-size: 14px;
}

.industry-name {
  font-weight: 500;
  flex: 1;
}

.industry-unit {
  font-size: 12px;
  padding: 2px 6px;
  background: rgba(79, 172, 254, 0.2);
  color: #4facfe;
  border-radius: 4px;
}

.expand-icon {
  font-size: 10px;
  color: rgba(255, 255, 255, 0.5);
  transition: transform 0.2s ease;
}

.expand-icon.rotated {
  transform: rotate(180deg);
}

.selector-dropdown {
  position: absolute;
  top: 100%;
  left: 8px;
  right: 8px;
  background: #1a1a2e;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 6px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.3);
  z-index: 1000;
  overflow: hidden;
  margin-top: 4px;
}

.dropdown-list {
  max-height: 250px;
  overflow-y: auto;
}

.dropdown-item {
  display: flex;
  align-items: center;
  padding: 10px 12px;
  cursor: pointer;
  transition: background 0.15s ease;
  color: rgba(255, 255, 255, 0.85);
}

.dropdown-item:hover {
  background: rgba(255, 255, 255, 0.05);
}

.dropdown-item.active {
  background: rgba(79, 172, 254, 0.15);
  color: #fff;
}

.item-name {
  flex: 1;
}

.item-unit {
  font-size: 11px;
  padding: 2px 5px;
  background: rgba(79, 172, 254, 0.15);
  color: #4facfe;
  border-radius: 3px;
  margin-right: 8px;
}

.item-check {
  color: #4facfe;
  font-weight: bold;
  margin-left: 8px;
}

.dropdown-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 999;
}
</style>
