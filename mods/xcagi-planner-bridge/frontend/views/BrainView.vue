<template>
  <div class="page-view" id="view-brain">
    <div class="page-content brain-page">
      <div class="page-header brain-agent-header">
        <div class="brain-agent-title-row">
          <h2>AI智脑集成</h2>
          <span class="brain-agent-badge" title="编排与观测控制台">Agent</span>
        </div>
        <p class="muted brain-sub">
          下方为 <strong>Agent 控制台</strong>（对话走 <code class="brain-mono">/api/ai/unified_chat</code>，与主助手同源 Planner）。
          P1 / P2 与口令说明见状态条；架构、OpenAPI、code-editor 联调仍在页内分区。
        </p>
      </div>

      <div class="brain-status-bar" role="region" aria-label="Agent 状态">
        <div class="brain-status-chips">
          <span
            class="brain-chip"
            :class="clientTier === 'p2' ? 'brain-chip--p2' : 'brain-chip--p1'"
          >
            本机意图：{{ clientTier === 'p2' ? 'P2' : 'P1' }}
          </span>
          <span v-if="tierStatusLoading" class="brain-chip brain-chip--muted">同步服务端…</span>
          <template v-else>
            <span
              class="brain-chip brain-chip--muted"
              title="服务端是否配置 FHD_AI_ELEVATED_TOKEN"
            >
              提升口令：{{ tierStatus?.elevated_token_configured ? '已配置' : '未配置' }}
            </span>
            <span v-if="tierStatus?.tier_strict" class="brain-chip brain-chip--warn">严格模式</span>
          </template>
        </div>
        <div class="brain-status-actions">
          <span v-if="openapiLoadedAt" class="brain-status-meta">
            OpenAPI：{{ openapiLoadedAt }}
          </span>
          <router-link to="/settings" class="brain-link-settings">系统设置</router-link>
        </div>
      </div>

      <!-- Claude Code 风格：主对话壳（深色控制台 + 底部输入） -->
      <section class="brain-agent-console" aria-label="Agent 对话">
        <header class="brain-agent-console__head">
          <div class="brain-agent-console__title">
            <span class="brain-agent-console__dot" aria-hidden="true" />
            <span>Agent</span>
            <span class="brain-agent-console__sub">unified_chat</span>
          </div>
          <div class="brain-agent-console__actions">
            <span
              v-if="brainAgentSessionId"
              class="brain-agent-console__session-id"
              :title="brainAgentSessionId"
            >session {{ brainAgentSessionId.slice(0, 10) }}…</span>
            <button type="button" class="brain-agent-console__btn" :disabled="agentSending" @click="clearAgentChat">
              清空会话
            </button>
          </div>
        </header>
        <div ref="agentScrollRef" class="brain-agent-console__messages" role="log" aria-live="polite">
          <div v-if="!agentMessages.length" class="brain-agent-console__empty muted">
            输入问题或任务说明：<strong>Ctrl+Enter</strong> / <strong>⌘+Enter</strong> 或点「发送」；换行用普通 Enter。与主助手同源 Planner；会话 ID 存于 sessionStorage。
          </div>
          <div
            v-for="m in agentMessages"
            :key="m.id"
            class="brain-agent-msg"
            :class="'brain-agent-msg--' + m.role"
          >
            <div class="brain-agent-msg__role">{{ m.role === 'user' ? 'You' : m.role === 'assistant' ? 'Agent' : '…' }}</div>
            <pre class="brain-agent-msg__body">{{ m.content }}</pre>
          </div>
          <div v-if="agentSending" class="brain-agent-msg brain-agent-msg--assistant brain-agent-msg--pending">
            <div class="brain-agent-msg__role">Agent</div>
            <div class="brain-agent-msg__body brain-agent-msg__typing">正在思考…</div>
          </div>
        </div>
        <div class="brain-agent-console__composer">
          <textarea
            v-model="agentInput"
            class="brain-agent-console__input"
            rows="3"
            :disabled="agentSending"
            placeholder="描述任务或提问…（Ctrl+Enter / ⌘+Enter 发送）"
            spellcheck="true"
            @keydown="onAgentComposerKeydown"
          />
          <div class="brain-agent-console__composer-bar">
            <span class="brain-agent-console__hint muted">{{ clientTier === 'p2' ? 'P2 · 工具集更宽' : 'P1 · 默认' }}</span>
            <button
              type="button"
              class="btn btn-primary btn-sm brain-agent-console__send"
              :disabled="agentSending || !agentInput.trim()"
              @click="sendAgentMessage"
            >
              发送
            </button>
          </div>
        </div>
      </section>

      <div class="brain-layout" :style="brainPaneStyle">
        <div class="brain-main">
          <div class="brain-tabs" role="tablist" aria-label="智脑分区">
            <button
              v-for="t in tabs"
              :key="t.id"
              type="button"
              class="brain-tab"
              :class="{ active: activeTab === t.id }"
              role="tab"
              :aria-selected="activeTab === t.id"
              @click="activeTab = t.id"
            >
              {{ t.label }}
            </button>
          </div>

          <div v-show="activeTab === 'architecture'" class="brain-panel card brain-card">
            <div class="card-header">Level 3 · 页面层（Vue3）</div>
            <p class="muted">
              主交互与路由；下列组件为<strong>规划清单</strong>，待接入独立路由与侧栏入口。
            </p>
            <ul class="brain-list">
              <li><code>CodeEditorView.vue</code> — 主编辑区</li>
              <li><code>DiffViewer.vue</code> — Diff 对比</li>
              <li><code>FileTree.vue</code> — 文件树</li>
            </ul>
            <details class="brain-details">
              <summary>整体关系（示意）</summary>
              <pre class="brain-diagram" aria-label="三层架构示意">{{ architectureDiagram }}</pre>
            </details>
          </div>

          <div v-show="activeTab === 'api'" class="brain-panel card brain-card">
            <div class="card-header">Level 2 · 接口层（当前 OpenAPI）</div>
            <p class="muted">
              数据来自 <code class="brain-mono">GET /api/system/openapi</code>（与仅反代 <code class="brain-mono">/api</code> 的部署一致）。
            </p>
            <div v-if="openapiError" class="muted text-warn">{{ openapiError }}</div>
            <div v-else-if="openapiLoading" class="muted">加载 OpenAPI…</div>
            <template v-else>
              <div class="form-group brain-search">
                <label for="brain-api-filter">按 path 过滤</label>
                <input
                  id="brain-api-filter"
                  v-model="apiFilter"
                  type="search"
                  placeholder="例如 /api/system 或 chat"
                  class="brain-input-mono"
                  autocomplete="off"
                >
              </div>
              <p class="muted brain-count">
                共 <strong>{{ filteredOperations.length }}</strong> 条 operation（{{ openapiTitle }}）
              </p>
              <div class="brain-table-wrap">
                <table class="brain-table">
                  <thead>
                    <tr>
                      <th>Method</th>
                      <th>Path</th>
                      <th>Summary / operationId</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="(row, idx) in filteredOperations" :key="idx">
                      <td>
                        <span class="brain-method-chip" :class="'brain-method-chip--' + row.method.toLowerCase()">
                          {{ row.method }}
                        </span>
                      </td>
                      <td><code class="brain-mono">{{ row.path }}</code></td>
                      <td>{{ row.summary }}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </template>
            <p class="muted brain-future">
              规划中的代码编辑接口示例：<code class="brain-mono">POST /api/code-editor/analyze</code>、
              <code class="brain-mono">POST /api/code-editor/edit</code>、<code class="brain-mono">GET /api/code-editor/diff/{id}</code>、
              <code class="brain-mono">POST /api/code-editor/apply/{id}</code> — 实现后将出现在上表。
            </p>
          </div>

          <div v-show="activeTab === 'skills'" class="brain-panel card brain-card">
            <div class="card-header">Level 1 · 能力层（Skill）</div>
            <p class="muted">与 code-editor 栈对齐：analyze / edit / diff 可联调；apply 须设置页 P2 + 与服务器一致的提升口令。</p>
            <div class="brain-skill-grid">
              <article v-for="s in skillRows" :key="s.id" class="brain-skill-card">
                <header class="brain-skill-card__head">
                  <code class="brain-skill-card__id">{{ s.id }}</code>
                  <span class="brain-skill-card__status">{{ s.status }}</span>
                </header>
                <p class="brain-skill-card__desc">{{ s.desc }}</p>
              </article>
            </div>
            <div class="brain-code-editor-stub">
              <div class="brain-obs-title">code-editor 契约</div>
              <p class="muted brain-obs-hint">
                路径均相对 <code class="brain-mono">WORKSPACE_ROOT</code>。
                <code class="brain-mono">POST /edit</code> 提交完整
                <code class="brain-mono">new_content</code>；
                <code class="brain-mono">POST /apply</code> 会带上本机 P2 头并写盘。勾选「新建」时父目录须已存在，且为可识别文本后缀。
              </p>
              <label class="brain-stub-check">
                <input v-model="codeCreateIfMissing" type="checkbox" />
                <span class="muted">create_if_missing（path 不存在时按新建文本提案）</span>
              </label>
              <label class="brain-stub-path">
                <span class="muted">path</span>
                <input
                  v-model="codeAnalyzePath"
                  type="text"
                  class="brain-stub-path__input"
                  placeholder="例如 backend/env.example（留空则 noop）"
                  autocomplete="off"
                />
              </label>
              <label class="brain-stub-path">
                <span class="muted">new_content（POST /edit）</span>
                <textarea
                  v-model="codeEditNewContent"
                  class="brain-stub-textarea"
                  rows="4"
                  placeholder="编辑后的完整文件 UTF-8 文本…"
                  spellcheck="false"
                />
              </label>
              <label class="brain-stub-path">
                <span class="muted">instruction（POST /draft，须 P2 + LLM）</span>
                <textarea
                  v-model="codeDraftInstruction"
                  class="brain-stub-textarea brain-stub-textarea--sm"
                  rows="2"
                  placeholder="用自然语言描述希望对 path 的修改；成功后结果写入下方 new_content"
                  spellcheck="true"
                />
              </label>
              <div class="brain-stub-actions brain-stub-actions--wrap">
                <button type="button" class="btn btn-secondary btn-sm" :disabled="!codeLastPreview" @click="fillNewFromPreview">
                  用上次 analyze 预览填入
                </button>
                <button
                  type="button"
                  class="btn btn-secondary btn-sm"
                  :disabled="codeProbeLoading || !codeAnalyzePath.trim() || !codeDraftInstruction.trim()"
                  @click="probeCodeEditorDraft"
                >
                  POST /draft
                </button>
              </div>
              <div class="brain-stub-actions">
                <button
                  type="button"
                  class="btn btn-secondary btn-sm"
                  :disabled="codeProbeLoading"
                  @click="probeCodeEditorStatus"
                >
                  GET /status
                </button>
                <button
                  type="button"
                  class="btn btn-secondary btn-sm"
                  :disabled="codeProbeLoading"
                  @click="probeCodeEditorAnalyze"
                >
                  POST /analyze
                </button>
                <button
                  type="button"
                  class="btn btn-secondary btn-sm"
                  :disabled="codeProbeLoading || !codeAnalyzePath.trim() || !codeEditNewContent"
                  @click="probeCodeEditorEdit"
                >
                  POST /edit
                </button>
                <button
                  type="button"
                  class="btn btn-secondary btn-sm"
                  :disabled="codeProbeLoading || !lastEditId"
                  @click="probeCodeEditorDiff"
                >
                  GET /diff
                </button>
                <button
                  type="button"
                  class="btn btn-secondary btn-sm"
                  :disabled="codeProbeLoading || !lastEditId"
                  @click="probeCodeEditorApply"
                >
                  POST /apply
                </button>
              </div>
              <p v-if="lastEditId" class="muted brain-stub-editid">
                当前 <code class="brain-mono">edit_id</code>：<code class="brain-mono">{{ lastEditId }}</code>
              </p>
            </div>
          </div>
          <PaneResizeHandle
            v-if="isBrainPaneResizable"
            orientation="vertical"
            label="调整观测面板宽度"
            @resize-start="onBrainPaneResizeStart"
            @reset="resetBrainPaneWidth"
          />
        </div>

        <aside class="brain-obs" aria-label="观测与活动">
          <div class="brain-obs-section">
            <div class="brain-obs-title">活动流</div>
            <p class="muted brain-obs-hint">占位：后续可对接 Planner / Agent 事件或审计日志。</p>
            <ul class="brain-activity-log">
              <li v-for="(line, i) in activityLines" :key="i" class="brain-activity-log__item">
                <span class="brain-activity-log__ts">{{ line.ts }}</span>
                <span class="brain-activity-log__msg">{{ line.msg }}</span>
              </li>
            </ul>
          </div>
          <details class="brain-details brain-obs-details brain-obs-models">
            <summary>模型注册（GET /api/fhd/ai/models）</summary>
            <div v-if="modelsLoading" class="muted brain-models-hint">加载中…</div>
            <div v-else-if="modelsError" class="muted text-warn">{{ modelsError }}</div>
            <ul v-else-if="publicModels.length" class="brain-models-list">
              <li v-for="m in publicModels" :key="m.id" class="brain-models-item">
                <div class="brain-models-row">
                  <code class="brain-mono brain-models-id">{{ m.id }}</code>
                  <span class="brain-models-chip">{{ m.provider }}</span>
                </div>
                <div class="brain-models-label">{{ m.label }}</div>
              </li>
            </ul>
            <p v-else class="muted brain-models-hint">暂无条目（可在后端配置 FHD_PUBLIC_MODEL_REGISTRY_JSON）</p>
          </details>
          <details class="brain-details brain-obs-details">
            <summary>架构简图（折叠）</summary>
            <pre class="brain-diagram brain-diagram--compact" aria-label="三层架构简图">{{ architectureDiagram }}</pre>
          </details>
        </aside>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { ApiError } from '@/api'
