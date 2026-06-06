<template>
  <div class="page-view" id="view-wechat-contacts" aria-busy="true" aria-label="正在跳转到数据来源" />
</template>

<script setup lang="ts">
import { onMounted } from 'vue';
import { useRouter } from 'vue-router';

const router = useRouter();

onMounted(() => {
  void router.replace({
    name: 'mod-erp-data-sources',
    query: { source: 'wechat_local_db' },
  });
});
</script>
