<template>
  <div class="card">
    <div class="card-header">数据库访问</div>
    <p class="muted" style="margin-bottom: 12px">
      一级：只读令牌（请求头 <code>X-FHD-Db-Read-Token</code>，对应服务器
      <code>FHD_DB_READ_TOKEN</code>）。二级：写入/导入令牌（<code>X-FHD-Db-Write-Token</code> /
      聊天 <code>db_write_token</code>，对应 <code>FHD_DB_WRITE_TOKEN</code>）。以下仅保存在本机浏览器，不会回传明文到状态接口。
    </p>
    <div v-if="statusLoading" class="muted">加载服务器状态…</div>
    <div v-else-if="statusError" class="muted">{{ statusError }}</div>
    <ul v-else class="muted" style="margin: 0 0 12px 1.2em">
      <li>一级（只读）服务器已配置：<strong>{{ status?.read_token_configured ? "是" : "否" }}</strong></li>
      <li>二级（写入）服务器已配置：<strong>{{ status?.write_token_configured ? "是" : "否" }}</strong></li>
    </ul>
    <div class="form-group">
      <label>一级密码（只读）</label>
      <input v-model="readInput" type="password" autocomplete="off" placeholder="与 FHD_DB_READ_TOKEN 一致" />
    </div>
    <div class="form-group">
      <label>二级密码（写入/导入）</label>
      <input v-model="writeInput" type="password" autocomplete="off" placeholder="与 FHD_DB_WRITE_TOKEN 一致" />
    </div>
    <button type="button" class="btn-primary" @click="onSave">保存到本机</button>
    <p v-if="saveMsg" class="muted" style="margin-top: 8px">{{ saveMsg }}</p>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue";
import {
  fetchDbTokensStatus,
  readStoredDbTokens,
  saveStoredDbTokens,
} from "./dbTokenHeaders";

const props = defineProps<{ apiBase?: string }>();

const status = ref<{ read_token_configured: boolean; write_token_configured: boolean } | null>(null);
const statusLoading = ref(true);
const statusError = ref("");
const readInput = ref("");
const writeInput = ref("");
const saveMsg = ref("");

onMounted(async () => {
  const s = readStoredDbTokens();
  readInput.value = s.read;
  writeInput.value = s.write;
  try {
    status.value = await fetchDbTokensStatus(props.apiBase || "");
  } catch (e: unknown) {
    statusError.value = e instanceof Error ? e.message : String(e);
  } finally {
    statusLoading.value = false;
  }
});

function onSave() {
  saveStoredDbTokens(readInput.value, writeInput.value);
  saveMsg.value = "已保存到 localStorage（xcagi_db_read_token / xcagi_db_write_token）。";
}
</script>
