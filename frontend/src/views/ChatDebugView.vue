<template>
  <div class="page-view chat-debug-view" id="view-chat-debug">
    <div class="page-content">
      <div class="page-header">
        <h2>聊天调试工作台</h2>
        <p class="muted">测试普通版/专业版的意图和流程分支。此页只做本地模拟，不调用真实工具。</p>
      </div>

      <div class="card">
        <div class="card-header">输入与模式</div>
        <div class="form-group">
          <label>快速测试样例</label>
          <div class="preset-row">
            <button
              v-for="item in presetCases"
              :key="item.label"
              type="button"
              class="preset-btn"
              @click="applyPreset(item.text)"
            >
              {{ item.label }}
            </button>
          </div>
        </div>
        <div class="form-group">
          <label>模式</label>
          <div class="mode-switch">
            <button
              type="button"
              class="btn"
              :class="mode === 'normal' ? 'btn-primary' : 'btn-secondary'"
              @click="mode = 'normal'"
            >
              普通版
            </button>
            <button
              type="button"
              class="btn"
              :class="mode === 'pro' ? 'btn-primary' : 'btn-secondary'"
              @click="mode = 'pro'"
            >
              专业版
            </button>
          </div>
        </div>
        <div class="form-group">
          <label>测试输入</label>
          <textarea
            v-model="inputText"
            rows="3"
            placeholder="例如：给成都客户生成并打印今天发货单"
          ></textarea>
        </div>
        <div class="action-row">
          <button class="btn btn-primary" @click="runSimulation">单模式模拟</button>
          <button class="btn btn-secondary" @click="runCompareSimulation">双模式对比</button>
          <button class="btn btn-success" @click="addToTestPack">加入测试包</button>
          <button class="btn btn-secondary" @click="resetResult">清空</button>
        </div>
      </div>

      <div class="card">
        <div class="card-header">意图测试包</div>
        <div class="action-row" style="margin-bottom:10px;">
          <button class="btn btn-primary btn-sm" @click="exportTestPackJson" :disabled="!testPack.length">导出 JSON</button>
          <button class="btn btn-secondary btn-sm" @click="exportTestPackTxt" :disabled="!testPack.length">导出 TXT</button>
          <button class="btn btn-danger btn-sm" @click="clearTestPack" :disabled="!testPack.length">清空列表</button>
        </div>
        <div v-if="!testPack.length" class="muted">暂无测试句子，先在上方输入并点“加入测试包”。</div>
        <table v-else class="data-table test-pack-table">
          <thead>
            <tr>
              <th style="width:60px;">#</th>
              <th>测试句子</th>
              <th style="width:120px;">添加时间</th>
              <th style="width:170px;">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(item, idx) in testPack" :key="item.id">
              <td>{{ idx + 1 }}</td>
              <td>{{ item.text }}</td>
              <td>{{ item.timeLabel }}</td>
              <td>
                <div class="pack-actions">
                  <button class="btn btn-secondary btn-sm" @click="applyPreset(item.text)">回填</button>
                  <button class="btn btn-danger btn-sm" @click="removeTestCase(item.id)">删除</button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="card" v-if="result">
        <div class="card-header">当前模式结果</div>
        <div class="result-grid">
          <div class="result-item">
            <span class="result-label">模式</span>
            <span class="result-value">{{ result.modeLabel }}</span>
          </div>
          <div class="result-item">
            <span class="result-label">识别意图</span>
            <span class="result-value intent-pill">{{ result.intentLabel }}</span>
          </div>
          <div class="result-item">
            <span class="result-label">流程分支</span>
            <span class="result-value">{{ result.flow }}</span>
          </div>
          <div class="result-item">
            <span class="result-label">拟调用工具</span>
            <span class="result-value">{{ result.mockTools.join(' -> ') }}</span>
          </div>
        </div>
        <p><strong>模拟回复：</strong>{{ result.reply }}</p>
        <p class="muted"><strong>风险提示：</strong>{{ result.riskHint }}</p>
      </div>

      <div class="card" v-if="result && result.stages.length">
        <div class="card-header">流程阶段</div>
        <div class="stage-row">
          <div v-for="(s, idx) in result.stages" :key="`${s}-${idx}`" class="stage-chip">{{ s }}</div>
        </div>
      </div>

      <div class="card" v-if="result && result.steps.length">
        <div class="card-header">流程追踪</div>
        <ol class="steps">
          <li v-for="(step, idx) in result.steps" :key="idx">{{ step }}</li>
        </ol>
      </div>

      <div class="card" v-if="compareResult">
        <div class="card-header">普通版 vs 专业版</div>
        <table class="data-table">
          <thead>
            <tr>
              <th>维度</th>
              <th>普通版</th>
              <th>专业版</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>意图</td>
              <td>{{ compareResult.normal.intentLabel }}</td>
              <td>{{ compareResult.pro.intentLabel }}</td>
            </tr>
            <tr>
              <td>流程</td>
              <td>{{ compareResult.normal.flow }}</td>
              <td>{{ compareResult.pro.flow }}</td>
            </tr>
            <tr>
              <td>拟调用工具</td>
              <td>{{ compareResult.normal.mockTools.join(' -> ') }}</td>
              <td>{{ compareResult.pro.mockTools.join(' -> ') }}</td>
            </tr>
            <tr>
              <td>回复摘要</td>
              <td>{{ compareResult.normal.reply }}</td>
              <td>{{ compareResult.pro.reply }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref, watch } from 'vue';

