<template>
  <main class="desktop-runtime">
    <section class="panel">
      <h1>桌面运行时</h1>
      <p>该页面在 web 版与桌面版共用，用于查看本地数据目录、模型目录和更新入口。</p>

      <button type="button" @click="refresh">刷新状态</button>
      <button v-if="isDesktopShell" type="button" @click="checkUpdates">检查桌面更新</button>
    </section>

    <section class="panel">
      <h2>运行状态</h2>
      <dl v-if="status">
        <dt>桌面模式</dt>
        <dd>{{ status.desktopMode ? '是' : '否' }}</dd>
        <dt>数据目录</dt>
        <dd>{{ status.dataDir }}</dd>
        <dt>数据库</dt>
        <dd>{{ status.database }}</dd>
        <dt>存储模式</dt>
        <dd>{{ storageModeLabel }}</dd>
        <dt>连接（脱敏）</dt>
        <dd>{{ status.databaseUrlRedacted || '—' }}</dd>
        <dt>Mod 目录</dt>
        <dd>{{ status.modsDir }}</dd>
        <dt>模型目录</dt>
        <dd>{{ status.modelsDir }}</dd>
      </dl>
      <p v-else>正在加载...</p>
    </section>

    <section class="panel">
      <h2>本地模型</h2>
      <ul v-if="models.length">
        <li v-for="model in models" :key="`${model.name}:${model.version}`">
          <strong>{{ model.name }}</strong> {{ model.version }}
          <span>{{ model.path }}</span>
        </li>
      </ul>
      <p v-else>暂无已安装模型。桌面版会在首次使用对应能力时按需下载。</p>
    </section>

    <section v-if="updateEvents.length" class="panel">
      <h2>更新事件</h2>
      <pre>{{ updateEvents.join('\n') }}</pre>
    </section>
  </main>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'

interface DesktopStatus {
  desktopMode: boolean
  dataDir: string
  database: string
  modsDir: string
  modelsDir: string
  storageMode?: string
  databaseUrlRedacted?: string
  profilePath?: string
}

interface ModelInfo {
  name: string
  version: string
  path: string
}

const status = ref<DesktopStatus | null>(null)
const models = ref<ModelInfo[]>([])
const updateEvents = ref<string[]>([])
const isDesktopShell = computed(() => Boolean(window.xcagiDesktop))

const storageModeLabel = computed(() => {
  const mode = status.value?.storageMode
  if (mode === 'local_sqlite') return '本地 SQLite'
  if (mode === 'remote_postgresql') return '远程 PostgreSQL'
  return mode || '—'
})

let unsubscribe: (() => void) | undefined

async function refresh() {
  const [statusResponse, modelsResponse] = await Promise.all([
    fetch('/api/desktop/status'),
    fetch('/api/desktop/models'),
  ])
  status.value = await statusResponse.json()
  const payload = await modelsResponse.json()
  models.value = payload.models || []
}

async function checkUpdates() {
  const result = await window.xcagiDesktop?.checkForUpdates()
  updateEvents.value.unshift(JSON.stringify(result))
}

onMounted(() => {
  void refresh()
  unsubscribe = window.xcagiDesktop?.onUpdateEvent((event) => {
    updateEvents.value.unshift(JSON.stringify(event))
  })
})

onUnmounted(() => {
  unsubscribe?.()
})
</script>

<style scoped>
.desktop-runtime {
  display: grid;
  gap: 16px;
  padding: 24px;
}

.panel {
  border: 1px solid #d9dee8;
  border-radius: 12px;
  padding: 18px;
  background: #fff;
}

button {
  margin-right: 12px;
  padding: 8px 14px;
  border: 1px solid #c8d0dc;
  border-radius: 8px;
  background: #f6f8fb;
  cursor: pointer;
}

dl {
  display: grid;
  grid-template-columns: 120px 1fr;
  gap: 8px 16px;
}

dt {
  font-weight: 600;
}

dd {
  margin: 0;
  word-break: break-all;
}

li span {
  display: block;
  color: #6b7280;
  word-break: break-all;
}

pre {
  overflow: auto;
  max-height: 240px;
}
</style>
