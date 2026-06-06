<template>
  <div class="tyn-settings page-view">
    <header class="tyn-settings__head">
      <h2>考勤转换设置</h2>
      <p class="muted">
        钉钉导出表 →「明细」工作表的裁窗与符号规则。配置保存在
        <code>resources/config/approval_config.yaml</code> 的 <code>attendance_policy</code> 段。
      </p>
      <router-link class="back-link" :to="{ name: 'taiyangniao-pro-home' }">← 返回太阳鸟首页</router-link>
    </header>

    <section class="card-block">
      <p class="hint">
        周一到周六正班默认 08:00–12:00、13:30–17:30；晚上 18:00 后按最后一次打卡计加班；周日按加班处理。
      </p>

      <div v-if="loadError" class="flash flash-err">{{ loadError }}</div>

      <div class="attendance-grid">
        <div class="form-group full-width">
          <label>公司/工厂考勤组关键字（每行一条，匹配考勤组或班次名）</label>
          <textarea v-model="kwText" rows="4" class="inp mono" :disabled="saving" />
        </div>
        <div class="form-group">
          <label>工作日正班时段 1</label>
          <input
            v-model="attendancePolicy.weekday_segments[0]"
            type="text"
            class="inp mono"
            placeholder="08:00-12:00"
            :disabled="saving"
          />
        </div>
        <div class="form-group">
          <label>工作日正班时段 2</label>
          <input
            v-model="attendancePolicy.weekday_segments[1]"
            type="text"
            class="inp mono"
            placeholder="13:30-17:30"
            :disabled="saving"
          />
        </div>
        <div class="form-group checkbox-row">
          <label class="inline-check">
            <input v-model="attendancePolicy.sunday_empty_schedule" type="checkbox" :disabled="saving" />
            周日不设正班裁窗（与「周日仅加班」策略配合）
          </label>
        </div>
        <div class="form-group checkbox-row">
          <label class="inline-check">
            <input v-model="attendancePolicy.sunday_map_sqrt_to_star" type="checkbox" :disabled="saving" />
            周日将原正班 √ / 交叉 ☆ 统一记为星期天加班 ★
          </label>
        </div>
        <button type="button" class="btn btn-primary" :disabled="saving || loading" @click="savePolicy">
          {{ saving ? '保存中…' : '保存考勤规则' }}
        </button>
      </div>
    </section>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { primeCsrfCookie } from '@/api/core'
import { appAlert } from '@/utils/appDialog'
import { apiFetch } from '@/utils/apiBase'

const MOD_API = '/api/mod/taiyangniao-pro'

const loading = ref(true)
const saving = ref(false)
const loadError = ref('')

const defaultAttendancePolicy = () => ({
  company_factory_group_keywords: ['公司-考勤', '公司正班', '惠州工厂-正班', '工厂正班'],
  weekday_segments: ['08:00-12:00', '13:30-17:30'],
  sunday_empty_schedule: true,
  sunday_map_sqrt_to_star: true,
})

const attendancePolicy = ref(defaultAttendancePolicy())

const kwText = computed({
  get: () => (attendancePolicy.value.company_factory_group_keywords || []).join('\n'),
  set: (v) => {
    const lines = String(v || '')
      .split(/\r?\n/)
      .map((s) => s.trim())
      .filter(Boolean)
    attendancePolicy.value.company_factory_group_keywords = lines.length
      ? lines
      : [...defaultAttendancePolicy().company_factory_group_keywords]
  },
})

function mergeAttendanceFromApi(raw) {
  const d = defaultAttendancePolicy()
  const r = raw && typeof raw === 'object' ? raw : {}
  const merged = { ...d, ...r }
  if (!Array.isArray(merged.company_factory_group_keywords)) {
    merged.company_factory_group_keywords = [...d.company_factory_group_keywords]
  }
  if (!Array.isArray(merged.weekday_segments) || merged.weekday_segments.length < 2) {
    merged.weekday_segments = [...d.weekday_segments]
  } else {
    merged.weekday_segments = [String(merged.weekday_segments[0]), String(merged.weekday_segments[1])]
  }
  merged.sunday_empty_schedule =
    r.sunday_empty_schedule !== undefined ? !!r.sunday_empty_schedule : d.sunday_empty_schedule
  merged.sunday_map_sqrt_to_star =
    r.sunday_map_sqrt_to_star !== undefined ? !!r.sunday_map_sqrt_to_star : d.sunday_map_sqrt_to_star
  attendancePolicy.value = merged
}

async function loadPolicy() {
  loading.value = true
  loadError.value = ''
  try {
    const res = await apiFetch(`${MOD_API}/attendance/policy`)
    const data = await res.json()
    if (!res.ok || data.success === false) {
      throw new Error(data.message || data.detail || `HTTP ${res.status}`)
    }
    mergeAttendanceFromApi(data.attendance_policy || data.data?.attendance_policy)
  } catch (e) {
    loadError.value = e instanceof Error ? e.message : String(e)
  } finally {
    loading.value = false
  }
}

async function savePolicy() {
  saving.value = true
  loadError.value = ''
  try {
    const res = await apiFetch(`${MOD_API}/attendance/policy`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ attendance_policy: attendancePolicy.value }),
    })
    const data = await res.json()
    if (!res.ok || data.success === false) {
      throw new Error(data.message || data.detail || `HTTP ${res.status}`)
    }
    mergeAttendanceFromApi(data.attendance_policy || data.data?.attendance_policy)
    await appAlert('考勤规则已保存')
  } catch (e) {
    loadError.value = e instanceof Error ? e.message : String(e)
    await appAlert(loadError.value)
  } finally {
    saving.value = false
  }
}

onMounted(async () => {
  await primeCsrfCookie()
  void loadPolicy()
})
</script>

<style scoped>
.tyn-settings {
  max-width: 900px;
  margin: 0 auto;
  padding: 1rem 1.25rem 2rem;
}

.tyn-settings__head h2 {
  margin: 0 0 0.35rem;
}

.back-link {
  display: inline-block;
  margin-top: 0.75rem;
  font-size: 0.875rem;
  color: var(--wb-accent, #60a5fa);
  text-decoration: none;
}

.back-link:hover {
  text-decoration: underline;
}

.hint {
  margin: 0 0 1rem;
  font-size: 0.875rem;
  line-height: 1.55;
  color: rgba(255, 255, 255, 0.65);
}

.attendance-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
}

.attendance-grid .full-width,
.attendance-grid .checkbox-row,
.attendance-grid .btn {
  grid-column: 1 / -1;
}

.form-group label {
  display: block;
  margin-bottom: 0.35rem;
  font-size: 0.8125rem;
  color: rgba(255, 255, 255, 0.75);
}

.inp {
  width: 100%;
  box-sizing: border-box;
}

.mono {
  font-family: ui-monospace, Consolas, monospace;
}

.inline-check {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.875rem;
  cursor: pointer;
}

.flash-err {
  margin-bottom: 0.75rem;
  padding: 0.5rem 0.75rem;
  border-radius: 6px;
  background: rgba(239, 68, 68, 0.12);
  color: #fca5a5;
  font-size: 0.875rem;
}

@media (max-width: 640px) {
  .attendance-grid {
    grid-template-columns: 1fr;
  }
}
</style>
