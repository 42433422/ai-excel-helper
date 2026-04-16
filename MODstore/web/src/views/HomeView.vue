<template>
  <div>
    <div class="hero">
      <div class="hero-main">
        <h1>{{ t('intro.home.title') }}</h1>
        <p class="sub">
          {{ t('intro.home.leadBefore') }}
          <router-link to="/author">{{ t('intro.home.authorLink') }}</router-link>
          {{ t('intro.home.leadAfter') }}
          {{ t('intro.home.leadTail') }}
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
        <div
          v-if="!installedLoading && !installedErr && (installedMods.length || installedPath)"
          class="primary-banner"
          role="status"
        >
          <template v-if="primaryMods.length === 1">
            <span class="primary-banner-label">{{ t('intro.home.currentPrimaryLabel') }}</span>
            <span class="primary-banner-value">{{
              t('intro.home.currentPrimaryLine', {
                name: primaryMods[0].name || primaryMods[0].id,
                id: primaryMods[0].id,
              })
            }}</span>
          </template>
          <template v-else-if="primaryMods.length === 0">
            <span class="primary-banner-none">{{ t('intro.home.currentPrimaryNone') }}</span>
          </template>
          <template v-else>
            <span class="primary-banner-warn">{{
              t('intro.home.currentPrimaryMany', { count: primaryMods.length })
            }}</span>
          </template>
        </div>
      </div>
      <aside class="hero-monitor" aria-label="XCAGI mods">
        <div class="monitor-bezel">
          <div class="monitor-titlebar">
            <span class="monitor-led" :class="{ on: monitorOk }" aria-hidden="true" />
            <span class="monitor-title">{{ t('intro.home.monitorTitle') }}</span>
          </div>
          <p class="monitor-sub">{{ t('intro.home.monitorSub') }}</p>
          <div v-if="installedLoading" class="monitor-body muted">{{ t('intro.home.monitorLoading') }}</div>
          <div v-else-if="installedErr" class="monitor-body monitor-err">{{ t('intro.home.monitorErr') }}：{{ installedErr }}</div>
          <div v-else class="monitor-body">
            <div v-if="primaryMods.length === 1" class="monitor-current">
              <div class="monitor-current-k">{{ t('intro.home.monitorCurrentTitle') }}</div>
              <div class="monitor-current-v">
                {{ t('intro.home.currentPrimaryLine', { name: primaryMods[0].name || primaryMods[0].id, id: primaryMods[0].id }) }}
              </div>
            </div>
            <div v-else-if="primaryMods.length === 0 && installedMods.length" class="monitor-current monitor-current-warn">
              <div class="monitor-current-k">{{ t('intro.home.monitorCurrentTitle') }}</div>
              <div class="monitor-current-v small">{{ t('intro.home.currentPrimaryNone') }}</div>
            </div>
            <div v-else-if="primaryMods.length > 1" class="monitor-current monitor-current-warn">
              <div class="monitor-current-k">{{ t('intro.home.monitorCurrentTitle') }}</div>
              <div class="monitor-current-v small">
                {{ t('intro.home.currentPrimaryMany', { count: primaryMods.length }) }}
              </div>
            </div>
            <div v-if="installedPath" class="monitor-path mono" :title="installedPath">
              {{ t('intro.home.monitorPath') }}：<span class="path-ellipsis">{{ installedPath }}</span>
            </div>
            <ul v-if="installedMods.length" class="monitor-list">
              <li v-for="im in installedMods" :key="im.id" class="monitor-li">
                <router-link
                  :to="{ name: 'mod', params: { id: im.id } }"
                  class="monitor-row monitor-row-link"
                  :title="t('intro.home.monitorRowLinkTitle')"
                >
                  <div class="monitor-row-head">
                    <span class="monitor-row-name">{{ im.name || im.id }}</span>
                    <span class="monitor-row-pills">
                      <span v-if="im.primary" class="pill pill-primary">{{ t('intro.home.monitorPrimary') }}</span>
                      <span v-if="im.ok === false" class="pill pill-warn" :title="im.error || ''">!</span>
                    </span>
                  </div>
                  <div class="monitor-row-meta mono">{{ im.id }}<template v-if="im.version"> · v{{ im.version }}</template></div>
                </router-link>
              </li>
            </ul>
            <div v-else class="monitor-empty muted">{{ installedNote || t('intro.home.monitorEmpty') }}</div>
          </div>
          <p class="monitor-footer muted">{{ t('intro.home.monitorFooter') }}</p>
        </div>
      </aside>
    </div>

    <div v-if="message" :class="['flash', messageOk ? 'flash-ok' : 'flash-err']">{{ message }}</div>

    <div v-if="loadErr" class="flash flash-err">{{ loadErr }}</div>

    <div v-if="loading" class="muted">加载中…</div>
    <div v-else class="grid-wrap">
      <p v-if="mods.length" class="grid-hint muted">{{ t('intro.home.gridHint') }}</p>
      <div class="grid">
      <router-link
        v-for="m in mods"
        :key="m.id"
        :to="{ name: 'mod', params: { id: m.id } }"
        class="card"
      >
        <div class="card-top">
          <span class="pill" :class="m.ok ? 'pill-ok' : 'pill-warn'">{{ m.ok ? '通过' : '待修正' }}</span>
          <span v-if="m.primary" class="pill pill-primary">primary</span>
        </div>
        <div class="card-title">{{ m.name || m.id }}</div>
        <div v-if="cardBlurb(m)" class="card-blurb">{{ cardBlurb(m) }}</div>
        <div class="card-meta mono">{{ m.id }} · v{{ m.version || '?' }}</div>
        <div v-if="m.warnings?.length" class="card-warn">
          {{ m.warnings[0] }}{{ m.warnings.length > 1 ? ' …' : '' }}
        </div>
        <div v-if="m.error" class="card-warn">{{ m.error }}</div>
      </router-link>
      </div>
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
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { api } from '../api'

