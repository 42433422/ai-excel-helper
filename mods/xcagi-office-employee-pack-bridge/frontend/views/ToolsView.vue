<template>
  <div class="page-view" id="view-tools">
    <div class="page-content">
      <div class="page-header">
        <h2>工具表</h2>
        <div class="header-actions">
          <input type="text" id="toolSearch" placeholder="搜索工具..." v-model="searchQuery" @input="filterTools">
          <select id="toolCategoryFilter" v-model="selectedCategory" @change="filterTools">
            <option value="">全部分类</option>
            <option value="planner">AI Planner</option>
            <option value="products">产品管理</option>
            <option value="customers">客户管理</option>
            <option value="orders">出货单</option>
            <option value="excel">Excel处理</option>
            <option value="ocr">图片OCR</option>
            <option value="materials">原材料仓库</option>
            <option value="print">标签打印</option>
            <option value="database">数据库管理</option>
            <option value="system">系统设置</option>
          </select>
        </div>
      </div>
      <div v-if="loading" class="loading">加载中...</div>
      <div v-else-if="error" class="error">{{ error }}</div>
      <template v-else>
        <div v-if="showPlannerBlock && filteredPlannerTools.length" class="tools-section">
          <div class="tools-section-head">
            <h3 class="tools-section-title">AI Planner 可调用的工具</h3>
            <p class="tools-section-hint">以下为对话里 Planner 实际注册并可能调用的后端工具（function calling），与下方「业务工作台入口」不同。</p>
          </div>
          <div class="tools-container tools-container-planner" id="plannerToolsContainer">
            <div
              v-for="tool in filteredPlannerTools"
              :key="getToolId(tool)"
              class="tool-card tool-card-planner"
              :data-tool-id="getToolId(tool)"
              @click="showToolDetail(getToolId(tool))"
            >
              <span class="tool-category planner">{{ getCategoryName(tool) }}</span>
              <span v-if="tool.planner_callable" class="planner-badge" title="由 AI Planner（对话）调用">Planner</span>
              <div class="tool-name">{{ tool.name }}</div>
              <div class="tool-description">{{ tool.description }}</div>
              <div class="tool-actions">
                <button
                  class="tool-action-btn query"
                  type="button"
                  data-action="open-tool"
                  :data-tool-id="getToolId(tool)"
                  @click.stop="showToolDetail(getToolId(tool))"
                >
                  查看
                </button>
              </div>
            </div>
          </div>
        </div>

        <div v-if="showAppBlock" class="tools-section">
          <div class="tools-section-head">
            <h3 class="tools-section-title">业务工作台入口</h3>
            <p class="tools-section-hint">打开各业务页面；不等同于左侧 Planner 的 function 工具。</p>
          </div>
          <div v-if="filteredAppTools.length === 0" class="empty">该分类下没有工作台入口</div>
          <div v-else class="tools-container" id="toolsContainer">
            <div
              v-for="tool in filteredAppTools"
              :key="getToolId(tool)"
              class="tool-card"
              :data-tool-id="getToolId(tool)"
              @click="showToolDetail(getToolId(tool))"
            >
              <span class="tool-category" :class="getCategoryKey(tool)">{{ getCategoryName(tool) }}</span>
              <div class="tool-name">{{ tool.name }}</div>
              <div class="tool-description">{{ tool.description }}</div>
              <div class="tool-actions">
                <button class="tool-action-btn query" data-action="open-tool" :data-tool-id="getToolId(tool)" @click.stop="openTool(getToolId(tool))">查看</button>
              </div>
            </div>
          </div>
        </div>

        <div
          v-if="!loading && !error && !filteredPlannerTools.length && !filteredAppTools.length"
          class="empty"
        >
          没有找到工具
        </div>
      </template>
    </div>

    <div v-if="showModal" class="modal" id="toolDetailModal" @click.self="closeToolModal">
      <div class="modal-content" style="max-width: 500px;">
        <div class="modal-header">
          <span>{{ selectedTool?.name }}</span>
          <span class="close" data-action="close-tool-modal" @click="closeToolModal">×</span>
        </div>
        <div class="modal-body" v-if="selectedTool">
          <p v-if="selectedTool.planner_callable || selectedTool.kind === 'planner_backend'">
            <span class="planner-badge modal-badge">Planner 可调用</span>
          </p>
          <p><strong>分类：</strong>{{ getCategoryName(selectedTool) }}</p>
          <p><strong>描述：</strong>{{ selectedTool.description || '无' }}</p>
          <p><strong>工具Key：</strong>{{ selectedTool.tool_key || selectedTool.id }}</p>
          <div v-if="plannerParamFields.length" class="tool-params">
            <h4>参数（JSON Schema）</h4>
            <div v-for="param in plannerParamFields" :key="param.name" class="tool-param">
              <label>{{ param.name }}{{ param.required ? ' *' : '' }} ({{ param.type }})</label>
              <input
                :type="param.type === 'number' ? 'number' : 'text'"
                :id="'param_' + param.name"
                :placeholder="param.description || ''"
                v-model="toolParams[param.name]"
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { apiFetch, apiUrl, isApiFetchTimeoutError } from '@/utils/apiBase';