const mode = ref('normal');
const inputText = ref('');
const result = ref(null);
const compareResult = ref(null);
const testPack = ref([]);
const TEST_PACK_STORAGE_KEY = 'xcagi_intent_test_pack_v1';

const presetCases = [
  { label: '产品查询', text: '查一下A001的价格' },
  { label: '客户查询', text: '有哪些客户？' },
  { label: '开单需求', text: '给成都客户生成今天发货单' },
  { label: '打印命令', text: '开始打印' },
  { label: '复合任务', text: '给成都客户生成并打印今天发货单' }
];

const INTENT_LABEL_MAP = {
  empty: '空输入',
  print: '打印',
  shipment_generate: '开单',
  shipment_and_print: '开单+打印',
  product_query: '产品查询',
  customer_query: '客户查询',
  general_chat: '通用问答'
};

function applyPreset(text) {
  inputText.value = text;
}

function formatTimeLabel(ts) {
  const d = new Date(ts);
  const pad = (n) => String(n).padStart(2, '0');
  return `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
}

function buildExportFileName(ext = 'json') {
  const d = new Date();
  const pad = (n) => String(n).padStart(2, '0');
  const stamp = `${d.getFullYear()}${pad(d.getMonth() + 1)}${pad(d.getDate())}-${pad(d.getHours())}${pad(d.getMinutes())}${pad(d.getSeconds())}`;
  return `intent-test-pack-${stamp}.${ext}`;
}

function triggerDownload(text, type, fileName) {
  const blob = new Blob([text], { type });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = fileName;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

function addToTestPack() {
  const text = String(inputText.value || '').trim();
  if (!text) {
    alert('请先输入测试句子');
    return;
  }
  const exists = testPack.value.some(item => item.text === text);
  if (exists) {
    alert('该句子已在测试包中');
    return;
  }
  const now = Date.now();
  testPack.value.push({
    id: `${now}-${Math.random().toString(36).slice(2, 8)}`,
    text,
    createdAt: now,
    timeLabel: formatTimeLabel(now)
  });
}

function removeTestCase(id) {
  testPack.value = testPack.value.filter(item => item.id !== id);
}

function clearTestPack() {
  if (!testPack.value.length) return;
  if (!window.confirm('确定清空测试包列表吗？')) return;
  testPack.value = [];
}

function exportTestPackJson() {
  if (!testPack.value.length) return;
  const payload = {
    name: '意图测试包',
    exported_at: new Date().toISOString(),
    total: testPack.value.length,
    cases: testPack.value.map((item, idx) => ({
      index: idx + 1,
      text: item.text,
      created_at: new Date(item.createdAt).toISOString()
    }))
  };
  triggerDownload(JSON.stringify(payload, null, 2), 'application/json;charset=utf-8', buildExportFileName('json'));
}

function exportTestPackTxt() {
  if (!testPack.value.length) return;
  const lines = [
    '# 意图测试包',
    `# 导出时间: ${new Date().toLocaleString('zh-CN')}`,
    `# 总数: ${testPack.value.length}`,
    ''
  ];
  testPack.value.forEach((item, idx) => {
    lines.push(`${idx + 1}. ${item.text}`);
  });
  triggerDownload(lines.join('\n'), 'text/plain;charset=utf-8', buildExportFileName('txt'));
}