const { t } = useI18n()
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
const installedMods = ref([])
const installedPath = ref('')
const installedNote = ref('')
const installedErr = ref('')
const installedLoading = ref(false)
const monitorOk = ref(false)

/** manifest primary: true，决定宿主侧栏/角标等「主扩展」 */
const primaryMods = computed(() => installedMods.value.filter((m) => m.primary === true))

function flash(msg, ok = true) {
  message.value = msg
  messageOk.value = ok
  setTimeout(() => {
    message.value = ''
  }, 5000)
}

/** manifest.library_blurb，否则用 description 一行摘要 */
function cardBlurb(m) {
  if (!m || typeof m !== 'object') return ''
  const b = typeof m.library_blurb === 'string' ? m.library_blurb.trim() : ''
  if (b) return b
  const d = typeof m.description === 'string' ? m.description.trim() : ''
  if (!d) return ''
  const one = d.replace(/\s+/g, ' ')
  return one.length > 120 ? `${one.slice(0, 117)}…` : one
}

async function load() {
  loading.value = true
  loadErr.value = ''
  try {
    const res = await api.listMods()
    if (!res || typeof res !== 'object') {
      loadErr.value = '接口返回格式异常（非 JSON 对象）。'
      mods.value = []
      return
    }
    const rows = res.data
    mods.value = Array.isArray(rows) ? rows : []
  } catch (e) {
    loadErr.value = e.message || String(e)
    mods.value = []
  } finally {
    loading.value = false
  }
}

async function loadInstalled() {
  installedLoading.value = true
  installedErr.value = ''
  installedNote.value = ''
  try {
    const res = await api.xcagiInstalledMods()
    monitorOk.value = !!(res && res.ok)
    installedPath.value = res?.mods_path || ''
    installedMods.value = Array.isArray(res?.mods) ? res.mods : []
    if (res?.note) installedNote.value = String(res.note)
    if (res && res.ok === false) installedErr.value = res.error || 'unknown'
  } catch (e) {
    monitorOk.value = false
    installedErr.value = e.message || String(e)
    installedMods.value = []
    installedPath.value = ''
  } finally {
    installedLoading.value = false
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
    await loadInstalled()
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
    await loadInstalled()
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
    await loadInstalled()
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
    await load()
    await loadInstalled()
  } catch (e) {
    flash(e.message || String(e), false)
  } finally {
    syncing.value = false
  }
}

onMounted(async () => {
  await Promise.all([load(), loadInstalled()])
})
</script>