import chatApi from '@/api/chat'
import PaneResizeHandle from '@/components/PaneResizeHandle.vue'
import { useResizablePane } from '@/composables/useResizablePane'
import { apiFetch } from '@/utils/apiBase'
import {
  XCAGI_AI_DEVELOPER_MODE_KEY,
  XCAGI_AI_ELEVATED_TOKEN_KEY,
  XCAGI_AI_TIER_CHANGED_EVENT
} from '@/utils/xcagiStorageKeys'

const BRAIN_AGENT_SESSION_KEY = 'xcagi_brain_agent_session_id'
const BRAIN_LAYOUT_MQ = '(max-width: 960px)'

const tabs = [
  { id: 'architecture', label: '架构' },
  { id: 'api', label: 'API' },
  { id: 'skills', label: 'Skill' }
]

const activeTab = ref('architecture')
const isBrainPaneResizable = ref(true)
let brainPaneViewportMedia = null

const tierStatus = ref(null)
const tierStatusLoading = ref(true)
const openapiLoadedAt = ref('')

const architectureDiagram = `┌─────────────────────────────────────────────────────────┐
│  Level 3: Page (页面层)     ← Vue3 前端交互             │
│  - CodeEditorView.vue       ← 主页面                     │
│  - DiffViewer.vue          ← Diff 对比                   │
│  - FileTree.vue            ← 文件树                      │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│  Level 2: API (接口层)      ← FastAPI 提供接口           │
│  POST /api/code-editor/analyze   ← 分析代码            │
│  POST /api/code-editor/edit      ← 生成修改建议        │
│  GET  /api/code-editor/diff/{id} ← 获取 Diff          │
│  POST /api/code-editor/apply/{id} ← 应用修改          │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│  Level 1: Skill (能力层)    ← 底层代码处理能力           │
│  - CodeAnalyzerSkill    ← 分析/解释/审查代码            │
│  - CodeEditorSkill      ← 生成修改建议                 │
│  - BackupManager        ← 备份/恢复机制                │
└─────────────────────────────────────────────────────────┘`

