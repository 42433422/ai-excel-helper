<template>
  <div class="mod-home page-view">
    <div class="page-grid">
      <div class="page-content page-main">
        <h2>太阳鸟pro</h2>
        <p class="muted">
          Mod ID: <code>taiyangniao-pro</code> — 在库项目中编辑后执行 <code>modman push</code> 部署到 XCAGI。
        </p>
        <p class="muted small">
          <router-link :to="{ name: 'taiyangniao-pro-settings' }">考勤转换设置</router-link>
          （钉钉 → 明细裁窗、加班规则；原在「审批中心 → 流程规则」中，已迁于此）
        </p>

        <section class="card-block bridge-contact" aria-labelledby="bridge-contact-title">
          <h3 id="bridge-contact-title">联系管理员</h3>
          <p class="muted small">
            通过客服桥接把消息送到管理员「内部客服」收件箱（与侧栏「外部客服」同一通道）。
            分机：<code>{{ bridgeInstanceId }}</code>
          </p>
          <div class="form-row">
            <input
              v-model.trim="bridgeTitle"
              type="text"
              class="inp"
              maxlength="256"
              placeholder="简要说明问题或需求"
            />
          </div>
          <div class="form-row">
            <textarea
              v-model.trim="bridgeDescription"
              class="inp"
              rows="2"
              placeholder="补充说明（可选）"
            />
          </div>
          <div class="actions">
            <button
              type="button"
              class="btn primary"
              :disabled="!bridgeTitle || bridgeSending"
              @click="sendBridgeContact"
            >
              {{ bridgeSending ? '发送中…' : '发送到管理员' }}
            </button>
            <router-link class="btn" :to="{ name: 'enterprise-customer-service' }">打开外部客服</router-link>
          </div>
          <p v-if="bridgeOk" class="ok">{{ bridgeOk }}</p>
          <p v-if="bridgeErr" class="err">{{ bridgeErr }}</p>
        </section>

        <section class="card-block" aria-labelledby="upload-convert-title">
          <h3 id="upload-convert-title">上传转化</h3>
          <p class="muted small">
            将钉钉导出的考勤 xlsx 上传后，由宿主
            <code>app/shell/taiyangniao_attendance/</code>
            按列别名解析「每日统计」等表。默认<strong>按侧栏「人员管理」</strong>（主库产品表：姓名、部门对应「单位」、性质对应「规格」）重排「明细」每人 6 行，再按姓名把钉钉数据一一填入；<strong>无钉钉记录则打卡区留空</strong>。取消勾选下方选项时，改为仅使用固定模板「明细」里原有姓名名单。路径相对
            <code>WORKSPACE_ROOT</code>（默认写入 <code>424/</code>）。成功后会自动下载，也可点「再次下载」。
          </p>

          <div class="form-row">
            <label class="lbl">钉钉考勤表</label>
            <input type="file" accept=".xlsx,.xlsm,.xls" class="file" @change="onFile" />
          </div>

          <div class="form-row">
            <label class="lbl" for="out-rel">输出相对路径</label>
            <input
              id="out-rel"
              v-model.trim="outputRelpath"
              type="text"
              class="inp"
              placeholder="如 424/考勤转换结果.xlsx（建议填新文件名）"
              autocomplete="off"
            />
          </div>

          <div class="form-row">
            <label class="lbl" for="tpl-rel">模板相对路径（固定）</label>
            <input
              id="tpl-rel"
              v-model.trim="templateRelpath"
              type="text"
              class="inp"
              placeholder="如 424/考勤-2026-3月份考勤统计表.xlsx"
              readonly
              autocomplete="off"
            />
            <p class="hint">
              按你指定的固定模板回填：424/考勤-2026-3月份考勤统计表.xlsx
            </p>
          </div>

          <div class="form-row inline">
            <div class="grow">
              <label class="lbl" for="month">统计月份（可选）</label>
              <input id="month" v-model.trim="month" type="text" class="inp" placeholder="YYYY-MM" />
            </div>
            <div class="grow">
              <label class="lbl" for="hdr">表头所在行（0 为自动识别）</label>
              <input id="hdr" v-model.number="headerRow" type="number" min="0" class="inp narrow" />
            </div>
          </div>

          <div class="form-row">
            <label class="lbl checkbox">
              <input type="checkbox" v-model="usePersonnelRoster" />
              按「人员管理」名单重排明细并回填（有钉钉则填，无则空）
            </label>
            <p class="hint">与侧栏「人员管理」同一数据源；请先在其中维护员工名单。</p>
          </div>

          <div class="form-row">
            <label class="lbl checkbox">
              <input type="checkbox" v-model="useLlm" />
              本地规则识别不出时，调用我的 LLM 智能识别表头
            </label>
            <p class="hint">
              仅当出现 "表头未识别" 或 "0 行" 时才会真正调用模型；需后端配置
              <code>OPENAI_API_KEY</code> 或 <code>DEEPSEEK_API_KEY</code>。
            </p>
          </div>

          <div class="actions">
            <button type="button" class="btn primary" :disabled="!file || loading" @click="doUploadConvert">
              {{ loading ? '转换中…' : '上传并转换' }}
            </button>
            <button
              v-if="lastOutputRelpath"
              type="button"
              class="btn"
              :disabled="loadingDl"
              @click="downloadOutput(lastOutputRelpath)"
            >
              {{ loadingDl ? '下载中…' : '再次下载' }}
            </button>
          </div>

          <p v-if="err" class="err">{{ err }}</p>
          <p v-if="okMsg" class="ok">{{ okMsg }}</p>
        </section>
      </div>

      <aside class="rules-sidebar" aria-labelledby="rules-title">
        <div class="rules-card">
          <h3 id="rules-title" class="rules-title">考勤规则</h3>
          <p class="rules-sub muted small">
            与宿主 <code>app/shell/taiyangniao_attendance/rules.py</code> 默认配置一致；转换时使用同一套逻辑。
          </p>
          <p v-if="rulesLoading" class="rules-muted">加载中…</p>
          <p v-else-if="rulesErr" class="rules-err">{{ rulesErr }}</p>
          <template v-else-if="rulesLines.length">
            <p v-if="rulesWindow" class="rules-window">
              当前周六有效时段：<strong>{{ rulesWindow }}</strong>
            </p>
            <ul class="rules-list">
              <li v-for="(ln, i) in rulesLines" :key="i">{{ ln }}</li>
            </ul>

            <section
              v-if="scheduleGroups.length"
              class="schedule-groups"
              aria-labelledby="sched-ref-title"
            >
              <h4 id="sched-ref-title" class="schedule-groups__title">钉钉考勤组（参考）</h4>
              <p class="schedule-groups__hint muted small">
                与钉钉后台「固定班制」排班文案一致，便于对照；转换时按导出表中的考勤组/部门列名匹配规则。
              </p>
              <div
                v-for="(g, gi) in scheduleGroups"
                :key="gi"
                class="schedule-group-card"
              >
                <div class="schedule-group-card__head">
                  <span class="schedule-group-card__name">{{ g.name }}</span>
                  <span class="schedule-group-card__meta">{{ g.headcount }} · {{ g.shift_type }}</span>
                </div>
                <ul class="schedule-group-card__lines">
                  <li v-for="(sl, si) in (g.lines || [])" :key="si">{{ sl }}</li>
                </ul>
              </div>
            </section>

            <details v-if="rulesConfigKeys.length" class="rules-details">
              <summary>默认参数（只读）</summary>
              <dl class="rules-dl">
                <template v-for="k in rulesConfigKeys" :key="k">
                  <dt>{{ k }}</dt>
                  <dd>{{ formatConfigValue(rulesConfig[k]) }}</dd>
                </template>
              </dl>
            </details>
          </template>
        </div>
      </aside>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { apiFetch } from '@/utils/apiBase'
