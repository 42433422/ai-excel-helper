<template>
  <div>
    <div class="hero">
      <h1>Mod 库</h1>
      <p class="sub">
        集中存放与编辑 XCAGI 扩展；校验通过后一键推送到
        <code class="mono">XCAGI/mods</code>。
      </p>
      <div class="actions">
        <button type="button" class="btn btn-primary" @click="showCreate = true">新建 Mod</button>
        <label class="btn">
          导入 ZIP
          <input type="file" accept=".zip" class="hidden-file" @change="onImport" />
        </label>
        <button type="button" class="btn" :disabled="syncing" @click="doPull">从 XCAGI 拉回</button>
        <button type="button" class="btn" :disabled="syncing" @click="doPush">推送到 XCAGI</button>
      </div>
    </div>

    <div v-if="message" :class="['flash', messageOk ? 'flash-ok' : 'flash-err']">{{ message }}</div>

    <div v-if="loadErr" class="flash flash-err">{{ loadErr }}</div>

    <div v-if="loading" class="muted">加载中…</div>
    <div v-else class="grid">
      <router-link
        v-for="m in mods"
        :key="m.id"
        :to="'/mod/' + encodeURIComponent(m.id)"
        class="card"
      >
        <div class="card-top">
          <span class="pill" :class="m.ok ? 'pill-ok' : 'pill-warn'">{{ m.ok ? '通过' : '待修正' }}</span>
          <span v-if="m.primary" class="pill pill-primary">primary</span>
        </div>
        <div class="card-title">{{ m.name || m.id }}</div>
        <div class="card-meta mono">{{ m.id }} · v{{ m.version || '?' }}</div>
        <div v-if="m.warnings?.length" class="card-warn">
          {{ m.warnings[0] }}{{ m.warnings.length > 1 ? ' …' : '' }}
        </div>
        <div v-if="m.error" class="card-warn">{{ m.error }}</div>
      </router-link>
    </div>

    <div v-if="!loading && !mods.length" class="empty">库中暂无 Mod。可「新建」或「导入 ZIP」。</div>

    <div v-if="showCreate" class="modal-overlay" @click.self="showCreate = false">
      <div class="modal">
        <h2>新建 Mod</h2>
        <label class="label">目录名 / manifest.id</label>
        <input v-model="createId" class="input" placeholder="如 acme-pro" />
        <label class="label">显示名称</label>
        <input v-model="createName" class="input" placeholder="客户或产品名" />
        <div class="modal-actions">
          <button type="button" class="btn btn-ghost" @click="showCreate = false">取消</button>
          <button type="button" class="btn btn-primary" @click="submitCreate">创建</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../api'

const router = useRouter()
const mods = ref([])
const loading = ref(true)
const loadErr = ref('')
const message = ref('')
const messageOk = ref(true)
const syncing = ref(false)
const showCreate = ref(false)
const createId = ref('')
const createName = ref('')

function flash(msg, ok = true) {
  message.value = msg
  messageOk.value = ok
  setTimeout(() => {
    message.value = ''
  }, 5000)
}

async function load() {
  loading.value = true
  loadErr.value = ''
  try {
    const res = await api.listMods()
    mods.value = res.data || []
  } catch (e) {
    loadErr.value = e.message || String(e)
  } finally {
    loading.value = false
  }
}

async function submitCreate() {
  try {
    const res = await api.createMod(createId.value, createName.value)
    showCreate.value = false
    createId.value = ''
    createName.value = ''
    flash(`已创建 ${res.id}`)
    await load()
    router.push('/mod/' + encodeURIComponent(res.id))
  } catch (e) {
    flash(e.message || String(e), false)
  }
}

async function onImport(ev) {
  const f = ev.target.files?.[0]
  ev.target.value = ''
  if (!f) return
  try {
    const res = await api.importZip(f, true)
    flash(`已导入 ${res.id}`)
    await load()
  } catch (e) {
    flash(e.message || String(e), false)
  }
}

async function doPull() {
  syncing.value = true
  try {
    const res = await api.pull(null)
    flash(`已拉回: ${(res.pulled || []).join(', ') || '无'}`)
    await load()
  } catch (e) {
    flash(e.message || String(e), false)
  } finally {
    syncing.value = false
  }
}

async function doPush() {
  syncing.value = true
  try {
    const res = await api.push(null)
    flash(`已部署: ${(res.deployed || []).join(', ') || '无'}`)
  } catch (e) {
    flash(e.message || String(e), false)
  } finally {
    syncing.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.hero {
  margin-bottom: 1.75rem;
}
.hero h1 {
  margin: 0 0 0.35rem;
  font-size: 1.75rem;
  font-weight: 700;
}
.sub {
  margin: 0 0 1rem;
  color: var(--muted);
  max-width: 52ch;
}
.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}
.hidden-file {
  display: none;
}
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 1rem;
}
.card {
  display: block;
  padding: 1rem 1.1rem;
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 10px;
  color: inherit;
  text-decoration: none;
  transition: border-color 0.15s, transform 0.12s;
}
.card:hover {
  border-color: var(--accent-dim);
  transform: translateY(-2px);
  text-decoration: none;
}
.card-top {
  display: flex;
  gap: 0.35rem;
  margin-bottom: 0.5rem;
}
.pill {
  font-size: 0.68rem;
  padding: 0.15rem 0.45rem;
  border-radius: 4px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
.pill-ok {
  background: #14532d;
  color: #bbf7d0;
}
.pill-warn {
  background: #422006;
  color: #fde68a;
}
.pill-primary {
  background: #312e81;
  color: #c7d2fe;
}
.card-title {
  font-weight: 600;
  font-size: 1.05rem;
}
.card-meta {
  margin-top: 0.25rem;
  font-size: 0.8rem;
  color: var(--muted);
}
.card-warn {
  margin-top: 0.5rem;
  font-size: 0.78rem;
  color: var(--warn);
}
.empty {
  color: var(--muted);
  padding: 2rem 0;
  text-align: center;
}
.muted {
  color: var(--muted);
}
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.65);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 50;
  padding: 1rem;
}
.modal {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 1.25rem 1.5rem;
  width: 100%;
  max-width: 400px;
}
.modal h2 {
  margin: 0 0 1rem;
  font-size: 1.15rem;
}
.modal .label {
  margin-top: 0.75rem;
}
.modal .input {
  margin-bottom: 0.25rem;
}
.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
  margin-top: 1.25rem;
}
</style>