const skillRows = [
  {
    id: 'CodeAnalyzerSkill',
    desc: '分析、解释、审查代码',
    status: '✅ 已实现 v1.0'
  },
  {
    id: 'CodeEditorSkill',
    desc: '生成修改建议',
    status: '✅ 已实现 v1.0'
  },
  {
    id: 'BackupManager',
    desc: '备份与恢复',
    status: '✅ 已实现 v1.0'
  }
]

const openapiSpec = ref(null)
const openapiLoading = ref(true)
const openapiError = ref('')
const apiFilter = ref('')

const activityLines = ref([{ ts: '--:--:--', msg: '等待接入事件源…' }])

/** GET /api/fhd/ai/models 元数据（无密钥） */
const publicModels = ref([])
const modelsLoading = ref(true)
const modelsError = ref('')

const codeProbeLoading = ref(false)
/** 相对 WORKSPACE_ROOT，传给 POST /api/code-editor/analyze */
const codeAnalyzePath = ref('')
/** POST /edit 的完整新文本 */
const codeEditNewContent = ref('')
/** 最近一次 text_preview 的原文，用于一键填入 new_content */
const codeLastPreview = ref('')
/** 最近一次 POST /edit 返回的 edit_id */
const lastEditId = ref('')
/** POST /edit：path 不存在时在已有父目录下新建文本（与后端 JSON 严格 true 一致） */
const codeCreateIfMissing = ref(false)
/** POST /api/code-editor/draft */
const codeDraftInstruction = ref('')

/** Agent 控制台（Claude Code 风格对话壳） */
const agentScrollRef = ref(null)
const agentMessages = ref([])
const agentInput = ref('')
const agentSending = ref(false)
const brainAgentSessionId = ref('')
let brainAgentMsgSeq = 0

function nextBrainAgentMsgId() {
  brainAgentMsgSeq += 1
  return `brain-agent-${brainAgentMsgSeq}`
}

function readBrainAgentSessionId() {
  try {
    const s = window.sessionStorage.getItem(BRAIN_AGENT_SESSION_KEY)
    return s && String(s).trim() ? String(s).trim() : ''
  } catch {
    return ''
  }
}

