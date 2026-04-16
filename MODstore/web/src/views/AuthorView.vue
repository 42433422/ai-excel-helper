<template>
  <div class="author">
    <h1>{{ t('intro.author.title') }}</h1>
    <p class="intro-callout">{{ introPage }}</p>
    <p class="sub">{{ t('intro.author.subHint') }}</p>

    <div v-if="flash" :class="['flash', flashOk ? 'flash-ok' : 'flash-err']">{{ flash }}</div>

    <div class="row-actions">
      <button type="button" class="btn" :disabled="loading" @click="loadBundled">{{ t('intro.author.btnRefresh') }}</button>
      <button type="button" class="btn btn-primary" :disabled="loadingHost" @click="loadWithHost">
        {{ loadingHost ? t('intro.author.btnMergeLoading') : t('intro.author.btnMerge') }}
      </button>
    </div>

    <div v-if="loading" class="muted">{{ t('intro.author.loading') }}</div>

    <template v-else-if="surface">
      <section class="panel" v-if="surface.bundled?.manifest_contract">
        <h2>{{ t('intro.author.manifestTitle') }}</h2>
        <p class="section-intro">{{ manifestSectionIntro }}</p>
        <ul class="field-list">
          <li v-for="(f, i) in surface.bundled.manifest_contract.fields" :key="i">
            <code class="mono">{{ f.key }}</code>
            <span class="pill">{{ fieldKindZh(f.kind) }}</span>
            <span v-if="f.required" class="pill pill-req">{{ t('intro.author.requiredPill') }}</span>
            <p class="field-note">{{ f.note }}</p>
            <p v-if="f.example" class="muted small mono">{{ t('intro.author.examplePrefix') }} {{ f.example }}</p>
          </li>
        </ul>
      </section>

      <section class="panel" v-if="surface.bundled?.backend_blueprint_convention">
        <h2>{{ t('intro.author.blueprintTitle') }}</h2>
        <p class="section-intro">{{ blueprintSectionIntro }}</p>
        <p class="muted small mono">{{ surface.bundled.backend_blueprint_convention.register_signature }}</p>
        <ul>
          <li v-for="(p, i) in surface.bundled.backend_blueprint_convention.file_candidates" :key="i">
            <code class="mono">{{ p }}</code>
          </li>
        </ul>
      </section>

      <section class="panel" v-if="hostRoutes.length">
        <h2>{{ t('intro.author.openapiTitle') }}</h2>
        <p class="section-intro">{{ openapiSectionIntro }}</p>
        <p class="muted small">{{ t('intro.author.openapiCount', { n: hostRoutes.length }) }}</p>
        <div class="table-wrap">
          <table class="rtable">
            <thead>
              <tr>
                <th>{{ t('intro.author.thPath') }}</th>
                <th>{{ t('intro.author.thMethod') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(r, i) in hostRoutes" :key="i">
                <td class="mono">{{ r.path }}</td>
                <td>{{ (r.methods || []).join(', ') }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <section v-else-if="hostError" class="panel warn">
        <h2>{{ t('intro.author.hostOpenapiTitle') }}</h2>
        <p class="mono">{{ hostError }}</p>
      </section>

      <section class="panel muted" v-if="surface.bundled?.runtime_and_debug">
        <h2>{{ t('intro.author.runtimeTitle') }}</h2>
        <p class="section-intro">{{ runtimeSectionIntro }}</p>
        <pre class="mono pre">{{ runtimeDebugText }}</pre>
      </section>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { api } from '../api'
import { fieldKindZh } from '../i18n/fieldKind'

const { t } = useI18n()

const loading = ref(true)
const loadingHost = ref(false)
const surface = ref(null)
const hostError = ref('')
const flash = ref('')
const flashOk = ref(true)

const hostRoutes = computed(() => surface.value?.host_openapi?.routes || [])

const uiZh = computed(() => surface.value?.bundled?.ui_intro_zh || {})

const introPage = computed(() => uiZh.value.page || t('intro.author.fallbackPage'))
const manifestSectionIntro = computed(() => uiZh.value.manifest_section || t('intro.author.manifestSection'))
const blueprintSectionIntro = computed(() => uiZh.value.blueprint_section || t('intro.author.blueprintSection'))
const openapiSectionIntro = computed(() => uiZh.value.openapi_section || t('intro.author.openapiSection'))
const runtimeSectionIntro = computed(() => uiZh.value.runtime_section || t('intro.author.runtimeSection'))

const runtimeDebugText = computed(() => {
  const r = surface.value?.bundled?.runtime_and_debug
  if (!r) return ''
  try {
    return JSON.stringify(r, null, 2)
  } catch {
    return String(r)
  }
})

async function loadBundled() {
  loading.value = true
  hostError.value = ''
  flash.value = ''
  surface.value = null
  try {
    surface.value = await api.extensionSurface(false)
  } catch (e) {
    flash.value = e.message || String(e)
    flashOk.value = false
  } finally {
    loading.value = false
  }
}

async function loadWithHost() {
  loadingHost.value = true
  hostError.value = ''
  flash.value = ''
  try {
    surface.value = await api.extensionSurface(true)
    if (surface.value.host_openapi_error) {
      hostError.value = surface.value.host_openapi_error
      flash.value = t('intro.author.flashHostOpenapiFail')
      flashOk.value = false
    } else if (surface.value.host_openapi?.route_count != null) {
      flash.value = t('intro.author.flashMergedRoutes', { count: surface.value.host_openapi.route_count })
      flashOk.value = true
    }
  } catch (e) {
    flash.value = e.message || String(e)
    flashOk.value = false
  } finally {
    loadingHost.value = false
    loading.value = false
  }
}

onMounted(async () => {
  await loadBundled()
})
</script>

<style scoped>
.author h1 {
  margin: 0 0 0.35rem;
  font-size: 1.6rem;
}
.intro-callout {
  margin: 0 0 0.65rem;
  max-width: 72ch;
  line-height: 1.6;
  padding: 0.65rem 0.85rem;
  border-radius: 8px;
  border: 1px solid var(--border);
  background: var(--bg-elevated);
  color: var(--text);
  font-size: 0.95rem;
}
.section-intro {
  margin: 0 0 0.75rem;
  color: var(--muted);
  font-size: 0.9rem;
  line-height: 1.55;
  max-width: 72ch;
}
.sub {
  color: var(--muted);
  max-width: 72ch;
  line-height: 1.55;
  margin-bottom: 1rem;
}
.row-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-bottom: 1rem;
}
.panel {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 1rem 1.2rem;
  margin-bottom: 1rem;
}
.panel h2 {
  margin: 0 0 0.65rem;
  font-size: 1.05rem;
}
.field-list {
  margin: 0;
  padding-left: 0;
  list-style: none;
}
.field-list li {
  margin-bottom: 1rem;
  padding-bottom: 0.75rem;
  border-bottom: 1px solid var(--border);
}
.field-list li:last-child {
  border-bottom: none;
}
.field-note {
  margin: 0.35rem 0 0;
  color: var(--text);
  font-size: 0.9rem;
}
.pill {
  display: inline-block;
  margin-left: 0.35rem;
  font-size: 0.68rem;
  padding: 0.1rem 0.4rem;
  border-radius: 4px;
  background: var(--bg-elevated);
  color: var(--muted);
}
.pill-req {
  color: #fecaca;
  background: #450a0a;
}
.table-wrap {
  max-height: 420px;
  overflow: auto;
}
.rtable {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.82rem;
}
.rtable th,
.rtable td {
  border: 1px solid var(--border);
  padding: 0.35rem 0.5rem;
  text-align: left;
}
.rtable th {
  background: var(--bg-elevated);
}
.pre {
  font-size: 0.78rem;
  white-space: pre-wrap;
  word-break: break-all;
}
.warn {
  border-color: #92400e;
}
</style>