import { useServiceBridge } from '@/composables/useServiceBridge'
import { useServiceBridgeInstance } from '@/composables/useServiceBridgeInstance'

const { instanceId: bridgeInstanceId, instanceName: bridgeInstanceName, persistInstanceSnapshot } =
  useServiceBridgeInstance()
const { createEnterpriseContact, submitting: bridgeSending } = useServiceBridge()
const bridgeTitle = ref('')
const bridgeDescription = ref('')
const bridgeOk = ref('')
const bridgeErr = ref('')

async function sendBridgeContact() {
  if (!bridgeTitle.value.trim()) return
  bridgeOk.value = ''
  bridgeErr.value = ''
  persistInstanceSnapshot()
  try {
    await createEnterpriseContact({
      source_instance_id: bridgeInstanceId.value,
      source_instance_name: bridgeInstanceName.value,
      request_type: '建议',
      title: bridgeTitle.value.trim(),
      description: bridgeDescription.value.trim() || undefined,
      priority: 'normal',
    })
    bridgeOk.value = '已送达管理员总机，请在「外部客服」查看进度。'
    bridgeTitle.value = ''
    bridgeDescription.value = ''
  } catch (e) {
    bridgeErr.value = e instanceof Error ? e.message : '发送失败'
  }
}

// 原有考勤转换相关
const file = ref(null)
const outputRelpath = ref('424/考勤转换输出.xlsx')
const templateRelpath = ref('424/考勤-2026-3月份考勤统计表.xlsx')
const month = ref('')
const headerRow = ref(0)
const usePersonnelRoster = ref(true)
const useLlm = ref(false)
const loading = ref(false)
const loadingDl = ref(false)
const err = ref('')
const okMsg = ref('')
const lastOutputRelpath = ref('')

