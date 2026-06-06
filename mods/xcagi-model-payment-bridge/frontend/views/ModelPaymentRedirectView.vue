<template>
  <div class="page-view" id="view-model-payment" aria-busy="true" aria-label="正在跳转到系统设置" />
</template>

<script setup lang="ts">
import { onMounted } from 'vue';
import { useRouter } from 'vue-router';

const router = useRouter();

onMounted(() => {
  void router.replace({
    path: '/settings',
    query: { section: 'model-payment' },
  });
});
</script>
