<template>
  <div class="detail-page">
    <div class="back-row">
      <router-link to="/" class="back">{{ t('intro.modDetail.back') }}</router-link>
    </div>

    <div v-if="err" class="flash flash-err">{{ err }}</div>
    <div v-if="msg" class="flash flash-ok">{{ msg }}</div>

    <div v-if="loading" class="muted">{{ t('intro.modDetail.loading') }}</div>

    <template v-else-if="detail">
      <header class="head">
        <div class="head-main">
          <h1>{{ detail.manifest?.name || id }}</h1>
          <p class="mono meta">{{ id }} · v{{ detail.manifest?.version }}</p>
          <p v-if="detail.manifest?.description" class="desc">{{ detail.manifest.description }}</p>
        </div>
        <div class="head-actions">
          <span class="pill" :class="detail.validation_ok ? 'pill-ok' : 'pill-warn'">
            {{ detail.validation_ok ? t('intro.modDetail.validationOk') : t('intro.modDetail.validationWarn') }}
          </span>
          <a class="btn" :href="exportUrl" download>{{ t('intro.modDetail.exportZip') }}</a>
          <button type="button" class="btn" @click="doPushOne">{{ t('intro.modDetail.pushXcagi') }}</button>
          <button type="button" class="btn btn-danger" @click="confirmDelete">{{ t('intro.modDetail.delete') }}</button>
        </div>
      </header>

      <div v-if="detail.warnings?.length" class="warn-box">
        <div class="label">{{ t('intro.modDetail.warningsTitle') }}</div>
        <ul>
          <li v-for="(w, i) in detail.warnings" :key="i">{{ w }}</li>
        </ul>
      </div>

      <nav class="tabs" :aria-label="t('intro.modDetail.tabsAria')">
        <button type="button" :class="['tab', tab === 'overview' && 'tab-on']" @click="tab = 'overview'">
          {{ t('intro.modDetail.tabOverview') }}
        </button>
        <button type="button" :class="['tab', tab === 'edit' && 'tab-on']" @click="tab = 'edit'">
          {{ t('intro.modDetail.tabEdit') }}
        </button>
        <button type="button" :class="['tab', tab === 'json' && 'tab-on']" @click="tab = 'json'">
          {{ t('intro.modDetail.tabJson') }}
        </button>
        <button type="button" :class="['tab', tab === 'files' && 'tab-on']" @click="tab = 'files'">
          {{ t('intro.modDetail.tabFiles') }}
        </button>
      </nav>

      <p v-show="tab === 'overview'" class="tab-hint">{{ t('intro.modDetail.overviewHint') }}</p>

      <div v-show="tab === 'overview'" class="stack">
        <section class="card">
          <h2 class="card-title">{{ t('intro.modDetail.cardApiTitle') }}</h2>
          <dl class="kv">
            <dt>backend.entry</dt>
            <dd class="mono">{{ be.entry || t('intro.modDetail.em') }}</dd>
            <dt>backend.init</dt>
            <dd class="mono">{{ be.init || t('intro.modDetail.em') }}</dd>
            <dt>comms.exports</dt>
            <dd>{{ commsExports.length ? commsExports.join(', ') : t('intro.modDetail.em') }}</dd>
          </dl>
          <div v-if="hooksList.length" class="sub-block">
            <div class="sub-label">{{ t('intro.modDetail.subHooks') }}</div>
            <ul class="tight-list">
              <li v-for="([ev, target], i) in hooksList" :key="i">
                <code class="mono">{{ ev }}</code>
                <span class="arrow">→</span>
                <code class="mono">{{ target }}</code>
              </li>
            </ul>
          </div>
          <div class="sub-block">
            <div class="sub-label">{{ t('intro.modDetail.routesPrefix') }}{{ bpFile || t('intro.modDetail.em') }}</div>
            <div v-if="bpLoading" class="muted small">{{ t('intro.modDetail.bpScanning') }}</div>
            <table v-else-if="bpRoutes.length" class="bp-table compact">
              <thead>
                <tr>
                  <th>{{ t('intro.modDetail.thFunction') }}</th>
                  <th>{{ t('intro.modDetail.thPath') }}</th>
                  <th>{{ t('intro.modDetail.thMethod') }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(r, i) in bpRoutes" :key="locale + '-' + i + '-' + r.function">
                  <td class="bp-fn" :title="r.function">{{ bpFnLabel(r.function) }}</td>
                  <td class="mono">{{ r.path }}</td>
                  <td>{{ (r.methods || []).join(', ') }}</td>
                </tr>
              </tbody>
            </table>
            <p v-else class="muted small">{{ bpHint || t('intro.modDetail.bpNoRoutes') }}</p>
          </div>
        </section>

        <section class="card">
          <h2 class="card-title">{{ t('intro.modDetail.cardConfigTitle') }}</h2>
          <p class="hint">
            {{ t('intro.modDetail.configHintBefore') }}<span class="mono">config</span>{{ t('intro.modDetail.configHintAfter') }}
          </p>
          <pre v-if="configJsonRedacted.trim()" class="config-pre mono">{{ configJsonRedacted }}</pre>
          <p v-else class="muted empty-hint">{{ t('intro.modDetail.noConfig') }}</p>
        </section>

        <section class="card">
          <h2 class="card-title">{{ t('intro.modDetail.cardWorkflowTitle') }}</h2>
          <ul v-if="employees.length" class="emp-list">
            <li v-for="(emp, i) in employees" :key="i" class="emp-item">
              <div class="emp-head">
                <span class="emp-id mono">{{ emp.id || t('intro.modDetail.em') }}</span>
                <span class="emp-label">{{ emp.label || '' }}</span>
              </div>
              <p v-if="emp.panel_title" class="emp-title">{{ emp.panel_title }}</p>
              <p v-if="emp.panel_summary" class="emp-sum">{{ emp.panel_summary }}</p>
              <p v-if="emp.phone_agent_base_path" class="muted small mono">phone_agent: {{ emp.phone_agent_base_path }}</p>
            </li>
          </ul>
          <p v-else class="muted empty-hint">{{ t('intro.modDetail.notConfigured') }}</p>
        </section>

        <section class="card">
          <h2 class="card-title">{{ t('intro.modDetail.cardMenuTitle') }}</h2>
          <dl class="kv">
            <dt>routes</dt>
            <dd class="mono">{{ fe.routes || t('intro.modDetail.em') }}</dd>
          </dl>
          <table v-if="menuRows.length" class="bp-table compact">
            <thead>
              <tr>
                <th>{{ t('intro.modDetail.thMenuId') }}</th>
                <th>{{ t('intro.modDetail.thMenuLabel') }}</th>
                <th>{{ t('intro.modDetail.thMenuPath') }}</th>
                <th>{{ t('intro.modDetail.thMenuIcon') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(m, i) in menuRows" :key="i">
                <td class="mono">{{ m.id }}</td>
                <td>{{ m.label }}</td>
                <td class="mono">{{ m.path }}</td>
                <td class="mono muted">{{ m.icon || t('intro.modDetail.em') }}</td>
              </tr>
            </tbody>
          </table>
          <p v-else class="muted empty-hint">{{ t('intro.modDetail.noMenu') }}</p>
        </section>

        <section class="card">
          <h2 class="card-title">{{ t('intro.modDetail.cardFhdTokensTitle') }}</h2>
          <p class="hint">{{ t('intro.modDetail.fhdTokensHint') }}</p>
          <div class="fhd-tokens-grid">
            <div>
              <div class="sub-label">{{ t('intro.modDetail.fhdColManifest') }}</div>
              <dl class="kv kv-tight">
                <dt>{{ t('intro.modDetail.fhdReadTokenLabel') }}</dt>
                <dd>{{ tokenPreview(cfg.fhd_db_read_token) }}</dd>
                <dt>{{ t('intro.modDetail.fhdWriteTokenLabel') }}</dt>
                <dd>{{ tokenPreview(cfg.fhd_db_write_token) }}</dd>
              </dl>
            </div>
            <div>
              <div class="sub-label">{{ t('intro.modDetail.fhdColHost') }}</div>
              <template v-if="fhdHostTokens && fhdHostTokens.ok && fhdHostTokens.data && typeof fhdHostTokens.data === 'object'">
                <ul class="tight-list">
                  <li>
                    {{
                      fhdHostTokens.data.read_token_configured
                        ? t('intro.modDetail.fhdHostReadYes')
                        : t('intro.modDetail.fhdHostReadNo')
                    }}
                  </li>
                  <li>
                    {{
                      fhdHostTokens.data.write_token_configured
                        ? t('intro.modDetail.fhdHostWriteYes')
                        : t('intro.modDetail.fhdHostWriteNo')
                    }}
                  </li>
                </ul>
                <p v-if="fhdHostTokens.url" class="muted small mono">{{ fhdHostTokens.url }}</p>
              </template>
              <p v-else class="muted small">
                {{ fhdHostErr || fhdHostTokens?.error || t('intro.modDetail.fhdHostFetchErr') }}
              </p>
            </div>
          </div>
        </section>

        <section class="card">
          <h2 class="card-title">{{ t('intro.modDetail.cardWalletTitle') }}</h2>
          <p class="hint">{{ t('intro.modDetail.walletHint') }}</p>
          <dl class="kv kv-tight">
            <dt>{{ t('intro.modDetail.walletSecretLabel') }}</dt>
            <dd>{{ tokenPreview(cfg.wallet_secret) }}</dd>
          </dl>
        </section>
      </div>

      <div v-show="tab === 'edit'" class="panel">
        <h2 class="panel-heading">{{ t('intro.modDetail.editBasicTitle') }}</h2>
        <p class="hint">{{ t('intro.modDetail.editHint') }}</p>
        <div class="grid2">
          <div>
            <label class="label">{{ t('intro.modDetail.labelId') }}</label>
            <input class="input" :value="id" disabled />
          </div>
          <div>
            <label class="label">{{ t('intro.modDetail.labelVersion') }}</label>
            <input v-model="form.version" class="input" />
          </div>
          <div class="full">
            <label class="label">{{ t('intro.modDetail.labelName') }}</label>
            <input v-model="form.name" class="input" />
          </div>
          <div class="full">
            <label class="label">{{ t('intro.modDetail.labelAuthor') }}</label>
            <input v-model="form.author" class="input" />
          </div>
          <div class="full">
            <label class="label">{{ t('intro.modDetail.labelDescription') }}</label>
            <input v-model="form.description" class="input" />
          </div>
          <div>
            <label class="label">
              <input v-model="form.primary" type="checkbox" />
              {{ t('intro.modDetail.labelPrimary') }}
            </label>
          </div>
          <div class="full token-block">
            <h3 class="token-block-title">{{ t('intro.modDetail.cardFhdTokensTitle') }}</h3>
            <p class="hint">{{ t('intro.modDetail.fhdTokensHint') }}</p>
            <label class="label">{{ t('intro.modDetail.fhdReadTokenLabel') }}</label>
            <input
              v-model="form.fhd_db_read_token"
              type="password"
              class="input"
              autocomplete="new-password"
              spellcheck="false"
            />
            <label class="label" style="margin-top: 0.75rem">{{ t('intro.modDetail.fhdWriteTokenLabel') }}</label>
            <input
              v-model="form.fhd_db_write_token"
              type="password"
              class="input"
              autocomplete="new-password"
              spellcheck="false"
            />
          </div>
          <div class="full token-block">
            <h3 class="token-block-title">{{ t('intro.modDetail.cardWalletTitle') }}</h3>
            <p class="hint">{{ t('intro.modDetail.walletHint') }}</p>
            <label class="label">{{ t('intro.modDetail.walletSecretLabel') }}</label>
            <input
              v-model="form.wallet_secret"
              type="password"
              class="input"
              autocomplete="new-password"
              spellcheck="false"
            />
          </div>
        </div>
        <button type="button" class="btn btn-primary" style="margin-top: 1rem" @click="saveFromForm">
          {{ t('intro.modDetail.btnSaveManifest') }}
        </button>
      </div>

      <div v-show="tab === 'json'" class="panel">
        <label class="label">{{ t('intro.modDetail.jsonLabel') }}</label>
        <textarea v-model="jsonText" class="textarea" spellcheck="false"></textarea>
        <button type="button" class="btn btn-primary" style="margin-top: 0.75rem" @click="saveJson">
          {{ t('intro.modDetail.btnSaveJson') }}
        </button>
      </div>

      <div v-show="tab === 'files'" class="panel">
        <p class="muted small">{{ t('intro.modDetail.filesHint') }}</p>
        <ul class="file-list mono">
          <li v-for="f in detail.files" :key="f">
            <button v-if="isEditableFile(f)" type="button" class="file-link" @click="openFileEditor(f)">{{ f }}</button>
            <span v-else class="file-static">{{ f }}</span>
          </li>
        </ul>
        <p v-if="!detail.files?.length" class="muted">{{ t('intro.modDetail.noFiles') }}</p>
      </div>
    </template>

    <div v-if="fileModal.open" class="modal-overlay" @click.self="closeFileEditor">
      <div class="modal modal-wide">
        <h2 class="modal-title mono">{{ fileModal.path }}</h2>
        <div v-if="fileModal.err" class="flash flash-err">{{ fileModal.err }}</div>
        <textarea
          v-model="fileModal.content"
          class="textarea textarea-tall"
          spellcheck="false"
          :disabled="fileModal.loading"
        />
        <div class="modal-actions">
          <button type="button" class="btn btn-ghost" @click="closeFileEditor">{{ t('intro.modDetail.modalClose') }}</button>
          <button
            type="button"
            class="btn btn-primary"
            :disabled="fileModal.loading || fileModal.saving"
            @click="saveFileEditor"
          >
            {{ fileModal.saving ? t('intro.modDetail.modalSaving') : t('intro.modDetail.modalSave') }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { api } from '../api'
import { blueprintFunctionLabel } from '../utils/blueprintLabels'

const { t, locale } = useI18n()

function bpFnLabel(fn) {
  return blueprintFunctionLabel(fn, locale.value)
}

const props = defineProps({ id: { type: String, required: true } })

const route = useRoute()
const router = useRouter()
const id = computed(() => decodeURIComponent(props.id || route.params.id))

const loading = ref(true)
const err = ref('')
const msg = ref('')
const detail = ref(null)
const tab = ref('overview')
const jsonText = ref('')

const bpRoutes = ref([])
const bpFile = ref('')
const bpHint = ref('')
const bpLoading = ref(false)

/** 代理拉取 FHD GET /api/fhd/db-tokens/status 的返回体（或 null） */
const fhdHostTokens = ref(null)
const fhdHostErr = ref('')

const form = ref({
  name: '',
  version: '',
  author: '',
  description: '',
  primary: false,
  fhd_db_read_token: '',
  fhd_db_write_token: '',
  wallet_secret: '',
})

const exportUrl = computed(() => api.exportUrl(id.value))

const m = computed(() => (detail.value?.manifest && typeof detail.value.manifest === 'object' ? detail.value.manifest : {}))

const be = computed(() => (typeof m.value.backend === 'object' && m.value.backend ? m.value.backend : {}))
const fe = computed(() => (typeof m.value.frontend === 'object' && m.value.frontend ? m.value.frontend : {}))

const commsExports = computed(() => {
  const c = m.value.comms
  if (!c || typeof c !== 'object') return []
  const ex = c.exports
  return Array.isArray(ex) ? ex.map(String) : []
})

const hooksList = computed(() => {
  const h = m.value.hooks
  if (!h || typeof h !== 'object') return []
  return Object.entries(h).map(([k, v]) => [k, String(v)])
})

const configJson = computed(() => {
  const c = m.value.config
  if (c === undefined || c === null) return ''
  try {
    return JSON.stringify(c, null, 2)
  } catch {
    return String(c)
  }
})

/** 概览区展示用：隐藏 FHD 令牌明文 */
const configJsonRedacted = computed(() => {
  const c = m.value.config
  if (c === undefined || c === null) return ''
  try {
    const o = JSON.parse(JSON.stringify(c))
    if (o && typeof o === 'object') {
      for (const k of ['fhd_db_read_token', 'fhd_db_write_token', 'wallet_secret']) {
        if (o[k] != null && String(o[k]).trim() !== '') o[k] = '***'
      }
    }
    return JSON.stringify(o, null, 2)
  } catch {
    return String(c)
  }
})

const cfg = computed(() => {
  const c = m.value.config
  return c && typeof c === 'object' ? c : {}
})

function tokenPreview(val) {
  const v = val != null && String(val).trim() !== '' ? String(val) : ''
  if (!v) return t('intro.modDetail.fhdTokenUnset')
  return t('intro.modDetail.fhdTokenSet', { n: v.length })
}

const employees = computed(() => {
  const w = m.value.workflow_employees
  return Array.isArray(w) ? w : []
})

const menuRows = computed(() => {
  const menu = fe.value.menu
  if (!Array.isArray(menu)) return []
  return menu.filter((x) => x && typeof x === 'object')
})

const EDITABLE_RE = /\.(py|json|vue|ts|js|mjs|cjs|css|md|txt|html)$/i

function isEditableFile(f) {
  return EDITABLE_RE.test(String(f || ''))
}

const fileModal = ref({
  open: false,
  path: '',
  content: '',
  loading: false,
  saving: false,
  err: '',
})

async function openFileEditor(relPath) {
  fileModal.value = {
    open: true,
    path: relPath,
    content: '',
    loading: true,
    saving: false,
    err: '',
  }
  try {
    const res = await api.getModFile(id.value, relPath)
    fileModal.value.content = res.content ?? ''
  } catch (e) {
    fileModal.value.err = e.message || String(e)
  } finally {
    fileModal.value.loading = false
  }
}

function closeFileEditor() {
  fileModal.value.open = false
}

async function saveFileEditor() {
  fileModal.value.saving = true
  fileModal.value.err = ''
  try {
    const res = await api.putModFile(id.value, fileModal.value.path, fileModal.value.content)
    if (res.manifest_warnings?.length) {
      msg.value = t('intro.modDetail.msgSavedFileWarn', { hint: res.manifest_warnings[0] })
    } else {
      msg.value = t('intro.modDetail.msgFileSaved')
    }
    await load()
    closeFileEditor()
  } catch (e) {
    fileModal.value.err = e.message || String(e)
  } finally {
    fileModal.value.saving = false
  }
}

function syncFormFromManifest(manifest) {
  const c = manifest.config && typeof manifest.config === 'object' ? manifest.config : {}
  form.value = {
    name: manifest.name || '',
    version: manifest.version || '',
    author: manifest.author || '',
    description: manifest.description || '',
    primary: !!manifest.primary,
    fhd_db_read_token: c.fhd_db_read_token != null ? String(c.fhd_db_read_token) : '',
    fhd_db_write_token: c.fhd_db_write_token != null ? String(c.fhd_db_write_token) : '',
    wallet_secret: c.wallet_secret != null ? String(c.wallet_secret) : '',
  }
}

async function loadBlueprintRoutes() {
  bpLoading.value = true
  bpHint.value = ''
  try {
    const r = await api.modBlueprintRoutes(id.value)
    bpFile.value = r.file || ''
    bpRoutes.value = r.routes || []
    bpHint.value = r.hint || ''
  } catch (e) {
    bpHint.value = e.message || String(e)
    bpFile.value = ''
    bpRoutes.value = []
  } finally {
    bpLoading.value = false
  }
}

async function loadFhdHostTokenStatus() {
  fhdHostErr.value = ''
  fhdHostTokens.value = null
  try {
    fhdHostTokens.value = await api.fhdDbTokensStatus()
  } catch (e) {
    fhdHostErr.value = `${t('intro.modDetail.fhdHostFetchErr')}${e.message ? ` (${e.message})` : ''}`
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
    await loadBlueprintRoutes()
    await loadFhdHostTokenStatus()
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
    err.value = t('intro.modDetail.jsonParseErr', { msg: e.message })
    return
  }
  try {
    const res = await api.putManifest(id.value, parsed)
    msg.value = res.warnings?.length ? t('intro.modDetail.msgSavedWithWarnings') : t('intro.modDetail.msgSaved')
    await load()
  } catch (e) {
    err.value = e.message || String(e)
  }
}

async function saveFromForm() {
  let manifest
  try {
    manifest = JSON.parse(jsonText.value)
  } catch {
    manifest = JSON.parse(JSON.stringify(detail.value.manifest))
  }
  manifest.id = id.value
  manifest.name = form.value.name
  manifest.version = form.value.version
  manifest.author = form.value.author
  manifest.description = form.value.description
  manifest.primary = form.value.primary
  const prevCfg =
    manifest.config && typeof manifest.config === 'object' ? { ...manifest.config } : {}
  manifest.config = {
    ...prevCfg,
    fhd_db_read_token: String(form.value.fhd_db_read_token ?? '').trim(),
    fhd_db_write_token: String(form.value.fhd_db_write_token ?? '').trim(),
    wallet_secret: String(form.value.wallet_secret ?? '').trim(),
  }
  jsonText.value = JSON.stringify(manifest, null, 2)
  try {
    await api.putManifest(id.value, manifest)
    msg.value = t('intro.modDetail.msgSaved')
    await load()
  } catch (e) {
    err.value = e.message || String(e)
  }
}

async function doPushOne() {
  try {
    const res = await api.push([id.value])
    msg.value = t('intro.modDetail.msgDeployed', { list: (res.deployed || []).join(', ') })
  } catch (e) {
    err.value = e.message || String(e)
  }
}

async function confirmDelete() {
  if (!confirm(t('intro.modDetail.confirmDelete', { id: id.value }))) return
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
.detail-page {
  max-width: 40rem;
  margin: 0 auto;
  padding-bottom: 2rem;
}
.back-row {
  margin-bottom: 1.25rem;
}
.back {
  color: var(--muted);
  font-size: 0.875rem;
}
.head {
  margin-bottom: 1.5rem;
  padding-bottom: 1.25rem;
  border-bottom: 1px solid var(--border);
}
.head h1 {
  margin: 0;
  font-size: 1.35rem;
  font-weight: 600;
  letter-spacing: -0.02em;
}
.desc {
  margin: 0.5rem 0 0;
  color: var(--muted);
  font-size: 0.875rem;
  line-height: 1.5;
}
.meta {
  margin: 0.25rem 0 0;
  color: var(--muted);
  font-size: 0.8125rem;
}
.head-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
  margin-top: 1rem;
}
.pill {
  font-size: 0.65rem;
  padding: 0.2rem 0.45rem;
  border-radius: 999px;
  font-weight: 600;
}
.pill-ok {
  background: rgba(74, 222, 128, 0.12);
  color: #86efac;
}
.pill-warn {
  background: rgba(251, 191, 36, 0.1);
  color: #fde68a;
}
.warn-box {
  background: rgba(251, 191, 36, 0.06);
  border-radius: 10px;
  padding: 0.75rem 1rem;
  margin-bottom: 1.25rem;
  border: 1px solid rgba(251, 191, 36, 0.2);
}
.warn-box ul {
  margin: 0.35rem 0 0 1rem;
  color: var(--warn);
  font-size: 0.8125rem;
}
.tabs {
  display: flex;
  gap: 0.1rem;
  margin-bottom: 0.5rem;
  border-bottom: 1px solid var(--border);
}
.tab-hint {
  margin: 0 0 1.1rem;
  font-size: 0.8125rem;
  color: var(--muted);
  line-height: 1.55;
  max-width: 42rem;
}
.tab {
  padding: 0.5rem 0.85rem;
  margin-bottom: -1px;
  border: none;
  border-bottom: 2px solid transparent;
  background: none;
  color: var(--muted);
  cursor: pointer;
  font-family: var(--font-sans);
  font-size: 0.875rem;
}
.tab:hover {
  color: var(--text);
}
.tab-on {
  color: var(--accent);
  border-bottom-color: var(--accent);
  font-weight: 600;
}
.stack {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}
.card {
  background: var(--bg-elevated);
  border-radius: 12px;
  padding: 1.1rem 1.2rem;
  border: 1px solid transparent;
}
.card-title {
  margin: 0 0 0.75rem;
  font-size: 0.9375rem;
  font-weight: 600;
  color: var(--text);
}
.hint {
  margin: 0 0 0.75rem;
  font-size: 0.75rem;
  color: var(--muted);
  line-height: 1.45;
}
.token-block {
  margin-top: 0.5rem;
  padding-top: 1rem;
  border-top: 1px solid var(--border);
}
.token-block-title {
  margin: 0 0 0.35rem;
  font-size: 0.9375rem;
  font-weight: 600;
  color: var(--text);
}
.empty-hint {
  margin: 0;
  font-size: 0.8125rem;
}
.kv {
  margin: 0;
  display: grid;
  grid-template-columns: 7.5rem 1fr;
  gap: 0.4rem 0.75rem;
  font-size: 0.8125rem;
  align-items: baseline;
}
.kv dt {
  color: var(--muted);
  font-weight: 400;
}
.kv dd {
  margin: 0;
  word-break: break-all;
}
.kv-tight {
  margin-top: 0.35rem;
}
.fhd-tokens-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem 1.25rem;
  margin-top: 0.35rem;
}
@media (max-width: 640px) {
  .fhd-tokens-grid {
    grid-template-columns: 1fr;
  }
}
.sub-block {
  margin-top: 1rem;
  padding-top: 1rem;
  border-top: 1px solid var(--border);
}
.sub-label {
  font-size: 0.75rem;
  color: var(--muted);
  margin-bottom: 0.4rem;
}
.tight-list {
  margin: 0;
  padding-left: 1rem;
  font-size: 0.8125rem;
  line-height: 1.5;
}
.tight-list li {
  margin-bottom: 0.2rem;
}
.arrow {
  margin: 0 0.25rem;
  color: var(--muted);
  opacity: 0.7;
}
.config-pre {
  margin: 0;
  padding: 0.75rem;
  background: var(--bg);
  border-radius: 8px;
  font-size: 0.75rem;
  max-height: 11rem;
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-all;
  border: 1px solid var(--border);
}
.emp-list {
  list-style: none;
  margin: 0;
  padding: 0;
}
.emp-item {
  padding: 0.85rem 0;
  border-bottom: 1px solid var(--border);
}
.emp-item:last-child {
  border-bottom: none;
  padding-bottom: 0;
}
.emp-item:first-child {
  padding-top: 0;
}
.emp-head {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem 0.6rem;
  align-items: baseline;
}
.emp-id {
  font-weight: 600;
  font-size: 0.8125rem;
  color: var(--accent);
}
.emp-label {
  font-size: 0.875rem;
  color: var(--text);
}
.emp-title {
  margin: 0.35rem 0 0;
  font-size: 0.8125rem;
  font-weight: 500;
}
.emp-sum {
  margin: 0.25rem 0 0;
  font-size: 0.75rem;
  color: var(--muted);
  line-height: 1.45;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.panel {
  background: var(--bg-elevated);
  border-radius: 12px;
  padding: 1.15rem 1.2rem;
}
.panel-heading {
  margin: 0 0 0.35rem;
  font-size: 1rem;
  font-weight: 600;
}
.grid2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.65rem 1rem;
}
.full {
  grid-column: 1 / -1;
}
.file-list {
  margin: 0;
  padding-left: 1.1rem;
  font-size: 0.8125rem;
  color: var(--muted);
  max-height: 22rem;
  overflow: auto;
  line-height: 1.55;
}
.muted {
  color: var(--muted);
}
.small {
  font-size: 0.8125rem;
  margin-bottom: 0.5rem;
}
.file-link {
  background: none;
  border: none;
  padding: 0;
  color: var(--accent);
  cursor: pointer;
  font-family: var(--font-mono);
  font-size: inherit;
  text-align: left;
  text-decoration: none;
}
.file-link:hover {
  text-decoration: underline;
}
.file-static {
  color: var(--muted);
}
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.65);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 1rem;
}
.modal-wide {
  max-width: min(920px, 100%);
  width: 100%;
}
.modal-title {
  margin: 0 0 0.75rem;
  font-size: 0.875rem;
  word-break: break-all;
}
.textarea-tall {
  min-height: 360px;
  font-family: var(--font-mono);
  font-size: 0.8125rem;
}
.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
  margin-top: 0.75rem;
}
.btn-ghost {
  background: transparent;
}
.bp-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.75rem;
  margin-top: 0.25rem;
}
.bp-table.compact th,
.bp-table.compact td {
  padding: 0.45rem 0.35rem;
}
.bp-table th {
  text-align: left;
  font-weight: 500;
  color: var(--muted);
  border-bottom: 1px solid var(--border);
}
.bp-table td {
  border-bottom: 1px solid var(--border);
}
.bp-fn {
  font-size: 0.8125rem;
  line-height: 1.35;
  color: var(--text);
  max-width: 14rem;
  word-break: break-word;
}
.bp-table tbody tr:last-child td {
  border-bottom: none;
}
.bp-table th,
.bp-table td {
  border-left: none;
  border-right: none;
  border-top: none;
}

@media (max-width: 520px) {
  .grid2 {
    grid-template-columns: 1fr;
  }
}
</style>
