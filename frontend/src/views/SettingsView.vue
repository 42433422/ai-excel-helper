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
                  <span class="pkg-icon">{{ pkg.icon }}</span>
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
          <label>系统名称</label>
          <input type="text" value="AI-Excel Helper 出货单管理系统" disabled>
        </div>
        <div class="form-group">
          <label>数据库路径</label>
          <input type="text" value="products.db" disabled>
        </div>
        <div class="form-group">
          <label>AI 模型</label>
          <select v-model="aiModel">
            <option value="deepseek">DeepSeek</option>
            <option value="local">本地模型 (需配置)</option>
          </select>
        </div>
        <button class="btn btn-primary" @click="saveSettings" :disabled="loading">保存设置</button>
      </div>

      <div class="card">
        <div class="card-header">蒸馏模型版本 <small style="opacity:0.8">专业版对话会参与蒸馏，此处可查看训练产物</small></div>
        <div>
          <p v-if="loadingVersions" class="muted">加载中...</p>
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
        </div>
      </div>

      <div class="card">
        <div class="card-header">关于</div>
        <p>AI-Excel Helper 出货单智能处理系统</p>
        <p>版本: 1.0.0</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref, computed, watch } from 'vue';
import api from '../api';
import { systemApi } from '../api/system';
import { intentPackagesApi } from '../api/intentPackages';
import { useIndustryStore } from '../stores/industry';

const industryStore = useIndustryStore();

const loading = ref(false);
const loadingVersions = ref(false);
const loadingPackages = ref(false);
const aiModel = ref('deepseek');
const versions = ref([]);
const sampleCount = ref(0);

const industries = ref([]);
const currentIndustry = ref('涂料');
const currentIndustryUnit = ref('桶');

const intentPackages = ref({
  base: {
    name: '基础意图',
    icon: '📋',
    description: '通用的单据操作意图：创建、查询、修改、删除、打印',
    enabled: true,
    keywords: ['开单', '查询', '打印', '导出', '删除', '修改', '创建', '生成']
  },
  industry: {
    name: '行业特定',
    icon: '🏭',
    description: '当前行业的特定用语和业务词汇',
    enabled: true,
    keywords: []
  },
  product: {
    name: '产品识别',
    icon: '📦',
    description: '产品型号、规格、分类的识别和解析',
    enabled: true,
    keywords: ['型号', '规格', '分类', '产品名', '编号']
  },
  quantity: {
    name: '数量解析',
    icon: '🔢',
    description: '数量单位和中文数字的智能解析',
    enabled: true,
    keywords: ['桶', '件', '箱', '斤', '公斤', '二十三', '一十']
  },
  customer: {
    name: '客户识别',
    icon: '👥',
    description: '客户名称、联系方式、地址的识别',
    enabled: true,
    keywords: ['客户', '单位', '联系人', '地址', '电话']
  }
});

const currentIndustryConfig = computed(() => {
  return industryStore.industries.find(i => i.id === currentIndustry.value);
});

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
    const response = await systemApi.setIndustry(currentIndustry.value);
    if (response.success) {
      await industryStore.switchIndustry(currentIndustry.value);
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
    if (data?.success && data?.preferences?.aiModel) {
      aiModel.value = data.preferences.aiModel;
    }
  } catch (e) {
    console.error('加载设置失败:', e);
  }
}

async function saveSettings() {
  loading.value = true;
  try {
    const data = await api.post('/api/preferences', {
      user_id: 'default',
      key: 'aiModel',
      value: aiModel.value
    });
    if (!data?.success) throw new Error(data?.message || '保存失败');
    alert('设置已保存');
  } catch (e) {
    console.error('保存设置失败:', e);
    alert(`保存失败: ${e?.message || '未知错误'}`);
  } finally {
    loading.value = false;
  }
}

async function loadDistillationVersions() {
  loadingVersions.value = true;
  try {
    const data = await api.get('/api/distillation/versions');
    if (!data?.success) throw new Error(data?.message || '加载失败');
    versions.value = Array.isArray(data.versions) ? data.versions : [];
    sampleCount.value = Number(data.distillation_samples || 0);
  } catch (e) {
    console.error('加载蒸馏版本失败:', e);
    versions.value = [];
    sampleCount.value = 0;
  } finally {
    loadingVersions.value = false;
  }
}

onMounted(async () => {
  await industryStore.initialize();
  await loadIndustries();
  await loadCurrentIndustryDetail();
  await loadIntentPackages();
  loadPreferences();
  loadDistillationVersions();
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
  background-color: rgba(255, 255, 255, 0.2);
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
  background-color: white;
  transition: 0.3s;
  border-radius: 50%;
}

.toggle-switch input:checked + .toggle-slider {
  background-color: #4facfe;
}

.toggle-switch input:checked + .toggle-slider:before {
  transform: translateX(18px);
}
</style>