function persistBrainAgentSessionId(id) {
  try {
    if (id) window.sessionStorage.setItem(BRAIN_AGENT_SESSION_KEY, id)
  } catch {
    /* ignore */
  }
}

function scrollAgentConsoleToBottom() {
  const el = agentScrollRef.value
  if (el && typeof el.scrollTop === 'number') {
    el.scrollTop = el.scrollHeight
  }
}

function extractUnifiedChatReply(res) {
  if (!res || typeof res !== 'object') return ''
  if (typeof res.response === 'string') return res.response
  const d = res.data
  if (d && typeof d === 'object') {
    if (typeof d.response === 'string') return d.response
    if (typeof d.text === 'string') return d.text
    if (d.message && typeof d.message.content === 'string') return d.message.content
  }
  if (res.success === false && res.message) return `请求未成功：${res.message}`
  if (res.error) return `错误：${res.error}`
  return ''
}

function extractSessionIdFromChatResponse(res) {
  if (!res || typeof res !== 'object') return ''
  const d = res.data
  if (d && typeof d.session_id === 'string' && d.session_id.trim()) return d.session_id.trim()
  if (typeof res.session_id === 'string' && res.session_id.trim()) return res.session_id.trim()
  return ''
}

async function clearAgentChat() {
  agentMessages.value = []
  agentInput.value = ''
  brainAgentSessionId.value = ''
  try {
    window.sessionStorage.removeItem(BRAIN_AGENT_SESSION_KEY)
  } catch {
    /* ignore */
  }
  pushActivity('已清空智脑 Agent 对话')
  await initBrainAgentSession()
}

function onAgentComposerKeydown(e) {
  if (e.key !== 'Enter') return
  if (e.ctrlKey || e.metaKey) {
    e.preventDefault()
    sendAgentMessage()
  }
}

async function sendAgentMessage() {
  const text = agentInput.value.trim()
  if (!text || agentSending.value) return
  agentSending.value = true
  agentMessages.value.push({ id: nextBrainAgentMsgId(), role: 'user', content: text })
  agentInput.value = ''
  await nextTick()
  scrollAgentConsoleToBottom()
  try {
    const payload = { message: text, source: 'brain_console' }
    const sid0 = brainAgentSessionId.value.trim()
    if (sid0) payload.session_id = sid0
    const res = await chatApi.sendUnifiedChat(payload)
    const reply = extractUnifiedChatReply(res)
    agentMessages.value.push({
      id: nextBrainAgentMsgId(),
      role: 'assistant',
      content: reply || '（空回复）'
    })
    const sid = extractSessionIdFromChatResponse(res)
    if (sid) {
      brainAgentSessionId.value = sid
      persistBrainAgentSessionId(sid)
    }
  } catch (err) {
    const msg = err instanceof ApiError ? err.message : err instanceof Error ? err.message : '请求失败'
    agentMessages.value.push({
      id: nextBrainAgentMsgId(),
      role: 'assistant',
      content: `错误：${msg}`
    })
    pushActivity(`Agent 对话失败：${msg.slice(0, 80)}`)
  } finally {
    agentSending.value = false
    await nextTick()
    scrollAgentConsoleToBottom()
  }
}

watch(
  () => [agentMessages.value.length, agentSending.value],
  () => {
    nextTick(() => scrollAgentConsoleToBottom())
  }
)

async function initBrainAgentSession() {
  const existing = readBrainAgentSessionId()
  if (existing) {
    brainAgentSessionId.value = existing
    return
  }
  try {
    const r = await chatApi.newConversation({})
    const sid = r?.data?.session_id
    if (sid && String(sid).trim()) {
      brainAgentSessionId.value = String(sid).trim()
      persistBrainAgentSessionId(brainAgentSessionId.value)
    }
  } catch {
    /* 无会话时仍允许发 unified_chat */
  }
}

function fillNewFromPreview() {
  if (codeLastPreview.value) {
    codeEditNewContent.value = codeLastPreview.value
    pushActivity('已将上次 analyze 预览写入 new_content')
  }
}

function readClientTier() {
  try {
    const dev = window.localStorage.getItem(XCAGI_AI_DEVELOPER_MODE_KEY) === '1'
    const tok = String(window.localStorage.getItem(XCAGI_AI_ELEVATED_TOKEN_KEY) || '').trim()
    return dev && tok ? 'p2' : 'p1'
  } catch {
    return 'p1'
  }
}

const clientTier = ref(readClientTier())

function pushActivity(msg) {
  const d = new Date()
  const ts = `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}:${String(d.getSeconds()).padStart(2, '0')}`
  activityLines.value = [{ ts, msg }, ...activityLines.value].slice(0, 12)
}

function onStorage(e) {
  if (!e.key || e.key === XCAGI_AI_DEVELOPER_MODE_KEY || e.key === XCAGI_AI_ELEVATED_TOKEN_KEY) {
    clientTier.value = readClientTier()
  }
}

function onWindowFocus() {
  const next = readClientTier()
  if (next !== clientTier.value) {
    clientTier.value = next
    pushActivity('已刷新本机 P1/P2 意图（自设置返回）')
  }
}

function onAiTierChanged() {
  const next = readClientTier()
  clientTier.value = next
  pushActivity(`本机意图已更新为 ${next.toUpperCase()}（设置已保存）`)
}

const openapiTitle = computed(() => {
  const s = openapiSpec.value
  if (!s || typeof s !== 'object') return ''
  const t = s.info && s.info.title
  return typeof t === 'string' && t.trim() ? t.trim() : 'OpenAPI'
})

const flatOperations = computed(() => {
  const spec = openapiSpec.value
  if (!spec || typeof spec !== 'object' || !spec.paths || typeof spec.paths !== 'object') {
    return []
  }
  const methods = ['get', 'post', 'put', 'patch', 'delete', 'options', 'head']
  const rows = []
  const pathKeys = Object.keys(spec.paths).sort((a, b) => a.localeCompare(b))
  for (const path of pathKeys) {
    const item = spec.paths[path]
    if (!item || typeof item !== 'object') continue
    for (const m of methods) {
      const op = item[m]
      if (!op || typeof op !== 'object') continue
      const summary =
        (typeof op.summary === 'string' && op.summary.trim()) ||
        (typeof op.operationId === 'string' && op.operationId.trim()) ||
        '—'
      rows.push({
        path,
        method: String(m).toUpperCase(),
        summary
      })
    }
  }
  return rows
})

