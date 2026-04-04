<template>
  <nav class="kitten-workflow" aria-label="分析工作流">
    <div
      v-for="(step, idx) in steps"
      :key="step.key"
      :class="['kitten-workflow-step', stepClass(idx)]"
    >
      <span class="kitten-workflow-index">{{ idx + 1 }}</span>
      <span class="kitten-workflow-label">{{ step.label }}</span>
      <span class="kitten-workflow-desc">{{ step.desc }}</span>
    </div>
  </nav>
</template>

<script setup>
const props = defineProps({
  steps: {
    type: Array,
    default: () => []
  },
  activeIndex: {
    type: Number,
    default: 0
  }
})

const stepClass = (idx) => ({
  done: idx < props.activeIndex,
  current: idx === props.activeIndex,
  upcoming: idx > props.activeIndex
})
</script>

<style scoped>
.kitten-workflow {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 8px;
  padding: 10px 16px;
  background: #f1f5f9;
  border-bottom: 1px solid #e2e8f0;
}
.kitten-workflow-step {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 10px 12px;
  border-radius: 10px;
  background: #ffffff;
  border: 1px solid #e2e8f0;
  transition: border-color 0.15s, box-shadow 0.15s;
}
.kitten-workflow-step.done {
  border-color: #86efac;
  background: #f0fdf4;
}
.kitten-workflow-step.current {
  border-color: #3b82f6;
  box-shadow: 0 0 0 1px rgba(59, 130, 246, 0.25);
}
.kitten-workflow-step.upcoming {
  opacity: 0.72;
}
.kitten-workflow-index {
  font-size: 11px;
  font-weight: 700;
  color: #64748b;
}
.kitten-workflow-step.current .kitten-workflow-index {
  color: #1d4ed8;
}
.kitten-workflow-label {
  font-size: 13px;
  font-weight: 600;
  color: #0f172a;
}
.kitten-workflow-desc {
  font-size: 11px;
  color: #64748b;
  line-height: 1.35;
}

@media (max-width: 1100px) {
  .kitten-workflow {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 640px) {
  .kitten-workflow {
    grid-template-columns: 1fr;
  }
}
</style>