<style scoped>
.hero {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  gap: 1.25rem 1.5rem;
  margin-bottom: 1.75rem;
}
.hero-main {
  flex: 1 1 280px;
  min-width: 0;
}
.primary-banner {
  margin-top: 1rem;
  padding: 0.65rem 0.85rem;
  border-radius: 8px;
  border: 1px solid var(--border);
  background: var(--bg-elevated);
  font-size: 0.82rem;
  line-height: 1.45;
  max-width: 62ch;
}
.primary-banner-label {
  color: var(--muted);
  margin-right: 0.35rem;
}
.primary-banner-value {
  font-weight: 600;
  color: var(--text);
}
.primary-banner-none,
.primary-banner-warn {
  color: var(--muted);
}
.primary-banner-warn {
  color: var(--warn);
}
.hero-monitor {
  flex: 0 1 320px;
  min-width: 260px;
  max-width: 100%;
}
.monitor-bezel {
  border-radius: 12px;
  padding: 0.85rem 1rem;
  background: linear-gradient(160deg, #0f172a 0%, #020617 55%, #0c1222 100%);
  border: 2px solid #334155;
  box-shadow:
    inset 0 0 0 1px rgba(148, 163, 184, 0.12),
    0 12px 28px rgba(0, 0, 0, 0.45);
  color: #e2e8f0;
}
.monitor-titlebar {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.35rem;
}
.monitor-led {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #64748b;
  box-shadow: inset 0 0 0 1px rgba(0, 0, 0, 0.35);
  flex-shrink: 0;
}
.monitor-led.on {
  background: #22c55e;
  box-shadow: 0 0 10px rgba(34, 197, 94, 0.65);
}
.monitor-title {
  font-size: 0.82rem;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: #94a3b8;
}
.monitor-sub {
  margin: 0 0 0.65rem;
  font-size: 0.72rem;
  line-height: 1.4;
  color: #64748b;
}
.monitor-body {
  font-size: 0.8rem;
  min-height: 4.5rem;
}
.monitor-current {
  margin-bottom: 0.65rem;
  padding: 0.5rem 0.55rem;
  border-radius: 6px;
  background: rgba(15, 23, 42, 0.65);
  border: 1px solid rgba(71, 85, 105, 0.85);
}
.monitor-current-warn {
  border-color: rgba(180, 83, 9, 0.55);
}
.monitor-current-k {
  font-size: 0.62rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #64748b;
  margin-bottom: 0.2rem;
}
.monitor-current-v {
  font-size: 0.88rem;
  font-weight: 600;
  color: #e2e8f0;
  line-height: 1.35;
}
.monitor-current-v.small {
  font-size: 0.72rem;
  font-weight: 400;
  color: #94a3b8;
}
.monitor-err {
  color: #fca5a5;
  font-size: 0.78rem;
}
.monitor-path {
  font-size: 0.68rem;
  color: #64748b;
  margin-bottom: 0.5rem;
  word-break: break-all;
}
.path-ellipsis {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.monitor-list {
  list-style: none;
  margin: 0;
  padding: 0;
  max-height: 11rem;
  overflow-y: auto;
}
.monitor-li {
  margin: 0;
  padding: 0;
  border-bottom: 1px solid rgba(51, 65, 85, 0.85);
}
.monitor-li:last-child {
  border-bottom: none;
}
.monitor-row {
  padding: 0.45rem 0;
}
.monitor-row-link {
  display: block;
  color: inherit;
  text-decoration: none;
  border-radius: 6px;
  margin: 0 -0.2rem;
  padding-left: 0.2rem;
  padding-right: 0.2rem;
}
.monitor-row-link:hover {
  background: rgba(51, 65, 85, 0.45);
  text-decoration: none;
}
.monitor-row-link:focus-visible {
  outline: 2px solid rgba(129, 140, 248, 0.9);
  outline-offset: 2px;
}
.monitor-row-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
}
.monitor-row-pills {
  display: flex;
  flex-shrink: 0;
  gap: 0.25rem;
  align-items: center;
}
.monitor-row-name {
  font-weight: 600;
  color: #f1f5f9;
  font-size: 0.8rem;
  min-width: 0;
}
.monitor-row-meta {
  margin-top: 0.15rem;
  font-size: 0.72rem;
  color: #94a3b8;
}
.monitor-empty {
  padding: 0.5rem 0;
  font-size: 0.78rem;
}
.monitor-footer {
  margin: 0.65rem 0 0;
  font-size: 0.65rem;
  color: #475569;
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
.grid-wrap {
  margin-top: 0.25rem;
}
.grid-hint {
  margin: 0 0 0.65rem;
  font-size: 0.82rem;
  line-height: 1.45;
}
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 1rem;
}
.card {
  display: block;
  cursor: pointer;
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
.card-blurb {
  margin-top: 0.35rem;
  font-size: 0.78rem;
  line-height: 1.4;
  color: var(--muted);
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 3;
  line-clamp: 3;
  overflow: hidden;
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