const filteredOperations = computed(() => {
  const q = apiFilter.value.trim().toLowerCase()
  if (!q) return flatOperations.value
  return flatOperations.value.filter(
    (r) =>
      r.path.toLowerCase().includes(q) ||
      r.method.toLowerCase().includes(q) ||
      String(r.summary).toLowerCase().includes(q)
  )
})

const {
  paneStyle: brainPaneStyle,
  startResize: onBrainPaneResizeStart,
  resetSize: resetBrainPaneWidth,
  stopResize: stopBrainPaneResize,
} = useResizablePane({
  paneKey: 'brain.obs-panel',
  cssVarName: '--brain-obs-width',
  orientation: 'vertical',
  invertDelta: true,
  defaultSize: 320,
  minSize: 260,
  maxSize: 480,
  enabled: () => isBrainPaneResizable.value,
})

function onBrainPaneViewportChange(event) {
  isBrainPaneResizable.value = !event.matches
  if (!isBrainPaneResizable.value) {
    stopBrainPaneResize()
  }
}

async function loadTierStatus() {
  tierStatusLoading.value = true
  try {
    const res = await apiFetch('/api/fhd/ai-tier/status')
    if (!res.ok) {
      tierStatus.value = null
      return
    }
    tierStatus.value = await res.json()
  } catch {
    tierStatus.value = null
  } finally {
    tierStatusLoading.value = false
  }
}

async function probeCodeEditorStatus() {
  codeProbeLoading.value = true
  try {
    const res = await apiFetch('/api/code-editor/status')
    const txt = res.ok ? `code-editor/status → ${res.status}` : `code-editor/status HTTP ${res.status}`
    pushActivity(txt)
  } catch (e) {
    pushActivity(`code-editor/status 异常：${e instanceof Error ? e.message : '错误'}`)
  } finally {
    codeProbeLoading.value = false
  }
}

async function probeCodeEditorAnalyze() {
  codeProbeLoading.value = true
  try {
    const path = codeAnalyzePath.value.trim()
    const res = await apiFetch('/api/code-editor/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message: 'brain probe',
        ...(path ? { path } : {})
      })
    })
    let extra = ''
    try {
      const j = await res.clone().json()
      if (j && typeof j.kind === 'string') {
        extra = ` — ${j.kind}`
      } else if (j && typeof j.message === 'string') {
        extra = ` — ${j.message.slice(0, 80)}`
      }
      if (j && j.kind === 'text_preview' && typeof j.preview === 'string') {
        codeLastPreview.value = j.preview
        const snippet = j.preview.replace(/\s+/g, ' ').trim().slice(0, 60)
        if (snippet) {
          extra += ` · ${snippet}${j.preview.length > 60 ? '…' : ''}`
        }
      } else {
        codeLastPreview.value = ''
      }
    } catch {
      /* ignore */
    }
    pushActivity(`code-editor/analyze → ${res.status}${extra}`)
  } catch (e) {
    pushActivity(`code-editor/analyze 异常：${e instanceof Error ? e.message : '错误'}`)
  } finally {
    codeProbeLoading.value = false
  }
}

async function probeCodeEditorDraft() {
  const path = codeAnalyzePath.value.trim()
  const instruction = codeDraftInstruction.value.trim()
  if (!path || !instruction) {
    pushActivity('POST /draft 需要 path 与 instruction')
    return
  }
  codeProbeLoading.value = true
  try {
    const payload = { path, instruction }
    if (codeCreateIfMissing.value) {
      payload.create_if_missing = true
    }
    const res = await apiFetch('/api/code-editor/draft', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    })
    let extra = ''
    try {
      const j = await res.clone().json()
      if (res.ok && j && j.success === true && typeof j.proposed_new_content === 'string') {
        codeEditNewContent.value = j.proposed_new_content
        extra = ' — 已填入 new_content'
        if (j.context_truncated) {
          extra += '（模型侧上下文已截断）'
        }
      } else if (j && typeof j.message === 'string') {
        extra = ` — ${j.message.slice(0, 120)}`
      }
    } catch {
      /* ignore */
    }
    if (res.status === 403) {
      extra += ' — 需 P2'
    }
    if (res.status === 503 || res.status === 502) {
      extra += ' — 检查 LLM 配置'
    }
    pushActivity(`code-editor/draft → ${res.status}${extra}`)
  } catch (e) {
    pushActivity(`code-editor/draft 异常：${e instanceof Error ? e.message : '错误'}`)
  } finally {
    codeProbeLoading.value = false
  }
}

async function probeCodeEditorEdit() {
  const path = codeAnalyzePath.value.trim()
  if (!path) {
    pushActivity('POST /edit 需要 path')
    return
  }
  const newContent = codeEditNewContent.value
  if (!newContent) {
    pushActivity('POST /edit 需要 new_content')
    return
  }
  codeProbeLoading.value = true
  try {
    const body = { path, new_content: newContent }
    if (codeCreateIfMissing.value) {
      body.create_if_missing = true
    }
    const res = await apiFetch('/api/code-editor/edit', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    })
    let extra = ''
    try {
      const j = await res.clone().json()
      if (j && j.edit_id) {
        lastEditId.value = String(j.edit_id)
        extra = ` — edit_id=${lastEditId.value.slice(0, 12)}…`
        if (j.is_new_file) {
          extra += ', new_file'
        }
      }
    } catch {
      /* ignore */
    }
    pushActivity(`code-editor/edit → ${res.status}${extra}`)
  } catch (e) {
    pushActivity(`code-editor/edit 异常：${e instanceof Error ? e.message : '错误'}`)
  } finally {
    codeProbeLoading.value = false
  }
}