const router = useRouter();

/** 避免 /api/db-tools 或 /api/tools 挂死时 loading 永不结束（无异常则全局日志也看不到） */
const LOAD_TOOLS_TIMEOUT_MS = 60_000;

const allTools = ref([]);
/** 与 execute_workflow_tool 对齐的 Planner function 工具表（来自 /api/db-tools planner_tools） */
const plannerTools = ref([]);
const loading = ref(true);
const error = ref('');
const searchQuery = ref('');
const selectedCategory = ref('');
const showModal = ref(false);
const selectedTool = ref(null);
const toolParams = ref({});

/** Planner 工具为 OpenAI JSON Schema；旧工作台工具可能为 parameters 数组 */
const plannerParamFields = computed(() => {
  const st = selectedTool.value;
  if (!st || !st.parameters) return [];
  if (Array.isArray(st.parameters) && st.parameters.length) {
    return st.parameters.map((p) => ({
      name: p.name,
      type: p.type || 'string',
      required: !!p.required,
      description: p.description || ''
    }));
  }
  const p = st.parameters;
  if (typeof p !== 'object' || p.type !== 'object' || !p.properties || typeof p.properties !== 'object') {
    return [];
  }
  const req = new Set(Array.isArray(p.required) ? p.required : []);
  return Object.keys(p.properties).map((name) => {
    const spec = p.properties[name] || {};
    return {
      name,
      type: spec.type || 'string',
      required: req.has(name),
      description: spec.description || ''
    };
  });
});

const categoryNames = {
  planner: 'AI Planner',
  products: '产品管理',
  customers: '客户/购买单位',
  orders: '出货单',
  excel: 'Excel 处理',
  ocr: '图片 OCR',
  materials: '原材料仓库',
  print: '标签打印',
  database: '数据库管理',
  system: '系统设置'
};

function extractTools(data) {
  if (Array.isArray(data)) return data;
  if (!data || typeof data !== 'object') return [];
  if (Array.isArray(data.tools)) return data.tools;
  if (Array.isArray(data.data)) return data.data;
  return [];
}

function extractPlannerTools(data) {
  if (!data || typeof data !== 'object') return [];
  if (Array.isArray(data.planner_tools)) return data.planner_tools;
  return [];
}

const showPlannerBlock = computed(() => {
  if (selectedCategory.value === 'planner') return true;
  return !selectedCategory.value;
});

const showAppBlock = computed(() => selectedCategory.value !== 'planner');

const filteredPlannerTools = computed(() => {
  if (!showPlannerBlock.value) return [];
  const q = (searchQuery.value || '').trim().toLowerCase();
  return plannerTools.value.filter((tool) => {
    const matchSearch =
      !q ||
      (tool.name || '').toLowerCase().includes(q) ||
      (tool.description || '').toLowerCase().includes(q) ||
      (tool.tool_key || '').toLowerCase().includes(q);
    return matchSearch;
  });
});

const filteredAppTools = computed(() => {
  if (!showAppBlock.value) return [];
  return allTools.value.filter((tool) => {
    const categoryKey = getCategoryKey(tool);
    const matchSearch =
      !searchQuery.value ||
      (tool.name || '').toLowerCase().includes(searchQuery.value.toLowerCase()) ||
      (tool.description || '').toLowerCase().includes(searchQuery.value.toLowerCase());
    const matchCategory = !selectedCategory.value || categoryKey === selectedCategory.value;
    return matchSearch && matchCategory;
  });
});

const allToolsFlat = computed(() => [...plannerTools.value, ...allTools.value]);

function getCategoryKey(tool) {
  return (tool && tool.category && tool.category.category_key) 
    ? tool.category.category_key 
    : (tool && tool.category ? tool.category : 'other');
}

function getCategoryName(tool) {
  const key = getCategoryKey(tool);
  return categoryNames[key] || key;
}

function getToolId(tool) {
  return (tool && tool.id != null) ? String(tool.id) : tool.tool_key;
}

