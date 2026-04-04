<template>
  <div class="example-mod-view">
    <h1>企业版 PRO</h1>
    <p>这是一个企业级功能模块</p>
    <div class="status-card">
      <h3>Mod 状态</h3>
      <p>Mod ID: example-mod</p>
      <p>版本: 1.0.0</p>
      <button @click="testApi" class="btn">测试 API</button>
      <div v-if="apiResult" class="result">
        <pre>{{ JSON.stringify(apiResult, null, 2) }}</pre>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';

const apiResult = ref(null);

const testApi = async () => {
  try {
    const response = await fetch('/api/mod/example-mod/hello');
    const data = await response.json();
    apiResult.value = data;
  } catch (error) {
    apiResult.value = { error: error.message };
  }
};
</script>

<style scoped>
.example-mod-view {
  padding: 20px;
}

.status-card {
  background: var(--card-background, #fff);
  border-radius: 8px;
  padding: 20px;
  margin-top: 20px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.btn {
  background: var(--primary-color, #007bff);
  color: white;
  border: none;
  padding: 10px 20px;
  border-radius: 4px;
  cursor: pointer;
}

.btn:hover {
  opacity: 0.9;
}

.result {
  margin-top: 20px;
  padding: 10px;
  background: var(--code-bg, #f5f5f5);
  border-radius: 4px;
  overflow-x: auto;
}

pre {
  margin: 0;
  white-space: pre-wrap;
}
</style>