// 规则加载
const rulesLoading = ref(true)
const rulesErr = ref('')
const rulesPayload = ref(null)

// 原有规则相关
const rulesLines = computed(() => {
  const d = rulesPayload.value
  if (!d || !Array.isArray(d.lines)) return []
  return d.lines.filter((x) => typeof x === 'string' && x.trim())
})

const rulesWindow = computed(() => {
  const w = rulesPayload.value?.saturday_window_label
  return typeof w === 'string' && w.trim() ? w.trim() : ''
})

const rulesConfig = computed(() => {
  const c = rulesPayload.value?.config
  return c && typeof c === 'object' ? c : {}
})

const rulesConfigKeys = computed(() => Object.keys(rulesConfig.value).sort())

const scheduleGroups = computed(() => {
  const raw = rulesPayload.value?.schedule_groups
  return Array.isArray(raw) ? raw : []
})

function formatConfigValue(v) {
  if (typeof v === 'boolean') return v ? '是' : '否'
  return String(v)
}

async function loadRules() {
  rulesLoading.value = true
  rulesErr.value = ''
  try {
    const res = await apiFetch('/api/mod/taiyangniao-pro/attendance/rules')
    const j = await res.json().catch(() => ({}))
    if (!res.ok) {
      rulesErr.value = j.error || j.message || `HTTP ${res.status}`
      rulesPayload.value = null
      return
    }
    if (!j.success) {
      rulesErr.value = j.error || '无法加载规则'
      rulesPayload.value = null
      return
    }
    rulesPayload.value = j.data && typeof j.data === 'object' ? j.data : null
  } catch (e) {
    rulesErr.value = e instanceof Error ? e.message : String(e)
    rulesPayload.value = null
  } finally {
    rulesLoading.value = false
  }
}

onMounted(() => {
  void loadRules()
})

function onFile(ev) {
  const f = ev.target?.files?.[0]
  file.value = f || null
  err.value = ''
  okMsg.value = ''
}

function _basename(rel) {
  const s = String(rel || '').replace(/\\/g, '/')
  const i = s.lastIndexOf('/')
  return i >= 0 ? s.slice(i + 1) : s || '考勤转换输出.xlsx'
}

async function downloadOutput(relpath) {
  const rel = String(relpath || '').trim()
  if (!rel) return
  loadingDl.value = true
  err.value = ''
  try {
    const q = new URLSearchParams()
    q.set('relpath', rel)
    const res = await apiFetch(`/api/mod/taiyangniao-pro/attendance/download?${q.toString()}`)
    if (!res.ok) {
      const t = await res.text().catch(() => '')
      err.value = t || `下载失败 HTTP ${res.status}`
      return
    }
    const blob = await res.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = _basename(rel)
    a.rel = 'noopener'
    document.body.appendChild(a)
    a.click()
    a.remove()
    URL.revokeObjectURL(url)
  } catch (e) {
    err.value = e instanceof Error ? e.message : String(e)
  } finally {
    loadingDl.value = false
  }
}