function classifyIntent(message = '') {
  const text = String(message).trim();
  if (!text) return 'empty';

  const hasPrint = /打印|打标签/.test(text);
  const hasShipment = /生成|开单|发货单/.test(text);
  if (hasPrint && hasShipment) return 'shipment_and_print';
  if (hasPrint) return 'print';
  if (hasShipment) return 'shipment_generate';
  if (/查|查询|价格|型号/.test(text)) return 'product_query';
  if (/客户/.test(text)) return 'customer_query';
  return 'general_chat';
}

function buildSimulation(message = '', currentMode = 'normal') {
  const text = String(message || '').trim();
  const isPro = currentMode === 'pro';
  const intent = classifyIntent(text);

  if (!text) {
    return {
      modeLabel: isPro ? '专业版' : '普通版',
      intent,
      intentLabel: INTENT_LABEL_MAP.empty,
      flow: '输入校验',
      reply: '请输入测试内容后再执行模拟。',
      steps: ['收到空输入 -> 停止流程'],
      stages: ['输入校验'],
      mockTools: ['none'],
      riskHint: '空输入会直接终止流程，无法进入意图识别。'
    };
  }

  const steps = [
    `收到输入：${text}`,
    `模式判定：${isPro ? '专业版' : '普通版'}`,
    `意图识别：${INTENT_LABEL_MAP[intent] || INTENT_LABEL_MAP.general_chat}`
  ];

  let flow = '';
  let reply = '';
  let riskHint = '';
  let stages = ['输入', '意图识别'];
  let mockTools = ['intent-router'];

  if (isPro) {
    flow = 'professional-simulated';
    stages = [...stages, '任务编排', '运行态跟踪', '结果总结'];
    steps.push('进入专业版任务编排链路（模拟）');
    steps.push('构建多步骤执行计划（模拟）');
    steps.push('输出专业版运行态卡片（模拟）');

    if (intent === 'shipment_and_print') {
      reply = '识别为复合任务：将先开单再打印，展示可执行计划与状态追踪（模拟）。';
      mockTools = ['intent-router', 'planner', 'shipment-generate', 'print-dispatch'];
      riskHint = '复合指令里若缺失客户或时间条件，真实环境需二次确认参数。';
    } else if (intent === 'shipment_generate') {
      reply = '识别为开单任务：将生成待确认任务并提供执行状态（模拟）。';
      mockTools = ['intent-router', 'planner', 'shipment-generate'];
      riskHint = '若产品项不足，真实环境会提示补充明细。';
    } else if (intent === 'print') {
      reply = '识别为打印任务：将检查最近一次可打印上下文后执行打印（模拟）。';
      mockTools = ['intent-router', 'print-context', 'print-dispatch'];
      riskHint = '若无可打印上下文，真实环境会返回“暂无可打印任务”。';
    } else {
      reply = '识别为轻量任务：专业链路将生成简化计划并返回结果（模拟）。';
      mockTools = ['intent-router', 'planner'];
      riskHint = '专业版在轻量查询场景可能略慢于普通版。';
    }
  } else {
    flow = 'normal-simulated';
    stages = [...stages, '单步响应', '可选自动动作'];
    steps.push('进入普通版单步问答链路（模拟）');
    steps.push('生成单轮回复，不做多任务编排（模拟）');

    if (intent === 'shipment_and_print') {
      reply = '识别到复合意图，但普通版会拆解为单步处理并提示分步执行（模拟）。';
      mockTools = ['intent-router', 'single-step-suggestion'];
      riskHint = '普通版无法完整编排多步骤任务，建议切换专业版。';
    } else if (intent === 'shipment_generate') {
      reply = '识别为开单需求：将返回待确认任务卡片（模拟）。';
      mockTools = ['intent-router', 'task-preview'];
      riskHint = '订单号和产品明细在真实流程中仍需确认。';
    } else if (intent === 'print') {
      reply = '识别为打印需求：将检查最近上下文并执行打印动作（模拟）。';
      mockTools = ['intent-router', 'print-context'];
      riskHint = '若未先生成发货单，打印会失败。';
    } else if (intent === 'product_query') {
      reply = '识别为产品查询：可返回查询结果并触发副窗操作（模拟）。';
      mockTools = ['intent-router', 'products-float'];
      riskHint = '关键字过短时可能命中多个产品。';
    } else {
      reply = '识别为通用请求：走基础问答与单次动作判断（模拟）。';
      mockTools = ['intent-router'];
      riskHint = '通用语义过于抽象时，可能需要追问澄清。';
    }
  }

  return {
    modeLabel: isPro ? '专业版' : '普通版',
    intent,
    intentLabel: INTENT_LABEL_MAP[intent] || INTENT_LABEL_MAP.general_chat,
    flow,
    reply,
    steps,
    stages,
    mockTools,
    riskHint
  };
}

