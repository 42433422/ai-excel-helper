<template>
  <div>
    <div class="back-row">
      <router-link to="/" class="back">← 返回列表</router-link>
    </div>

    <div v-if="err" class="flash flash-err">{{ err }}</div>
    <div v-if="msg" class="flash flash-ok">{{ msg }}</div>

    <div v-if="loading" class="muted">加载中…</div>

    <template v-else-if="detail">
      <header class="head">
        <div>
          <h1>{{ detail.manifest?.name || id }}</h1>
          <p class="mono meta">{{ id }} · v{{ detail.manifest?.version }}</p>
        </div>
        <div class="head-actions">
          <span class="pill" :class="detail.validation_ok ? 'pill-ok' : 'pill-warn'">
            {{ detail.validation_ok ? '校验通过' : '有警告' }}
          </span>
          <a class="btn" :href="exportUrl" download>导出 ZIP</a>
          <button type="button" class="btn" @click="doPushOne">推送到 XCAGI</button>
          <button type="button" class="btn btn-danger" @click="confirmDelete">删除</button>
        </div>
      </header>

      <div v-if="detail.warnings?.length" class="warn-box">
        <div class="label">校验提示</div>
        <ul>
          <li v-for="(w, i) in detail.warnings" :key="i">{{ w }}</li>
        </ul>
      </div>

      <div class="tabs">
        <button
          type="button"
          :class="['tab', tab === 'form' && 'tab-on']"
          @click="tab = 'form'"
        >
          表单
        </button>
        <button
          type="button"
          :class="['tab', tab === 'json' && 'tab-on']"
          @click="tab = 'json'"
        >
          manifest.json
        </button>
        <button
          type="button"
          :class="['tab', tab === 'files' && 'tab-on']"
          @click="tab = 'files'"
        >
          文件
        </button>
      </div>

      <div v-show="tab === 'form'" class="panel">
        <div class="grid2">
          <div>
            <label class="label">id（与目录名一致）</label>
            <input class="input" :value="id" disabled />
          </div>
          <div>
            <label class="label">版本</label>
            <input v-model="form.version" class="input" />
          </div>
          <div class="full">
            <label class="label">名称</label>
            <input v-model="form.name" class="input" />
          </div>
          <div class="full">
            <label class="label">作者</label>
            <input v-model="form.author" class="input" />
          </div>
          <div class="full">
            <label class="label">描述</label>
            <input v-model="form.description" class="input" />
          </div>
          <div>
            <label class="label">
              <input v-model="form.primary" type="checkbox" />
              primary（主 Mod）
            </label>
          </div>
        </div>
        <button type="button" class="btn btn-primary" style="margin-top: 1rem" @click="saveFromForm">
          保存表单到 manifest
        </button>
      </div>

      <div v-show="tab === 'json'" class="panel">
        <label class="label">完整 JSON（须保持 id 与目录名一致）</label>
        <textarea v-model="jsonText" class="textarea" spellcheck="false"></textarea>
        <button type="button" class="btn btn-primary" style="margin-top: 0.75rem" @click="saveJson">
          保存 JSON
        </button>
      </div>

      <div v-show="tab === 'files'" class="panel">
        <ul class="file-list mono">
          <li v-for="f in detail.files" :key="f">{{ f }}</li>
        </ul>
        <p v-if="!detail.files?.length" class="muted">无文件或未扫描到。</p>
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '../api'

const props = defineProps({ id: { type: String, required: true } })

const route = useRoute()
const router = useRouter()
const id = computed(() => decodeURIComponent(props.id || route.params.id))

const loading = ref(true)
const err = ref('')
const msg = ref('')
const detail = ref(null)
const tab = ref('form')
const jsonText = ref('')

const form = ref({
  name: '',
  version: '',
  author: '',
  description: '',
  primary: false,
})

const exportUrl = computed(() => api.exportUrl(id.value))

function syncFormFromManifest(m) {
  form.value = {
    name: m.name || '',
    version: m.version || '',
    author: m.author || '',
    description: m.description || '',
    primary: !!m.primary,
  }
}