async function loadTools() {
  try {
    loading.value = true;
    error.value = '';
    plannerTools.value = [];

    let loaded = false;
    try {
      const r1 = await apiFetch('/api/db-tools', { timeoutMs: LOAD_TOOLS_TIMEOUT_MS });
      if (r1.ok) {
        const data1 = await r1.json();
        const tools1 = data1?.success ? extractTools(data1) : [];
        plannerTools.value = data1?.success ? extractPlannerTools(data1) : [];
        if (tools1.length > 0 || plannerTools.value.length > 0) {
          allTools.value = tools1;
          loaded = true;
        } else if (!data1?.success) {
          console.warn('[ToolsView] /api/db-tools 业务未成功:', data1);
        }
      } else {
        console.warn('[ToolsView] /api/db-tools HTTP', r1.status);
      }
    } catch (e) {
      if (isApiFetchTimeoutError(e)) {
        console.error('[ToolsView] /api/db-tools 超时（', LOAD_TOOLS_TIMEOUT_MS, 'ms），将尝试 /api/tools');
      } else {
        console.warn('[ToolsView] /api/db-tools 请求异常:', e);
      }
    }

    if (!loaded) {
      const r2 = await apiFetch('/api/tools', { timeoutMs: LOAD_TOOLS_TIMEOUT_MS });
      if (!r2.ok) {
        throw new Error(`工具列表接口 HTTP ${r2.status}（/api/tools）`);
      }
      const data2 = await r2.json();
      if (data2.success) {
        allTools.value = extractTools(data2);
        plannerTools.value = extractPlannerTools(data2);
      } else {
        allTools.value = [];
        plannerTools.value = [];
        error.value = String(data2.message || data2.error || '工具列表不可用（success=false）');
        console.warn('[ToolsView] /api/tools 业务未成功:', data2);
      }
    }
  } catch (err) {
    console.error('[ToolsView] 加载工具失败:', err);
    error.value =
      '加载失败: ' + (err instanceof Error ? err.message : String(err));
    allTools.value = [];
  } finally {
    loading.value = false;
  }
}

function filterTools() {
}

function showToolDetail(toolId) {
  const tool = allToolsFlat.value.find((t) => getToolId(t) === toolId);
  if (!tool) return;
  
  selectedTool.value = tool;
  toolParams.value = {};
  showModal.value = true;
}

function resolveConsoleRedirectToRoute(redirect) {
  const url = String(redirect || '').trim();
  if (!url) return '';
  if (url.startsWith('/orders')) return '/orders';
  if (url.startsWith('/products')) return '/products';
  if (url.startsWith('/customers')) return '/customers';
  if (url.startsWith('/materials')) return '/materials';
  if (url.startsWith('/print')) return '/print';
  if (url.startsWith('/template-preview')) return '/template-preview';
  if (url.startsWith('/ocr')) return '/chat';
  if (url.startsWith('/wechat-contacts')) return '/wechat-contacts';
  if (!url.startsWith('/console')) return url;

  const match = url.match(/[?&]view=([^&]+)/);
  const view = decodeURIComponent(match?.[1] || '').trim();
  const viewRouteMap = {
    products: '/products',
    customers: '/customers',
    'shipment-orders': '/orders',
    print: '/print',
    materials: '/materials',
    ocr: '/chat',
    'wechat-contacts': '/wechat-contacts',
    excel: '/template-preview',
    'template-preview': '/template-preview',
    shipment: '/orders'
  };
  return viewRouteMap[view] || '';
}

async function openTool(toolId) {
  const directRouteMap = {
    products: '/products',
    customers: '/customers',
    orders: '/orders',
    print: '/print',
    materials: '/materials',
    shipment_template: '/template-preview',
    excel_decompose: '/template-preview',
    wechat: '/wechat-contacts'
  };

  const directRoute = directRouteMap[String(toolId || '').trim()];
  if (directRoute) {
    router.push(directRoute);
    return;
  }

  try {
    const response = await fetch(apiUrl('/api/tools/execute'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ tool_id: toolId, action: 'view' })
    });
    const data = await response.json();
    if (data?.success && data?.redirect) {
      const targetRoute = resolveConsoleRedirectToRoute(data.redirect);
      if (targetRoute) {
        router.push(targetRoute);
        return;
      }
    }
  } catch (err) {
    console.warn('打开工具失败，回退详情弹窗:', err);
  }

  showToolDetail(toolId);
}

function closeToolModal() {
  showModal.value = false;
  selectedTool.value = null;
  toolParams.value = {};
}

onMounted(() => {
  loadTools();
});
</script>

<style scoped>
.tools-section {
  margin-top: 4px;
}
.tools-section + .tools-section {
  margin-top: 28px;
  padding-top: 8px;
  border-top: 1px solid #e5e7eb;
}
.tools-section-head {
  margin-bottom: 12px;
}
.tools-section-title {
  font-size: 1.1rem;
  margin: 0 0 6px;
  color: #0f172a;
}
.tools-section-hint {
  margin: 0;
  font-size: 12px;
  color: #64748b;
  line-height: 1.45;
  max-width: 900px;
}
.planner-badge {
  display: inline-block;
  font-size: 11px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 4px;
  background: #ede9fe;
  color: #5b21b6;
  margin-left: 8px;
  vertical-align: middle;
}
.modal-badge {
  margin-left: 0;
  margin-bottom: 10px;
}
.tool-card-planner {
  border-color: #c4b5fd;
  background: #faf5ff;
}
.tool-card-planner .tool-category.planner {
  background: #ede9fe;
  color: #5b21b6;
}
</style>
