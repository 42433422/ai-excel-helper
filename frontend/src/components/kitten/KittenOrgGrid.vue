<template>
  <section class="kitten-org" aria-label="职能模块">
    <div class="kitten-org-title">工作台职能</div>
    <div class="kitten-org-grid">
      <div
        v-for="card in cards"
        :key="card.key"
        class="kitten-org-card"
        :class="{ active: card.key === activeLayerKey }"
      >
        <span class="kitten-org-card-title">{{ card.title }}</span>
        <span class="kitten-org-card-desc">{{ card.desc }}</span>
      </div>
    </div>
  </section>
</template>

<script setup>
defineProps({
  cards: {
    type: Array,
    default: () => []
  },
  activeLayerKey: {
    type: String,
    default: 'ingest'
  }
})
</script>

<style scoped>
.kitten-org {
  padding: 10px 16px 6px;
  border-bottom: 1px solid #e2e8f0;
  background: #ffffff;
}
.kitten-org-title {
  font-size: 12px;
  font-weight: 600;
  color: #475569;
  margin-bottom: 8px;
}
.kitten-org-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 8px;
}
.kitten-org-card {
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 10px 10px 12px;
  background: #f8fafc;
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-height: 0;
  transition: border-color 0.15s ease, box-shadow 0.15s ease, background-color 0.15s ease;
}
.kitten-org-card.active {
  border-color: #60a5fa;
  box-shadow: 0 0 0 1px rgba(59, 130, 246, 0.2);
  background: #eff6ff;
}
.kitten-org-card-title {
  font-size: 12px;
  font-weight: 600;
  color: #1e293b;
}
.kitten-org-card-desc {
  font-size: 11px;
  color: #64748b;
  line-height: 1.4;
}

@media (max-width: 1100px) {
  .kitten-org-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 640px) {
  .kitten-org-grid {
    grid-template-columns: 1fr;
  }
}
</style>