async function load() {
  loading.value = true
  err.value = ''
  msg.value = ''
  try {
    const d = await api.getMod(id.value)
    detail.value = d
    jsonText.value = JSON.stringify(d.manifest, null, 2)
    syncFormFromManifest(d.manifest)
  } catch (e) {
    err.value = e.message || String(e)
    detail.value = null
  } finally {
    loading.value = false
  }
}

watch(
  () => route.params.id,
  () => load()
)

async function saveJson() {
  err.value = ''
  msg.value = ''
  let parsed
  try {
    parsed = JSON.parse(jsonText.value)
  } catch (e) {
    err.value = 'JSON 解析失败: ' + e.message
    return
  }
  try {
    const res = await api.putManifest(id.value, parsed)
    msg.value = '已保存' + (res.warnings?.length ? '（仍有提示，见上方）' : '')
    await load()
  } catch (e) {
    err.value = e.message || String(e)
  }
}

async function saveFromForm() {
  let m
  try {
    m = JSON.parse(jsonText.value)
  } catch {
    m = JSON.parse(JSON.stringify(detail.value.manifest))
  }
  m.id = id.value
  m.name = form.value.name
  m.version = form.value.version
  m.author = form.value.author
  m.description = form.value.description
  m.primary = form.value.primary
  jsonText.value = JSON.stringify(m, null, 2)
  try {
    await api.putManifest(id.value, m)
    msg.value = '已保存'
    await load()
  } catch (e) {
    err.value = e.message || String(e)
  }
}

async function doPushOne() {
  try {
    const res = await api.push([id.value])
    msg.value = '已部署: ' + (res.deployed || []).join(', ')
  } catch (e) {
    err.value = e.message || String(e)
  }
}

async function confirmDelete() {
  if (!confirm(`确定从库中删除 Mod「${id.value}」？不可恢复。`)) return
  try {
    await api.deleteMod(id.value)
    router.push('/')
  } catch (e) {
    err.value = e.message || String(e)
  }
}

onMounted(load)
</script>

<style scoped>
.back-row {
  margin-bottom: 1rem;
}
.back {
  color: var(--muted);
  font-size: 0.9rem;
}
.head {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 1.25rem;
}
.head h1 {
  margin: 0;
  font-size: 1.5rem;
}
.meta {
  margin: 0.35rem 0 0;
  color: var(--muted);
  font-size: 0.85rem;
}
.head-actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem;
}
.pill {
  font-size: 0.68rem;
  padding: 0.2rem 0.5rem;
  border-radius: 4px;
  font-weight: 600;
}
.pill-ok {
  background: #14532d;
  color: #bbf7d0;
}
.pill-warn {
  background: #422006;
  color: #fde68a;
}
.warn-box {
  background: #1c1508;
  border: 1px solid #422006;
  border-radius: 8px;
  padding: 0.75rem 1rem;
  margin-bottom: 1rem;
}
.warn-box ul {
  margin: 0.35rem 0 0 1.1rem;
  color: var(--warn);
  font-size: 0.88rem;
}
.tabs {
  display: flex;
  gap: 0.25rem;
  margin-bottom: 0.75rem;
}
.tab {
  padding: 0.4rem 0.85rem;
  border: 1px solid var(--border);
  background: transparent;
  color: var(--muted);
  border-radius: 6px;
  cursor: pointer;
  font-family: var(--font-sans);
}
.tab-on {
  color: var(--accent);
  border-color: var(--accent-dim);
  background: var(--bg-elevated);
}
.panel {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 1.1rem 1.25rem;
}
.grid2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.75rem 1rem;
}
.full {
  grid-column: 1 / -1;
}
.file-list {
  margin: 0;
  padding-left: 1.2rem;
  font-size: 0.82rem;
  color: var(--muted);
  max-height: 420px;
  overflow: auto;
}
.muted {
  color: var(--muted);
}
</style>
