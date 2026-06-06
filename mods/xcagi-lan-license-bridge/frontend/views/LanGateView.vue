<template>
  <div class="lan-gate-page">
    <LanGatePanel variant="page" :redirect-path="redirectPath" />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useRoute } from 'vue-router';
import LanGatePanel from '@/components/lan/LanGatePanel.vue';

const route = useRoute();
const redirectPath = computed(() => (route.query.redirect as string) || '/');
</script>

<style scoped>
.lan-gate-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #1f2937 0%, #111827 100%);
  padding: 24px;
}
</style>