function runSimulation() {
  result.value = buildSimulation(inputText.value, mode.value);
  compareResult.value = null;
}

function runCompareSimulation() {
  const normal = buildSimulation(inputText.value, 'normal');
  const pro = buildSimulation(inputText.value, 'pro');
  compareResult.value = { normal, pro };
  result.value = mode.value === 'pro' ? pro : normal;
}

function resetResult() {
  inputText.value = '';
  result.value = null;
  compareResult.value = null;
}

onMounted(() => {
  try {
    const raw = localStorage.getItem(TEST_PACK_STORAGE_KEY);
    if (!raw) return;
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return;
    testPack.value = parsed
      .map(item => {
        const text = String(item?.text || '').trim();
        const createdAt = Number(item?.createdAt || Date.now());
        if (!text) return null;
        return {
          id: String(item?.id || `${createdAt}-${Math.random().toString(36).slice(2, 8)}`),
          text,
          createdAt,
          timeLabel: formatTimeLabel(createdAt)
        };
      })
      .filter(Boolean);
  } catch (_e) {}
});

watch(testPack, (val) => {
  try {
    localStorage.setItem(TEST_PACK_STORAGE_KEY, JSON.stringify(val));
  } catch (_e) {}
}, { deep: true });
</script>

<style scoped>
.chat-debug-view .page-header p {
  margin-top: 8px;
}

.preset-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.preset-btn {
  border: 1px solid rgba(79, 172, 254, 0.35);
  color: #2563eb;
  background: rgba(79, 172, 254, 0.08);
  border-radius: 16px;
  padding: 4px 10px;
  font-size: 12px;
  cursor: pointer;
}

.preset-btn:hover {
  background: rgba(79, 172, 254, 0.15);
}

.mode-switch {
  display: flex;
  gap: 8px;
}

.action-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.test-pack-table td {
  vertical-align: middle;
}

.pack-actions {
  display: flex;
  gap: 6px;
}

.result-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 8px;
  margin-bottom: 8px;
}

.result-item {
  background: rgba(148, 163, 184, 0.08);
  border-radius: 8px;
  padding: 8px 10px;
}

.result-label {
  display: block;
  color: #64748b;
  font-size: 12px;
}

.result-value {
  display: block;
  margin-top: 4px;
  color: #0f172a;
  font-size: 13px;
}

.intent-pill {
  color: #1d4ed8;
  font-weight: 600;
}

.stage-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.stage-chip {
  padding: 4px 10px;
  border-radius: 16px;
  background: rgba(34, 197, 94, 0.12);
  color: #166534;
  font-size: 12px;
}

.steps {
  margin: 0;
  padding-left: 18px;
}

.steps li {
  margin-bottom: 6px;
}
</style>