async function doUploadConvert() {
  err.value = ''
  okMsg.value = ''
  if (!file.value) {
    err.value = '请先选择钉钉导出的 Excel 文件。'
    return
  }

  // 检查填写方式是否正确
  const outPath = outputRelpath.value || '424/考勤转换输出.xlsx'
  const tplPath = templateRelpath.value || ''

  // 如果输出路径看起来像一个现有模板文件（包含考勤统计表），但没有单独指定模板
  if (outPath.includes('考勤统计表') && !tplPath) {
    const confirmed = confirm(
      `你填写的输出路径 "${outPath}" 看起来像是一个现有模板文件。\\n\\n` +
      `建议填写方式：\\n` +
      `• 输出相对路径：填一个新文件名，如 "424/考勤转换结果.xlsx"\\n` +
      `• 模板相对路径（可选）：填现有模板文件，如 "${outPath}"\\n\\n` +
      `是否继续当前填写方式？`
    )
    if (!confirmed) {
      return
    }
  }

  loading.value = true
  try {
    const fd = new FormData()
    fd.append('file', file.value)
    fd.append('output_relpath', outputRelpath.value || '424/考勤转换输出.xlsx')
    if (templateRelpath.value) fd.append('template_relpath', templateRelpath.value)
    if (month.value) fd.append('month', month.value)
    fd.append('header_row', String(Number.isFinite(headerRow.value) ? headerRow.value : 0))
    if (useLlm.value) fd.append('use_llm', '1')
    fd.append('use_personnel_roster', usePersonnelRoster.value ? '1' : '0')

    const res = await apiFetch('/api/mod/taiyangniao-pro/attendance/convert-upload', {
      method: 'POST',
      body: fd,
    })
    const j = await res.json().catch(() => ({}))
    if (!res.ok || !j.success) {
      err.value = j.error || j.message || `HTTP ${res.status}`
      return
    }
    const d = j.data || {}
    const rowsIn = Number(d.rows_in ?? 0)
    const rowsStats = Number(d.rows_stats ?? 0)
    // 旧版后端仍可能在「成功」里返回 0 行；新版应返回 422。此处兜底避免误导性绿字。
    if (rowsIn === 0 && rowsStats === 0) {
      err.value =
        '未解析到任何考勤数据行（源表 0 行）。请确认：① 已重新部署/重启并加载当前仓库里的太阳鸟 pro（含智能表头识别）；' +
        '② 或填写「表头所在行」、勾选「LLM 识别表头」后重试。若成功提示里应出现 [表头识别:…] 片段。'
      okMsg.value = ''
      return
    }
    const outRel = d.output_relpath || outputRelpath.value
    lastOutputRelpath.value = outRel
    const hi = d.header_info || {}
    const tag = hi.source ? `[表头识别:${hi.source}@行${hi.header_row}]` : ''
    const llmTag = d.used_llm ? '（LLM 参与）' : ''
    const ru = d.rows_used_for_template
    const ruTxt =
      ru != null && ru !== '' && Number(ru) !== Number(d.rows_in)
        ? `；与名单姓名匹配 ${ru} 条日记录用于回填`
        : ''
    const prc = Number(d.personnel_roster_count ?? 0)
    const prTxt = prc > 0 ? `；人员管理 ${prc} 人` : ''
    okMsg.value = `完成：输出 ${outRel}；钉钉源表 ${d.rows_in ?? '?'} 行，统计 ${d.rows_stats ?? '?'} 行${prTxt}${ruTxt}${tag}${llmTag}。`
    await downloadOutput(outRel)
    if (!err.value) {
      okMsg.value += ' 已自动下载。'
    }
  } catch (e) {
    err.value = e instanceof Error ? e.message : String(e)
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.page-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(260px, 320px);
  gap: 1.5rem;
  align-items: start;
  max-width: 1120px;
}

@media (max-width: 900px) {
  .page-grid {
    grid-template-columns: 1fr;
  }
}

.mod-home .muted {
  color: #666;
  margin-top: 0.5rem;
}
.small {
  font-size: 13px;
  line-height: 1.5;
}
.page-main .small {
  max-width: none;
}

.card-block {
  margin-top: 1.5rem;
  padding: 1.25rem 1.35rem;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  background: #fafafa;
}

.card-block h3 {
  margin: 0 0 0.5rem;
  font-size: 1.1rem;
}

.form-row {
  margin-top: 0.85rem;
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.form-row.inline {
  flex-direction: row;
  flex-wrap: wrap;
  gap: 1rem;
}

.grow {
  flex: 1;
  min-width: 140px;
}

.lbl {
  font-size: 12px;
  font-weight: 600;
  color: #334155;
}

.hint {
  margin: 0;
  font-size: 12px;
  color: #64748b;
}

.inp {
  padding: 8px 10px;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  font-size: 14px;
}

.inp.narrow {
  max-width: 120px;
}

.file {
  font-size: 13px;
}

.actions {
  margin-top: 1rem;
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  align-items: center;
}

.btn {
  padding: 8px 18px;
  border-radius: 6px;
  border: 1px solid #94a3b8;
  background: #fff;
  cursor: pointer;
  font-size: 14px;
}

.btn.primary {
  background: #2563eb;
  border-color: #1d4ed8;
  color: #fff;
}

.btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.err {
  margin-top: 0.75rem;
  color: #b91c1c;
  font-size: 13px;
}

.ok {
  margin-top: 0.75rem;
  color: #15803d;
  font-size: 13px;
}

.rules-sidebar {
  position: sticky;
  top: 1rem;
}

.rules-card {
  padding: 1.1rem 1.2rem;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  background: #f8fafc;
  box-shadow: 0 1px 2px rgb(15 23 42 / 6%);
}

.rules-title {
  margin: 0 0 0.35rem;
  font-size: 1.05rem;
  color: #0f172a;
}

.rules-sub {
  margin: 0 0 0.75rem;
}

.rules-window {
  margin: 0 0 0.65rem;
  font-size: 13px;
  color: #334155;
}

.rules-list {
  margin: 0;
  padding-left: 1.15rem;
  font-size: 13px;
  line-height: 1.55;
  color: #1e293b;
}

.rules-list li + li {
  margin-top: 0.4rem;
}

.rules-muted {
  margin: 0;
  font-size: 13px;
  color: #64748b;
}

.rules-err {
  margin: 0;
  font-size: 13px;
  color: #b91c1c;
}

.rules-details {
  margin-top: 0.85rem;
  font-size: 12px;
  color: #475569;
}

.rules-dl {
  margin: 0.5rem 0 0;
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 0.25rem 0.75rem;
  font-size: 12px;
}

.rules-dl dt {
  font-weight: 600;
  color: #64748b;
}

.rules-dl dd {
  margin: 0;
  font-family: ui-monospace, monospace;
  word-break: break-all;
}

.schedule-groups {
  margin-top: 1.1rem;
  padding-top: 1rem;
  border-top: 1px solid #e2e8f0;
}

.schedule-groups__title {
  margin: 0 0 0.35rem;
  font-size: 0.95rem;
  color: #0f172a;
}

.schedule-groups__hint {
  margin: 0 0 0.75rem;
}

.schedule-group-card {
  margin-bottom: 0.75rem;
  padding: 0.65rem 0.75rem;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: #fff;
}

.schedule-group-card:last-child {
  margin-bottom: 0;
}

.schedule-group-card__head {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  justify-content: space-between;
  gap: 0.35rem 0.75rem;
  margin-bottom: 0.4rem;
}

.schedule-group-card__name {
  font-weight: 600;
  font-size: 13px;
  color: #1d4ed8;
}

.schedule-group-card__meta {
  font-size: 12px;
  color: #64748b;
  white-space: nowrap;
}

.schedule-group-card__lines {
  margin: 0;
  padding-left: 1.1rem;
  font-size: 12px;
  line-height: 1.5;
  color: #334155;
}

.schedule-group-card__lines li + li {
  margin-top: 0.25rem;
}
</style>