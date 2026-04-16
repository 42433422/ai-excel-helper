<template>
  <div>
    <h1>路径与同步</h1>
    <p class="sub">
      库目录存放所有 Mod 源；XCAGI 根目录用于推送到
      <span class="mono">mods/</span>。留空则使用项目默认路径。
    </p>

    <div v-if="flash" :class="['flash', flashOk ? 'flash-ok' : 'flash-err']">{{ flash }}</div>

    <div class="panel">
      <label class="label">库根目录（library）</label>
      <input v-model="library_root" class="input" placeholder="默认：项目内 library/" />

      <label class="label" style="margin-top: 1rem">XCAGI 项目根目录</label>
      <input v-model="xcagi_root" class="input" placeholder="默认：与仓库同级的 XCAGI/" />

      <div class="resolved" v-if="effective">
        <div><span class="muted">当前解析 · 库：</span> {{ effective.library_root }}</div>
        <div><span class="muted">当前解析 · XCAGI：</span> {{ effective.xcagi_root || '（未检测到）' }}</div>
        <div class="muted small">XCAGI mods 就绪: {{ effective.xcagi_ok ? '是' : '否' }}</div>
      </div>

      <div class="row">
        <button type="button" class="btn btn-primary" @click="save">保存配置</button>
        <button type="button" class="btn" @click="reload">重新读取</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { api } from '../api'

const library_root = ref('')
const xcagi_root = ref('')
const effective = ref(null)
const flash = ref('')
const flashOk = ref(true)

async function reload() {
  const c = await api.getConfig()
  library_root.value = c.saved_library_root || ''
  xcagi_root.value = c.saved_xcagi_root || ''
  effective.value = c
}

async function save() {
  flash.value = ''
  try {
    await api.putConfig({
      library_root: library_root.value,
      xcagi_root: xcagi_root.value,
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
  gap: 0.5rem;
  margin-top: 1rem;
}
</style>