async function probeCodeEditorDiff() {
  const id = lastEditId.value.trim()
  if (!id) return
  codeProbeLoading.value = true
  try {
    const res = await apiFetch(`/api/code-editor/diff/${encodeURIComponent(id)}`)
    let extra = ''
    try {
      const j = await res.clone().json()
      if (j && typeof j.unified_diff === 'string') {
        const n = j.unified_diff.split('\n').length
        extra = ` — ${n} 行 diff`
      }
    } catch {
      /* ignore */
    }
    pushActivity(`code-editor/diff → ${res.status}${extra}`)
  } catch (e) {
    pushActivity(`code-editor/diff 异常：${e instanceof Error ? e.message : '错误'}`)
  } finally {
    codeProbeLoading.value = false
  }
}

async function probeCodeEditorApply() {
  const id = lastEditId.value.trim()
  if (!id) return
  codeProbeLoading.value = true
  try {
    const res = await apiFetch(`/api/code-editor/apply/${encodeURIComponent(id)}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({})
    })
    let extra = ''
    if (res.ok) {
      lastEditId.value = ''
      extra = ' — 已写盘，edit_id 已失效'
    } else if (res.status === 403) {
      extra = ' — 需 P2（设置里开发者模式 + 与服务器一致的口令）'
    } else if (res.status === 409) {
      extra = ' — 磁盘文件在提案后已变，请重新 POST /edit'
    }
    pushActivity(`code-editor/apply → ${res.status}${extra}`)
  } catch (e) {
    pushActivity(`code-editor/apply 异常：${e instanceof Error ? e.message : '错误'}`)
  } finally {
    codeProbeLoading.value = false
  }
}

async function loadPublicModels() {
  modelsLoading.value = true
  modelsError.value = ''
  publicModels.value = []
  try {
    const res = await apiFetch('/api/fhd/ai/models')
    if (!res.ok) {
      modelsError.value = `HTTP ${res.status}`
      pushActivity(`模型列表加载失败 HTTP ${res.status}`)
      return
    }
    const data = await res.json()
    const rows = Array.isArray(data?.models) ? data.models : []
    publicModels.value = rows
      .map((row) => ({
        id: String(row?.id || row?.model_id || '').trim(),
        provider: String(row?.provider || '—').trim() || '—',
        label: String(row?.label || row?.id || '').trim() || '—'
      }))
      .filter((r) => r.id)
    pushActivity(`模型元数据 ${publicModels.value.length} 条`)
  } catch (e) {
    modelsError.value = e instanceof Error ? e.message : '请求失败'
    pushActivity('模型列表请求异常')
  } finally {
    modelsLoading.value = false
  }
}

async function loadOpenapi() {
  openapiLoading.value = true
  openapiError.value = ''
  try {
    const res = await apiFetch('/api/system/openapi')
    if (!res.ok) {
      openapiError.value = `加载失败（HTTP ${res.status}）`
      openapiSpec.value = null
      pushActivity(`OpenAPI 加载失败 HTTP ${res.status}`)
      return
    }
    const data = await res.json()
    if (!data || typeof data !== 'object' || typeof data.paths !== 'object') {
      openapiError.value = '返回体不是有效的 OpenAPI JSON'
      openapiSpec.value = null
      pushActivity('OpenAPI 返回格式无效')
      return
    }
    openapiSpec.value = data
    const pathCount = Object.keys(data.paths || {}).length
    pushActivity(`OpenAPI 已加载（paths ${pathCount}）`)
    const now = new Date()
    openapiLoadedAt.value = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')} ${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`
  } catch (e) {
    openapiError.value =
      e instanceof Error ? e.message : '网络错误，无法拉取 OpenAPI'
    openapiSpec.value = null
    pushActivity('OpenAPI 请求异常')
  } finally {
    openapiLoading.value = false
  }
}

onMounted(() => {
  void initBrainAgentSession()
  activityLines.value = []
  pushActivity('智脑控制台已就绪')
  brainPaneViewportMedia = window.matchMedia(BRAIN_LAYOUT_MQ)
  onBrainPaneViewportChange(brainPaneViewportMedia)
  if (typeof brainPaneViewportMedia.addEventListener === 'function') {
    brainPaneViewportMedia.addEventListener('change', onBrainPaneViewportChange)
  } else if (typeof brainPaneViewportMedia.addListener === 'function') {
    brainPaneViewportMedia.addListener(onBrainPaneViewportChange)
  }
  window.addEventListener('storage', onStorage)
  window.addEventListener('focus', onWindowFocus)
  window.addEventListener(XCAGI_AI_TIER_CHANGED_EVENT, onAiTierChanged)
  loadTierStatus().then(() => {
    if (tierStatus.value) {
      pushActivity('已同步 /api/fhd/ai-tier/status')
    }
  })
  loadPublicModels()
  loadOpenapi()
})

onUnmounted(() => {
  stopBrainPaneResize()
  if (brainPaneViewportMedia) {
    if (typeof brainPaneViewportMedia.removeEventListener === 'function') {
      brainPaneViewportMedia.removeEventListener('change', onBrainPaneViewportChange)
    } else if (typeof brainPaneViewportMedia.removeListener === 'function') {
      brainPaneViewportMedia.removeListener(onBrainPaneViewportChange)
    }
  }
  window.removeEventListener('storage', onStorage)
  window.removeEventListener('focus', onWindowFocus)
  window.removeEventListener(XCAGI_AI_TIER_CHANGED_EVENT, onAiTierChanged)
})
</script>

<style scoped>
.brain-page {
  max-width: 1280px;
}

.brain-agent-header {
  margin-bottom: 12px;
}

.brain-agent-title-row {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.brain-agent-badge {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  padding: 4px 8px;
  border-radius: 6px;
  background: linear-gradient(135deg, #312e81 0%, #4f46e5 100%);
  color: #eef2ff;
}

.brain-sub {
  margin-top: 6px;
  margin-bottom: 0;
}

.brain-status-bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 14px;
  margin-bottom: 16px;
  border-radius: 10px;
  border: 1px solid #e2e8f0;
  background: linear-gradient(180deg, #f8fafc 0%, #f1f5f9 100%);
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
}

.brain-status-chips {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}

.brain-chip {
  display: inline-flex;
  align-items: center;
  font-size: 12px;
  padding: 4px 10px;
  border-radius: 999px;
  border: 1px solid #cbd5e1;
  background: #fff;
  color: #334155;
}

.brain-chip--p1 {
  border-color: #93c5fd;
  background: #eff6ff;
  color: #1e3a8a;
}

.brain-chip--p2 {
  border-color: #a78bfa;
  background: #f5f3ff;
  color: #5b21b6;
}

.brain-chip--muted {
  border-color: #e2e8f0;
  color: #64748b;
}

.brain-chip--warn {
  border-color: #fcd34d;
  background: #fffbeb;
  color: #92400e;
}

.brain-status-actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px;
  font-size: 12px;
}

.brain-status-meta {
  color: #64748b;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace;
}

.brain-link-settings {
  color: #4f46e5;
  font-weight: 600;
  text-decoration: none;
}

.brain-link-settings:hover {
  text-decoration: underline;
}

/* —— Agent 控制台（Claude Code 式深色对话壳） —— */
.brain-agent-console {
  display: flex;
  flex-direction: column;
  margin-bottom: 20px;
  min-height: min(52vh, 440px);
  max-height: min(58vh, 520px);
  border-radius: 12px;
  border: 1px solid #27272f;
  background: linear-gradient(165deg, #16161d 0%, #12121a 100%);
  box-shadow:
    0 0 0 1px rgba(255, 255, 255, 0.04) inset,
    0 12px 40px rgba(0, 0, 0, 0.35);
  overflow: hidden;
  color: #e4e4e7;
}

.brain-agent-console__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 14px;
  border-bottom: 1px solid #27272f;
  background: rgba(0, 0, 0, 0.25);
}

.brain-agent-console__title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: #fafafa;
}

.brain-agent-console__dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #22c55e;
  box-shadow: 0 0 10px rgba(34, 197, 94, 0.6);
}

