<template>
  <div>
    <h1>调试与切换</h1>
    <p class="sub">{{ t('intro.debug.lead') }}</p>

    <div v-if="flash" :class="['flash', flashOk ? 'flash-ok' : 'flash-err']">{{ flash }}</div>

    <div class="panel block">
      <h2 class="h2">XCAGI 加载状态</h2>
      <p class="muted small">
        后端 URL 在「路径与同步」中配置。默认 http://127.0.0.1:5000；若 XCAGI 已由本仓库
        <span class="mono">backend.http_app</span> 托管，请改为 <span class="mono">http://127.0.0.1:8000</span>。
      </p>
      <div class="row">
        <button type="button" class="btn btn-primary" :disabled="statusLoading" @click="fetchStatus">
          {{ statusLoading ? '拉取中…' : '刷新状态' }}
        </button>
      </div>
      <pre v-if="statusJson" class="mono pre">{{ statusJson }}</pre>
      <p v-else-if="statusLoading" class="muted">加载中…</p>
    </div>

    <div class="panel block">
      <h2 class="h2">当前调试 Mod</h2>
      <label class="label">选择库中 Mod</label>
      <select v-model="selectedMod" class="input">
        <option value="">— 请选择 —</option>
        <option v-for="m in mods" :key="m.id" :value="m.id">
          {{ m.name || m.id }} ({{ m.id }})
        </option>
      </select>

      <label class="label" style="margin-top: 1rem">沙箱方式</label>
      <select v-model="sandboxMode" class="input">
        <option value="copy">复制（推荐，Windows 兼容）</option>
        <option value="symlink">符号链接（失败时自动回退为复制）</option>
      </select>

      <div class="row" style="margin-top: 1rem">
        <button type="button" class="btn btn-primary" :disabled="!selectedMod || busy" @click="doSandbox">
          生成独立 mods 目录
        </button>
        <button type="button" class="btn" :disabled="!selectedMod || busy" @click="doFocusPrimary">
          库内仅设其为 primary
        </button>
        <button type="button" class="btn" :disabled="!selectedMod || busy" @click="doPushOne">
          仅推送到 XCAGI/mods
        </button>
      </div>

      <div v-if="sandboxResult" class="sandbox-out">
        <div class="label">环境变量（CMD）</div>
        <code class="mono code-block">set {{ sandboxResult.xcagi_mods_root_env }}</code>
        <p class="muted small">{{ sandboxResult.hint }}</p>
        <div class="label">mods 根目录</div>
        <code class="mono code-block">{{ sandboxResult.mods_root }}</code>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { api } from '../api'

const { t } = useI18n()

const mods = ref([])
const selectedMod = ref('')
const sandboxMode = ref('copy')
const busy = ref(false)
const flash = ref('')
const flashOk = ref(true)
const statusLoading = ref(false)
const statusPayload = ref(null)
const sandboxResult = ref(null)

const statusJson = computed(() => {
  if (!statusPayload.value) return ''
  try {
    return JSON.stringify(statusPayload.value, null, 2)
  } catch {
    return String(statusPayload.value)
  }
})

function showFlash(msg, ok = true) {
  flash.value = msg
  flashOk.value = ok
  setTimeout(() => {
    flash.value = ''
  }, 6000)
}

async function loadMods() {
  try {
    const res = await api.listMods()
    const rows = res && typeof res === 'object' ? res.data : null
    mods.value = Array.isArray(rows) ? rows : []
  } catch (e) {
    showFlash(e.message || String(e), false)
  }
}

async function fetchStatus() {
  statusLoading.value = true
  statusPayload.value = null
  try {
    statusPayload.value = await api.xcagiLoadingStatus()
  } catch (e) {
    statusPayload.value = { error: e.message || String(e) }
    showFlash(e.message || String(e), false)
  } finally {
    statusLoading.value = false
  }
}

async function doSandbox() {
  if (!selectedMod.value) return
  busy.value = true
  sandboxResult.value = null
  try {
    const res = await api.debugSandbox(selectedMod.value, sandboxMode.value)
    sandboxResult.value = res
    showFlash('已生成沙箱目录', true)
  } catch (e) {
    showFlash(e.message || String(e), false)
  } finally {
    busy.value = false
  }
}

async function doFocusPrimary() {
  if (!selectedMod.value) return
  busy.value = true
  try {
    await api.debugFocusPrimary(selectedMod.value)
    showFlash('已更新各 Mod 的 manifest.primary（仅库内，未自动推送）', true)
  } catch (e) {
    showFlash(e.message || String(e), false)
  } finally {
    busy.value = false
  }
}

async function doPushOne() {
  if (!selectedMod.value) return
  busy.value = true
  try {
    const res = await api.push([selectedMod.value])
    showFlash('已部署: ' + (res.deployed || []).join(', '), true)
  } catch (e) {
    showFlash(e.message || String(e), false)
  } finally {
    busy.value = false
  }
}

onMounted(async () => {
  await loadMods()
  await fetchStatus()
  try {
    const c = await api.getConfig()
    const st = c.state || {}
    if (st.focus_mod_id && !selectedMod.value) {
      selectedMod.value = st.focus_mod_id
    }
    if (st.last_sandbox_mods_root && st.last_sandbox_mod_id) {
      sandboxResult.value = {
        mods_root: st.last_sandbox_mods_root,
        mod_id: st.last_sandbox_mod_id,
        xcagi_mods_root_env: `XCAGI_MODS_ROOT=${st.last_sandbox_mods_root}`,
        hint: '上次生成的沙箱（重启 XCAGI 后生效）。可重新生成以换新会话目录。',
      }
    }
  } catch {
    /* ignore */
  }
})
</script>

<style scoped>
h1 {
  margin: 0 0 0.35rem;
}
.h2 {
  margin: 0 0 0.75rem;
  font-size: 1.05rem;
  font-weight: 600;
}
.sub {
  color: var(--muted);
  max-width: 72ch;
  margin-bottom: 1.25rem;
  line-height: 1.5;
}
.mono {
  font-family: var(--font-mono);
}
.block {
  margin-bottom: 1.25rem;
}
.panel {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 1.25rem;
  max-width: 800px;
}
.row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-top: 0.75rem;
}
.pre {
  margin-top: 0.75rem;
  padding: 0.75rem;
  background: var(--bg);
  border-radius: 8px;
  font-size: 0.78rem;
  overflow: auto;
  max-height: 320px;
  white-space: pre-wrap;
  word-break: break-all;
}
.small {
  font-size: 0.82rem;
  margin: 0.35rem 0;
}
.sandbox-out {
  margin-top: 1rem;
  padding-top: 1rem;
  border-top: 1px solid var(--border);
}
.code-block {
  display: block;
  padding: 0.5rem 0.65rem;
  background: var(--bg);
  border-radius: 6px;
  font-size: 0.8rem;
  margin: 0.35rem 0 0.75rem;
  word-break: break-all;
}
select.input {
  cursor: pointer;
}
</style>
