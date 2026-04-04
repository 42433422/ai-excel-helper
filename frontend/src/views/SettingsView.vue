<template>
  <div class="page-view" id="view-settings">
    <div class="page-content">
      <div class="page-header">
        <h2>系统设置</h2>
      </div>

      <div class="card">
        <div class="card-header">行业配置</div>
        <div class="form-group">
          <label>当前行业</label>
          <select v-model="currentIndustry" @change="onIndustryChange">
            <option v-for="ind in industries" :key="ind.id" :value="ind.id">
              {{ ind.name }}
            </option>
          </select>
        </div>
        <p class="muted" style="margin-top:8px;">
          切换行业将影响 AI 意图识别和业务字段配置。
          当前行业主单位：<strong>{{ currentIndustryUnit }}</strong>
        </p>
      </div>

      <div class="card">
        <div class="card-header">AI 意图包</div>
        <p class="muted" style="margin-bottom:15px;">
          针对不同行业优化的 AI 意图识别配置包。开启后将增强对特定行业用语的理解。
        </p>

        <div v-if="loadingPackages" class="muted">加载中...</div>
        <div v-else-if="!currentIndustryConfig" class="muted">请先选择行业</div>
        <div v-else>
          <div class="intent-packages">
            <div
              v-for="(pkg, key) in intentPackages"
              :key="key"
              class="intent-package-item"
              :class="{ active: pkg.enabled }"
            >
              <div class="pkg-header">
                <div class="pkg-info">
                  <span class="pkg-icon" aria-hidden="true">
                    <i class="fa" :class="pkg.iconClass"></i>
                  </span>
                  <span class="pkg-name">{{ pkg.name }}</span>
                </div>
                <label class="toggle-switch">
                  <input type="checkbox" v-model="pkg.enabled" @change="togglePackage(key)">
                  <span class="toggle-slider"></span>
                </label>
              </div>
              <p class="pkg-desc">{{ pkg.description }}</p>
              <div class="pkg-keywords" v-if="pkg.enabled">
                <span class="keyword" v-for="kw in pkg.keywords.slice(0, 8)" :key="kw">{{ kw }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="card">
        <div class="card-header">基本设置</div>
        <div class="form-group">
          <label>侧栏样式</label>
          <select v-model="sidebarThemePreset" @change="onSidebarThemeChange">
            <option v-for="theme in SIDEBAR_THEME_OPTIONS" :key="theme.value" :value="theme.value">
              {{ theme.label }}
            </option>
          </select>
          <p class="muted" style="margin-top:8px;">
            控制左侧栏整块配色（顶栏、菜单、底栏）。选「Office」为浅色侧栏（白底菜单，与顶栏一致）；其余预设为整栏深色。当前强调色：
            <span class="theme-color-chip" :style="{ backgroundColor: selectedSidebarAccent }"></span>
            <strong>{{ selectedSidebarAccent }}</strong>
          </p>
        </div>
        <div class="form-group">
          <label>助手名称</label>
          <input
            v-model="assistantName"
            type="text"
            maxlength="24"
            placeholder="例如：修茈"
          >
          <p class="muted" style="margin-top:8px;">
            用于专业模式中的助手头部显示，如“{{ normalizedAssistantName }} ASSISTANT”。
          </p>
        </div>
        <div class="form-group">
          <label>系统名称</label>
          <input type="text" value="AI-Excel Helper 出货单管理系统" disabled>
        </div>
        <div class="form-group">
          <label>数据库路径</label>
          <input type="text" :value="currentDbPath" disabled>
        </div>
        <div class="form-group mod-ui-off-row">
          <div class="mod-ui-off-head">
            <div>
              <label class="mod-ui-off-label">原版模式（前端完全关闭 Mod）</label>
              <p class="muted mod-ui-off-desc">
                勾选后本浏览器为<strong>纯原版</strong>：不请求 <code>/api/mods</code>、不注册 Mod 路由与代码分包、不轮询
                <code>/api/mod/*</code>；侧栏、副窗、任务面板均无 Mod 痕迹（本地工作流开关中的扩展项也会清掉）。
                与后端是否仍加载插件、以及环境变量 <code>XCAGI_DISABLE_MODS</code> 无关。切换后<strong>自动刷新页面</strong>生效。
              </p>
            </div>
            <label class="toggle-switch mod-ui-off-toggle" title="原版模式：浏览器端完全不加载 Mod">
              <input type="checkbox" :checked="clientModsUiOff" @change="onClientModsUiOffChange" />
              <span class="toggle-slider"></span>
            </label>
          </div>
        </div>
        <div class="form-group">
          <label>AI 模式</label>
          <select v-model="aiMode">
            <option value="online">在线模式（DeepSeek）</option>
            <option value="offline">离线模式（本地）</option>
          </select>
          <p class="muted" style="margin-top:8px;">
            离线模式不调用云端 AI，适合网络不稳定场景；复杂开放问答建议切回在线模式。
          </p>
        </div>
        <button class="btn btn-primary" @click="saveSettings" :disabled="loading">保存设置</button>
      </div>

      <div class="card">
        <div class="card-header">导航自定义</div>
        <div class="form-group">
          <label style="display:flex;align-items:center;justify-content:space-between;gap:12px;">
            <span>启用自定义排列</span>
            <label class="toggle-switch">
              <input type="checkbox" :checked="sidebarLayoutStore.reorderEnabled" @change="toggleSidebarReorder">
              <span class="toggle-slider"></span>
            </label>
          </label>
          <p class="muted" style="margin-top:8px;">
            开启后可在左侧菜单长按约 0.3 秒拖动卡片，调整排序位置。
          </p>
          <button class="btn btn-secondary btn-sm" @click="resetSidebarOrder" :disabled="!sidebarLayoutStore.hasCustomOrder">
            恢复默认顺序
          </button>
        </div>
      </div>

      <div class="card">
        <div class="card-header">测试数据库</div>
        <div class="form-group">
          <div class="mod-ui-off-head">
            <div>
              <label class="mod-ui-off-label">启用测试模式</label>
              <p class="muted mod-ui-off-desc">
                开启后使用空白测试数据库 <code>products_test.db</code>，真实数据库不受影响。
                关闭时测试数据库会被重置为空，可重复使用。
              </p>
            </div>
            <label class="toggle-switch mod-ui-off-toggle" title="测试数据库模式">
              <input type="checkbox" v-model="testDbEnabled" @click="onTestDbToggle" :disabled="loadingTestDb" />
              <span class="toggle-slider"></span>
            </label>
          </div>
        </div>
        <p class="muted" style="margin-top:8px;">
          当前数据库：<strong :class="{ 'text-warning': testDbEnabled }">{{ testDbEnabled ? 'products_test.db (测试)' : 'products.db (真实)' }}</strong>
        </p>
        <p v-if="loadingTestDb" class="muted">处理中...</p>
        <p v-if="testDbMessage" :class="['muted', testDbMessageClass]" style="margin-top:4px;">{{ testDbMessage }}</p>
      </div>

      <div class="card">
        <div class="card-header">蒸馏模型版本 <small style="opacity:0.8">专业版对话会参与蒸馏，此处可查看训练产物</small></div>
        <div>
          <p v-if="loadingVersions" class="muted">加载中...</p>
          <p v-else-if="versionsError" class="muted">{{ versionsError }}</p>
          <p v-else-if="versions.length === 0" class="muted">暂无训练产物</p>
          <table v-else class="data-table">
            <thead>
              <tr><th>文件</th><th>说明</th><th>修改时间</th><th>大小</th></tr>
            </thead>
            <tbody>
              <tr v-for="v in versions" :key="v.name">
                <td>{{ v.name }}</td>
                <td>{{ v.label }}</td>
                <td>{{ v.modified || '-' }}</td>
                <td>{{ v.size_kb != null ? `${v.size_kb} KB` : '-' }}</td>
              </tr>
            </tbody>
          </table>
          <p class="muted" style="margin-top:8px;">已积累蒸馏样本数：{{ sampleCount }}</p>
          <p v-if="sampleCountWarning" class="muted" style="margin-top:4px;">{{ sampleCountWarning }}</p>
        </div>
      </div>

      <div class="card">
        <div class="card-header about-debug-entry" @click="handleAboutHeaderClick">关于</div>
        <p>AI-Excel Helper 出货单智能处理系统</p>
        <p>版本: 1.0.4</p>
        <p class="muted" style="margin-top:8px;">连点“关于”5下可进入调试页面（仅本地流程模拟，不调用真实工具）</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, onBeforeUnmount, ref, computed } from 'vue';
import { useRouter } from 'vue-router';
import { storeToRefs } from 'pinia';
import api from '../api';
import { systemApi } from '../api/system';
import { intentPackagesApi } from '../api/intentPackages';
import { useIndustryStore } from '../stores/industry';
import { useSidebarLayoutStore } from '../stores/sidebarLayout';
import {
  SIDEBAR_THEME_OPTIONS,
  readStoredSidebarTheme,
  persistSidebarTheme,
  applySidebarTheme,
} from '@/utils/sidebarTheme';
import { useModsStore } from '@/stores/mods';
import { useWorkflowAiEmployeesStore } from '@/stores/workflowAiEmployees';

const industryStore = useIndustryStore();
const sidebarLayoutStore = useSidebarLayoutStore();
const router = useRouter();
const modsStore = useModsStore();
const workflowEmployeesStore = useWorkflowAiEmployeesStore();
const { clientModsUiOff } = storeToRefs(modsStore);

function onClientModsUiOffChange(e) {
  const off = e.target.checked;
  modsStore.setClientModsUiOff(off);
  if (off) {
    workflowEmployeesStore.stripModWorkflowEmployeeKeys();
  }
  // 同步状态到后端，然后刷新页面
  fetch('/api/state/client-mods-off', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ client_mods_off: off }),
  }).finally(() => {
    window.location.reload();
  });
}

const loading = ref(false);
const loadingVersions = ref(false);
const loadingPackages = ref(false);
const loadingTestDb = ref(false);
const aiMode = ref('online');
const assistantName = ref('修茈');
const versions = ref([]);
const sampleCount = ref(0);
const versionsError = ref('');
const sampleCountWarning = ref('');
const aboutClickCount = ref(0);
const testDbEnabled = ref(false);
const testDbMessage = ref('');
const testDbMessageClass = ref('');
const currentDbPath = ref('products.db');
const ABOUT_CLICK_TARGET = 5;
let aboutClickTimer = null;
const ASSISTANT_NAME_KEY = 'assistantName';
const DEFAULT_ASSISTANT_NAME = '修茈';
const industries = ref([]);
const currentIndustry = ref('涂料');
const currentIndustryUnit = ref('桶');
const sidebarThemePreset = ref('office-default');

const selectedSidebarAccent = computed(() => {
  const selected = SIDEBAR_THEME_OPTIONS.find((item) => item.value === sidebarThemePreset.value);
  return selected?.accent || '#0f6cbd';
});

const intentPackages = ref({
  base: {
    name: '基础意图',
    iconClass: 'fa-file-text-o',
    description: '通用的单据操作意图：创建、查询、修改、删除、打印',
    enabled: true,
    keywords: ['开单', '查询', '打印', '导出', '删除', '修改', '创建', '生成']
  },
  industry: {
    name: '行业特定',
    iconClass: 'fa-industry',
    description: '当前行业的特定用语和业务词汇',
    enabled: true,
    keywords: []
  },
  product: {
    name: '产品识别',
    iconClass: 'fa-cubes',
    description: '产品型号、规格、分类的识别和解析',
    enabled: true,
    keywords: ['型号', '规格', '分类', '产品名', '编号']
  },
  quantity: {
    name: '数量解析',
    iconClass: 'fa-sort-numeric-asc',
    description: '数量单位和中文数字的智能解析',
    enabled: true,
    keywords: ['桶', '件', '箱', '斤', '公斤', '二十三', '一十']
  },
  customer: {
    name: '客户识别',
    iconClass: 'fa-users',
    description: '客户名称、联系方式、地址的识别',
    enabled: true,
    keywords: ['客户', '单位', '联系人', '地址', '电话']
  }
});

const currentIndustryConfig = computed(() => {
  return industryStore.industries.find(i => i.id === currentIndustry.value);
});

const normalizedAssistantName = computed(() => {
  const normalized = assistantName.value?.trim();
  return normalized || DEFAULT_ASSISTANT_NAME;
});

const sidebarDefaultKeys = [
  'chat',
  'products',
  'materials-list',
  'business-docking',
  'shipment-records',
  'customers',
  'wechat-contacts',
  'print',
  'printer-list',
  'template-preview',
  'settings',
  'tools',
  'other-tools',
];

async function loadIndustries() {
  try {
    const response = await systemApi.getIndustries();
    if (response.success) {
      industries.value = response.data.industries || [];
      currentIndustry.value = response.data.current || '涂料';
    }
  } catch (e) {
    console.error('加载行业列表失败:', e);
  }
}

async function loadCurrentIndustryDetail() {
  try {
    const response = await systemApi.getCurrentIndustry();
    if (response.success) {
      currentIndustryUnit.value = response.data?.units?.primary || '桶';
      updateIndustryKeywords();
    }
  } catch (e) {
    console.error('加载行业详情失败:', e);
  }
}

function updateIndustryKeywords() {
  const config = industryStore.currentConfig;
  if (config && config.intent_keywords) {
    const kw = config.intent_keywords;
    let keywords = [];
    if (kw.create_order) {
      keywords = [...keywords, ...(Array.isArray(kw.create_order) ? kw.create_order : [kw.create_order])];
    }
    if (kw.quantity_unit) {
      keywords.push(kw.quantity_unit);
    }
    if (kw.print_label) {
      keywords = [...keywords, ...(Array.isArray(kw.print_label) ? kw.print_label : [kw.print_label])];
    }
    intentPackages.value.industry.keywords = [...new Set(keywords)].slice(0, 12);
  }
}

async function onIndustryChange() {
  loadingPackages.value = true;
  try {
    const success = await industryStore.switchIndustry(currentIndustry.value);
    if (success) {
      await loadCurrentIndustryDetail();
      await loadIntentPackages();
    }
  } catch (e) {
    console.error('切换行业失败:', e);
  } finally {
    loadingPackages.value = false;
  }
}

async function loadIntentPackages() {
  try {
    const response = await intentPackagesApi.getPackages();
    if (response.success && response.data?.packages) {
      const packages = response.data.packages;
      for (const key in packages) {
        if (intentPackages.value[key]) {
          intentPackages.value[key].enabled = packages[key].enabled;
          intentPackages.value[key].keywords = packages[key].keywords || [];
        }
      }
    }
  } catch (e) {
    console.error('加载意图包失败:', e);
  }
}

async function togglePackage(key) {
  try {
    const enabled = intentPackages.value[key].enabled;
    await intentPackagesApi.updatePackage(key, enabled);
  } catch (e) {
    console.error('更新意图包失败:', e);
  }
}

async function loadPreferences() {
  try {
    const data = await api.get('/api/preferences', { user_id: 'default' });
    if (!data?.success || !data?.preferences) return;
    const preferredMode = data.preferences.aiMode;
    if (preferredMode === 'online' || preferredMode === 'offline') {
      aiMode.value = preferredMode;
      return;
    }
    const legacyModel = (data.preferences.aiModel || '').toLowerCase();
    aiMode.value = legacyModel === 'local' ? 'offline' : 'online';
    if (legacyModel) {
      // 兼容历史键：读取后自动迁移为新键，避免后续逻辑分叉。
      await api.post('/api/preferences', {
        user_id: 'default',
        key: 'aiMode',
        value: aiMode.value,
      });
    }
    const preferredAssistantName = data.preferences.assistantName;
    if (typeof preferredAssistantName === 'string') {
      assistantName.value = preferredAssistantName;
    } else {
      assistantName.value = window.localStorage.getItem(ASSISTANT_NAME_KEY) || DEFAULT_ASSISTANT_NAME;
    }
    window.localStorage.setItem(ASSISTANT_NAME_KEY, normalizedAssistantName.value);
  } catch (e) {
    console.error('加载设置失败:', e);
    assistantName.value = window.localStorage.getItem(ASSISTANT_NAME_KEY) || DEFAULT_ASSISTANT_NAME;
  }
}

async function saveSettings() {
  loading.value = true;
  try {
    const saveResults = await Promise.all([
      api.post('/api/preferences', {
        user_id: 'default',
        key: 'aiMode',
        value: aiMode.value
      }),
      api.post('/api/preferences', {
        user_id: 'default',
        key: ASSISTANT_NAME_KEY,
        value: normalizedAssistantName.value
      })
    ]);
    const failed = saveResults.find(item => !item?.success);
    if (failed) throw new Error(failed?.message || '保存失败');
    assistantName.value = normalizedAssistantName.value;
    window.localStorage.setItem(ASSISTANT_NAME_KEY, normalizedAssistantName.value);
    window.dispatchEvent(new CustomEvent('assistant-name-updated', {
      detail: {
        name: normalizedAssistantName.value
      }
    }));
    alert('设置已保存');
  } catch (e) {
    console.error('保存设置失败:', e);
    alert(`保存失败: ${e?.message || '未知错误'}`);
  } finally {
    loading.value = false;
  }
}

function onSidebarThemeChange() {
  persistSidebarTheme(sidebarThemePreset.value);
}

function toggleSidebarReorder(event) {
  const enabled = Boolean(event?.target?.checked);
  sidebarLayoutStore.setReorderEnabled(enabled);
}

function resetSidebarOrder() {
  sidebarLayoutStore.resetOrder(sidebarDefaultKeys);
}

async function loadDistillationVersions() {
  loadingVersions.value = true;
  versionsError.value = '';
  sampleCountWarning.value = '';
  try {
    const data = await api.get('/api/distillation/versions');
    if (!data?.success) throw new Error(data?.message || '加载失败');
    versions.value = Array.isArray(data.versions) ? data.versions : [];
    sampleCount.value = Number(data.distillation_samples || 0);
    if (data?.sample_count_error) {
      sampleCountWarning.value = `样本数读取异常：${data.sample_count_error}`;
    }
  } catch (e) {
    console.error('加载蒸馏版本失败:', e);
    versions.value = [];
    sampleCount.value = 0;
    versionsError.value = `蒸馏信息加载失败：${e?.message || '网络或服务异常'}`;
  } finally {
    loadingVersions.value = false;
  }
}

async function loadTestDbStatus() {
  try {
    const data = await api.get('/api/system/test-db/status');
    if (data?.success && data?.data) {
      testDbEnabled.value = data.data.enabled || false;
      currentDbPath.value = data.data.current_db
        ? data.data.current_db.split(/[\\/]/).pop()
        : 'products.db';
    }
  } catch (e) {
    console.error('加载测试数据库状态失败:', e);
  }
}

async function onTestDbToggle(e) {
  loadingTestDb.value = true;
  testDbMessage.value = '';
  testDbMessageClass.value = '';

  // 事件触发时 v-model 可能尚未同步到 ref，因此从事件源读取最新 checked 状态
  const target = e && e.target ? e.target : null;
  const nextEnabled = typeof target?.checked === 'boolean' ? target.checked : testDbEnabled.value;
  testDbEnabled.value = nextEnabled;

  try {
    const endpoint = nextEnabled
      ? '/api/system/test-db/enable'
      : '/api/system/test-db/disable';
    const data = await api.post(endpoint, {});
    if (data?.success) {
      testDbMessage.value = data.message || (nextEnabled ? '已启用测试模式' : '已切换回真实数据库');
      testDbMessageClass.value = 'text-success';
      currentDbPath.value = data.data?.current_db
        ? data.data.current_db.split(/[\\/]/).pop()
        : (nextEnabled ? 'products_test.db' : 'products.db');

      // 与后端真实状态同步，避免 UI 和 DB 切换失败时出现短暂不一致
      await loadTestDbStatus();
    } else {
      testDbMessage.value = data?.error || '操作失败';
      testDbMessageClass.value = 'text-error';
      testDbEnabled.value = !nextEnabled;
    }
  } catch (e) {
    console.error('切换测试数据库失败:', e);
    testDbMessage.value = e?.message || '操作失败';
    testDbMessageClass.value = 'text-error';
    testDbEnabled.value = !nextEnabled;
  } finally {
    loadingTestDb.value = false;
  }
}

function resetAboutClickCount() {
  aboutClickCount.value = 0;
  if (aboutClickTimer) {
    window.clearTimeout(aboutClickTimer);
    aboutClickTimer = null;
  }
}

function handleAboutHeaderClick() {
  aboutClickCount.value += 1;

  if (aboutClickTimer) {
    window.clearTimeout(aboutClickTimer);
  }
  aboutClickTimer = window.setTimeout(() => {
    resetAboutClickCount();
  }, 1800);

  if (aboutClickCount.value >= ABOUT_CLICK_TARGET) {
    resetAboutClickCount();
    router.push({ name: 'chat-debug' });
  }
}

onMounted(async () => {
  sidebarThemePreset.value = readStoredSidebarTheme();
  applySidebarTheme(sidebarThemePreset.value);
  sidebarLayoutStore.initialize(sidebarDefaultKeys);
  await industryStore.initialize();
  await loadIndustries();
  await loadCurrentIndustryDetail();
  await loadIntentPackages();
  loadPreferences();
  loadDistillationVersions();
  loadTestDbStatus();
});

onBeforeUnmount(() => {
  resetAboutClickCount();
});
</script>

<style scoped>
.intent-packages {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.intent-package-item {
  padding: 12px 15px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 8px;
  transition: all 0.2s ease;
}

.intent-package-item.active {
  background: rgba(79, 172, 254, 0.08);
  border-color: rgba(79, 172, 254, 0.3);
}

.pkg-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
}

.pkg-info {
  display: flex;
  align-items: center;
  gap: 8px;
}

.pkg-icon {
  font-size: 16px;
  width: 18px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: #4facfe;
}

.pkg-name {
  font-weight: 500;
  color: #000;
}

.pkg-desc {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.5);
  margin: 0;
}

.pkg-keywords {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 10px;
}

.keyword {
  font-size: 11px;
  padding: 3px 8px;
  background: rgba(79, 172, 254, 0.15);
  color: #4facfe;
  border-radius: 4px;
}

.toggle-switch {
  position: relative;
  display: inline-block;
  width: 40px;
  height: 22px;
}

.toggle-switch input {
  opacity: 0;
  width: 0;
  height: 0;
}

.toggle-slider {
  position: absolute;
  cursor: pointer;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: #e5e7eb;
  border: 1px solid #cbd5e1;
  transition: 0.3s;
  border-radius: 22px;
}

.toggle-slider:before {
  position: absolute;
  content: "";
  height: 16px;
  width: 16px;
  left: 3px;
  bottom: 3px;
  background-color: #ffffff;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.25);
  transition: 0.3s;
  border-radius: 50%;
}

.toggle-switch input:checked + .toggle-slider {
  background-color: #4facfe;
  border-color: #4facfe;
}

.toggle-switch input:checked + .toggle-slider:before {
  transform: translateX(18px);
}

.about-debug-entry {
  cursor: pointer;
  user-select: none;
}

.theme-color-chip {
  display: inline-block;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  margin: 0 6px -3px 4px;
  border: 1px solid rgba(15, 23, 42, 0.2);
}

.mod-ui-off-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.mod-ui-off-label {
  display: block;
  font-weight: 600;
  margin-bottom: 0;
}

.mod-ui-off-desc {
  margin: 8px 0 0;
  max-width: 52rem;
}

.mod-ui-off-desc code {
  font-size: 0.85em;
  padding: 1px 4px;
  border-radius: 4px;
  background: rgba(15, 23, 42, 0.06);
}

.mod-ui-off-toggle {
  flex-shrink: 0;
  margin-top: 2px;
}

.text-warning {
  color: #f59e0b !important;
}

.text-success {
  color: #22c55e !important;
}

.text-error {
  color: #ef4444 !important;
}
</style>