.brain-agent-console__sub {
  font-size: 11px;
  font-weight: 500;
  text-transform: none;
  letter-spacing: 0;
  color: #71717a;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace;
}

.brain-agent-console__actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.brain-agent-console__session-id {
  font-size: 11px;
  color: #52525b;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace;
  max-width: 140px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.brain-agent-console__btn {
  padding: 5px 10px;
  font-size: 12px;
  border-radius: 6px;
  border: 1px solid #3f3f46;
  background: #27272a;
  color: #d4d4d8;
  cursor: pointer;
}

.brain-agent-console__btn:hover:not(:disabled) {
  border-color: #52525b;
  color: #fafafa;
}

.brain-agent-console__btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.brain-agent-console__messages {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 14px 14px 8px;
  scroll-behavior: smooth;
}

.brain-agent-console__empty {
  font-size: 13px;
  line-height: 1.55;
  color: #a1a1aa;
  padding: 8px 4px 16px;
}

.brain-agent-msg {
  margin-bottom: 14px;
  max-width: 100%;
}

.brain-agent-msg__role {
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: #71717a;
  margin-bottom: 4px;
}

.brain-agent-msg__body {
  margin: 0;
  padding: 10px 12px;
  border-radius: 10px;
  font-size: 13px;
  line-height: 1.55;
  white-space: pre-wrap;
  word-break: break-word;
  font-family: ui-sans-serif, system-ui, -apple-system, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
}

.brain-agent-msg--user .brain-agent-msg__body {
  background: #27272a;
  border: 1px solid #3f3f46;
  color: #f4f4f5;
}

.brain-agent-msg--assistant .brain-agent-msg__body {
  background: #18181b;
  border: 1px solid #3f3f46;
  color: #e4e4e7;
}

.brain-agent-msg--pending .brain-agent-msg__body {
  color: #a1a1aa;
  font-style: italic;
}

.brain-agent-msg__typing {
  white-space: normal;
}

.brain-agent-console__composer {
  flex-shrink: 0;
  padding: 10px 12px 12px;
  border-top: 1px solid #27272f;
  background: rgba(0, 0, 0, 0.35);
}

.brain-agent-console__input {
  width: 100%;
  box-sizing: border-box;
  resize: vertical;
  min-height: 72px;
  max-height: 200px;
  padding: 10px 12px;
  border-radius: 8px;
  border: 1px solid #3f3f46;
  background: #09090b;
  color: #fafafa;
  font-size: 13px;
  line-height: 1.5;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace;
}

.brain-agent-console__input::placeholder {
  color: #52525b;
}

.brain-agent-console__input:focus {
  outline: none;
  border-color: #6366f1;
  box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.25);
}

.brain-agent-console__composer-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-top: 8px;
}

.brain-agent-console__hint {
  font-size: 11px;
  color: #71717a !important;
}

.brain-agent-console__send {
  flex-shrink: 0;
}

.brain-layout {
  display: flex;
  gap: 20px;
  align-items: stretch;
  --brain-obs-width: 320px;
}

@media (max-width: 960px) {
  .brain-layout {
    flex-direction: column;
  }
}

.brain-main {
  position: relative;
  flex: 1 1 auto;
  min-width: 0;
}

.brain-obs {
  flex: 0 0 var(--brain-obs-width);
  width: var(--brain-obs-width);
  min-width: 0;
  padding: 14px 16px;
  border-radius: 10px;
  border: 1px solid #e2e8f0;
  background: #fff;
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.06);
}

@media (max-width: 960px) {
  .brain-obs {
    order: -1;
    width: 100%;
  }
}

.brain-obs-section {
  margin-bottom: 12px;
}

.brain-obs-title {
  font-size: 13px;
  font-weight: 700;
  color: #0f172a;
  margin-bottom: 6px;
  letter-spacing: 0.02em;
}

.brain-obs-hint {
  font-size: 12px;
  margin: 0 0 10px;
}

.brain-activity-log {
  list-style: none;
  margin: 0;
  padding: 0;
  max-height: 220px;
  overflow: auto;
  border: 1px solid #f1f5f9;
  border-radius: 8px;
  background: #fafafa;
}

