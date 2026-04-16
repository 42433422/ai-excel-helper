<template>
  <div class="wrap">
    <h1>页面不存在</h1>
    <p class="lead">{{ t('intro.notFound.lead') }}</p>
    <p class="muted">路径 <code class="mono">{{ route.path }}</code> 无对应路由。</p>
    <router-link to="/" class="btn btn-primary">返回 Mod 库</router-link>
  </div>
</template>

<script setup>
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()
const route = useRoute()
</script>

<style scoped>
.wrap {
  text-align: center;
  padding: 3rem 1rem;
}
h1 {
  margin: 0 0 0.75rem;
  font-size: 1.35rem;
}
.lead {
  color: var(--text);
  margin: 0 0 0.5rem;
  max-width: 42rem;
  margin-left: auto;
  margin-right: auto;
  line-height: 1.55;
}
.muted {
  color: var(--muted);
  margin-bottom: 1.5rem;
}
</style>
