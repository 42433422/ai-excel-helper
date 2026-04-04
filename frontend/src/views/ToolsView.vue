<template>
  <div class="page-view" id="view-tools">
    <div class="page-content">
      <div class="page-header">
        <h2>工具表</h2>
        <div class="header-actions">
          <input type="text" id="toolSearch" placeholder="搜索工具..." v-model="searchQuery" @input="filterTools">
          <select id="toolCategoryFilter" v-model="selectedCategory" @change="filterTools">
            <option value="">全部分类</option>
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
      <div class="tools-container" id="toolsContainer">
        <div v-if="loading" class="loading">加载中...</div>
        <div v-else-if="error" class="error">{{ error }}</div>
        <div v-else-if="filteredTools.length === 0" class="empty">没有找到工具</div>
        <template v-else>
          <div
            v-for="tool in filteredTools"
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
        </template>
      </div>
    </div>

    <div v-if="showModal" class="modal" id="toolDetailModal" @click.self="closeToolModal">
      <div class="modal-content" style="max-width: 500px;">
        <div class="modal-header">
          <span>{{ selectedTool?.name }}</span>
          <span class="close" data-action="close-tool-modal" @click="closeToolModal">×</span>
        </div>
        <div class="modal-body" v-if="selectedTool">
          <p><strong>分类：</strong>{{ getCategoryName(selectedTool) }}</p>
          <p><strong>描述：</strong>{{ selectedTool.description || '无' }}</p>
          <p><strong>工具Key：</strong>{{ selectedTool.tool_key || selectedTool.id }}</p>
          <div v-if="selectedTool.parameters && selectedTool.parameters.length > 0" class="tool-params">
            <h4>参数</h4>
            <div v-for="param in selectedTool.parameters" :key="param.name" class="tool-param">
              <label>{{ param.name }}{{ param.required ? ' *' : '' }} ({{ param.type }})</label>
              <input :type="param.type === 'number' ? 'number' : 'text'" :id="'param_' + param.name" :placeholder="param.description || ''" v-model="toolParams[param.name]">
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

const API_BASE = '';
const router = useRouter();

const allTools = ref([]);
const loading = ref(true);
const error = ref('');
const searchQuery = ref('');
const selectedCategory = ref('');
const showModal = ref(false);
const selectedTool = ref(null);
const toolParams = ref({});

const categoryNames = {
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

const filteredTools = computed(() => {
  return allTools.value.filter(tool => {
    const categoryKey = getCategoryKey(tool);
    const matchSearch = !searchQuery.value || 
      (tool.name || '').toLowerCase().includes(searchQuery.value.toLowerCase()) || 
      (tool.description || '').toLowerCase().includes(searchQuery.value.toLowerCase());
    const matchCategory = !selectedCategory.value || categoryKey === selectedCategory.value;
    return matchSearch && matchCategory;
  });
});

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
    
    let response = await fetch(API_BASE + '/api/db-tools');
    let data = await response.json();
    
    if (data.success && data.tools && data.tools.length > 0) {
      allTools.value = data.tools;
    } else {
      response = await fetch(API_BASE + '/api/tools');
      data = await response.json();
      if (data.success) {
        allTools.value = data.tools || data || [];
      }
    }
  } catch (err) {
    console.error('加载工具失败:', err);
    error.value = '加载失败: ' + String(err);
  } finally {
    loading.value = false;
  }
}

function filterTools() {
}

function showToolDetail(toolId) {
  const tool = allTools.value.find(t => getToolId(t) === toolId);
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
    const response = await fetch(`${API_BASE}/api/tools/execute`, {
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