.brain-activity-log__item {
  display: flex;
  gap: 8px;
  padding: 8px 10px;
  font-size: 12px;
  border-bottom: 1px solid #f1f5f9;
}

.brain-activity-log__item:last-child {
  border-bottom: none;
}

.brain-activity-log__ts {
  flex: 0 0 auto;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace;
  color: #94a3b8;
}

.brain-activity-log__msg {
  color: #334155;
  word-break: break-word;
}

.brain-obs-details {
  margin-top: 4px;
}

.brain-obs-models {
  margin-top: 12px;
}

.brain-models-hint {
  font-size: 12px;
  margin: 6px 0 0;
}

.brain-models-list {
  list-style: none;
  margin: 8px 0 0;
  padding: 0;
  max-height: 200px;
  overflow: auto;
}

.brain-models-item {
  padding: 8px 0;
  border-bottom: 1px solid #f1f5f9;
  font-size: 12px;
}

.brain-models-item:last-child {
  border-bottom: none;
}

.brain-models-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.brain-models-id {
  font-size: 11px;
  color: #1e293b;
}

.brain-models-chip {
  font-size: 10px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  padding: 2px 6px;
  border-radius: 4px;
  background: #f1f5f9;
  color: #475569;
}

.brain-models-label {
  margin-top: 4px;
  color: #64748b;
  line-height: 1.35;
}

.brain-details {
  margin-top: 12px;
}

.brain-details summary {
  cursor: pointer;
  font-weight: 600;
  font-size: 13px;
  color: #475569;
}

.brain-panel {
  margin-bottom: 0;
}

.brain-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 16px;
}

.brain-tab {
  padding: 8px 16px;
  border-radius: 8px;
  border: 1px solid #d1d5db;
  background: #fff;
  cursor: pointer;
  font-size: 14px;
}

.brain-tab.active {
  border-color: #6366f1;
  background: #eef2ff;
  font-weight: 600;
  color: #3730a3;
}

.brain-card {
  margin-bottom: 16px;
}

.brain-list {
  margin: 8px 0 0 1.2rem;
  line-height: 1.6;
}

.brain-diagram {
  margin: 12px 0 0;
  padding: 12px;
  font-size: 11px;
  line-height: 1.35;
  overflow: auto;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  white-space: pre;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace;
}

.brain-diagram--compact {
  font-size: 10px;
  max-height: 200px;
}

.brain-search {
  margin-top: 12px;
}

.brain-input-mono {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace;
}

.brain-mono {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace;
}

.brain-count {
  margin: 8px 0 10px;
}

.brain-table-wrap {
  overflow: auto;
  max-height: min(60vh, 520px);
  border: 1px solid #e5e7eb;
  border-radius: 8px;
}

.brain-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.brain-table th,
.brain-table td {
  padding: 8px 10px;
  text-align: left;
  border-bottom: 1px solid #e5e7eb;
  vertical-align: top;
}

.brain-table th {
  background: #f9fafb;
  font-weight: 600;
  position: sticky;
  top: 0;
  z-index: 1;
}

.brain-table tbody tr:hover {
  background: #fafafa;
}

.brain-method-chip {
  display: inline-block;
  font-size: 11px;
  font-weight: 700;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace;
  padding: 2px 8px;
  border-radius: 6px;
  border: 1px solid #e5e7eb;
  background: #fff;
  color: #475569;
}

.brain-method-chip--get {
  border-color: #86efac;
  background: #f0fdf4;
  color: #14532d;
}

.brain-method-chip--post {
  border-color: #93c5fd;
  background: #eff6ff;
  color: #1e3a8a;
}

.brain-method-chip--put,
.brain-method-chip--patch {
  border-color: #fcd34d;
  background: #fffbeb;
  color: #92400e;
}

.brain-method-chip--delete {
  border-color: #fca5a5;
  background: #fef2f2;
  color: #991b1b;
}

.brain-skill-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 12px;
  margin-top: 12px;
}

.brain-skill-card {
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 12px 14px;
  background: #fff;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}

.brain-skill-card:hover {
  border-color: #c7d2fe;
  box-shadow: 0 2px 8px rgba(79, 70, 229, 0.08);
}

.brain-skill-card__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 8px;
}

.brain-skill-card__id {
  font-size: 12px;
  color: #4338ca;
  word-break: break-all;
}

.brain-skill-card__status {
  font-size: 11px;
  color: #64748b;
  white-space: nowrap;
}

.brain-skill-card__desc {
  margin: 0;
  font-size: 13px;
  line-height: 1.5;
  color: #475569;
}

.brain-code-editor-stub {
  margin-top: 20px;
  padding-top: 16px;
  border-top: 1px dashed #e2e8f0;
}

.brain-stub-check {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 10px;
  font-size: 12px;
  cursor: pointer;
}

.brain-stub-check input {
  margin: 0;
}

.brain-stub-path {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-top: 10px;
  font-size: 12px;
}

.brain-stub-path__input {
  width: 100%;
  box-sizing: border-box;
  padding: 6px 10px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  font-size: 13px;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace;
  color: #0f172a;
  background: #fff;
}

.brain-stub-path__input:focus {
  outline: none;
  border-color: #818cf8;
  box-shadow: 0 0 0 2px rgba(129, 140, 248, 0.2);
}

.brain-stub-textarea {
  width: 100%;
  box-sizing: border-box;
  margin-top: 4px;
  padding: 8px 10px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  font-size: 12px;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace;
  color: #0f172a;
  background: #fff;
  resize: vertical;
  min-height: 72px;
}

.brain-stub-textarea:focus {
  outline: none;
  border-color: #818cf8;
  box-shadow: 0 0 0 2px rgba(129, 140, 248, 0.2);
}

.brain-stub-textarea--sm {
  min-height: 52px;
}

.brain-stub-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 8px;
}

.brain-stub-actions--wrap {
  margin-top: 6px;
}

.brain-stub-editid {
  margin-top: 8px;
  font-size: 12px;
  word-break: break-all;
}

.brain-future {
  margin-top: 16px;
  font-size: 12px;
}

.text-warn {
  color: #b45309;
}
</style>
