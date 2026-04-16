<template>
  <div>
    <h1>路径与同步</h1>
    <p class="sub">{{ t('intro.settings.lead') }}</p>

    <div v-if="flash" :class="['flash', flashOk ? 'flash-ok' : 'flash-err']">{{ flash }}</div>

    <div class="panel">
      <label class="label">库根目录（library）</label>
      <input v-model="library_root" class="input" placeholder="默认：项目内 library/" />

      <label class="label" style="margin-top: 1rem">XCAGI 项目根目录</label>
      <input v-model="xcagi_root" class="input" placeholder="默认：与仓库同级的 XCAGI/" />

      <label class="label" style="margin-top: 1rem">XCAGI / FHD 后端 URL（loading-status 代理）</label>
      <input
        v-model="xcagi_backend_url"
        class="input"
        placeholder="例：http://127.0.0.1:5000（XCAGI）或 http://127.0.0.1:8000（本仓库 FHD http_app）"
      />

      <div class="resolved" v-if="effective">
        <div><span class="muted">当前解析 · 库：</span> {{ effective.library_root }}</div>
        <div><span class="muted">当前解析 · XCAGI：</span> {{ effective.xcagi_root || '（未检测到）' }}</div>
        <div><span class="muted">当前解析 · 后端 URL：</span> {{ effective.xcagi_backend_url || '（默认 5000）' }}</div>
        <div class="muted small">XCAGI mods 就绪: {{ effective.xcagi_ok ? '是' : '否' }}</div>
      </div>

      <label class="label" style="margin-top: 1rem">FHD 壳层 JSON 输出路径（留空=默认）</label>
      <input
        v-model="fhd_shell_output"
        class="input"
        placeholder="默认：<FHD>/backend/shell/fhd_shell_mods.json"
      />

      <div class="row">
        <button type="button" class="btn btn-primary" @click="save">保存配置</button>
        <button type="button" class="btn" @click="reload">重新读取</button>
        <button type="button" class="btn" :disabled="testing" @click="testXcagi">
          {{ testing ? '测试中…' : '测试后端连接' }}
        </button>
        <button type="button" class="btn" :disabled="exporting" @click="exportFhdShell">
          {{ exporting ? '导出中…' : '导出 FHD 壳层 /api/mods JSON' }}
        </button>
      </div>

      <pre v-if="testResult" class="test-pre mono">{{ testResult }}</pre>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { api } from '../api'

const { t } = useI18n()

const library_root = ref('')
const xcagi_root = ref('')
const xcagi_backend_url = ref('')
const effective = ref(null)
const flash = ref('')
const flashOk = ref(true)
const testing = ref(false)
const testResult = ref('')
const fhd_shell_output = ref('')
const exporting = ref(false)

async function reload() {
  const c = await api.getConfig()
  library_root.value = c.saved_library_root || ''
  xcagi_root.value = c.saved_xcagi_root || ''
  xcagi_backend_url.value = c.saved_xcagi_backend_url || ''
  effective.value = c
}

async function exportFhdShell() {
  exporting.value = true
  flash.value = ''
  try {
    const res = await api.exportFhdShellMods(fhd_shell_output.value.trim())
    flash.value = `已导出 ${res.count} 条 → ${res.path}`
    flashOk.value = true
  } catch (e) {
    flash.value = e.message || String(e)
    flashOk.value = false
  } finally {
    exporting.value = false
  }
}

async function testXcagi() {
  testing.value = true
  testResult.value = ''
  try {
    const raw = await api.xcagiLoadingStatus()
    testResult.value = JSON.stringify(raw, null, 2)
  } catch (e) {
    testResult.value = e.message || String(e)
  } finally {
    testing.value = false
  }
}

async function save() {
  flash.value = ''
  try {
    await api.putConfig({
      library_root: library_root.value,
      xcagi_root: xcagi_root.value,
      xcagi_backend_url: xcagi_backend_url.value,
    })
    flash.value = '已保存'
    flashOk.value = true
    await reload()
  } catch (e) {
    flash.value = e.message || String(e)
    flashOk.value = false
  }
}

onMounted(reload)
</script>

<style scoped>
h1 {
  margin: 0 0 0.35rem;
}
.sub {
  color: var(--muted);
  max-width: 56ch;
  margin-bottom: 1.25rem;
}
.panel {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 1.25rem;
  max-width: 640px;
}
.resolved {
  margin: 1rem 0;
  padding: 0.75rem;
  background: var(--bg);
  border-radius: 8px;
  font-size: 0.88rem;
  line-height: 1.5;
}
.small {
  font-size: 0.8rem;
  margin-top: 0.35rem;
}
.row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-top: 1rem;
}
.test-pre {
  margin-top: 1rem;
  padding: 0.75rem;
  background: var(--bg);
  border-radius: 8px;
  font-size: 0.78rem;
  overflow: auto;
  max-height: 240px;
  white-space: pre-wrap;
  word-break: break-all;
}
</style>
