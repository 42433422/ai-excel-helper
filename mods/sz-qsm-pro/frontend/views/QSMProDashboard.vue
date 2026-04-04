<template>
  <div class="qsm-pro-dashboard">
    <div class="dashboard-header">
      <h1>
        <i class="fa fa-dashboard"></i>
        奇士美 PRO 仪表盘
      </h1>
      <span class="pro-badge">专业版</span>
    </div>

    <div class="dashboard-content">
      <!-- 核心指标卡片 -->
      <div class="metrics-grid">
        <div class="metric-card" v-for="metric in metrics" :key="metric.label">
          <div class="metric-icon" :style="{ background: metric.color }">
            <i :class="metric.icon"></i>
          </div>
          <div class="metric-info">
            <div class="metric-label">{{ metric.label }}</div>
            <div class="metric-value">{{ metric.value }}</div>
            <div class="metric-trend" :class="metric.trendClass">
              <i :class="metric.trendIcon"></i>
              {{ metric.trend }}
            </div>
          </div>
        </div>
      </div>

      <!-- 专业功能列表 -->
      <div class="pro-features">
        <h2><i class="fa fa-star"></i> 专业版功能</h2>
        <div class="features-grid">
          <div class="feature-item" v-for="feature in features" :key="feature">
            <i class="fa fa-check-circle"></i>
            <span>{{ feature }}</span>
          </div>
        </div>
      </div>

      <!-- 快捷操作 -->
      <div class="quick-actions">
        <h2><i class="fa fa-bolt"></i> 快捷操作</h2>
        <div class="actions-grid">
          <button class="action-btn" @click="handleBatchProcess">
            <i class="fa fa-files-o"></i>
            <span>批量处理</span>
          </button>
          <button class="action-btn" @click="handleSmartRecommend">
            <i class="fa fa-magic"></i>
            <span>智能推荐</span>
          </button>
          <button class="action-btn" @click="handleExportReport">
            <i class="fa fa-download"></i>
            <span>导出报表</span>
          </button>
          <button class="action-btn" @click="handleSettings">
            <i class="fa fa-cog"></i>
            <span>高级设置</span>
          </button>
        </div>
      </div>

      <!-- 测试 API -->
      <div class="api-test">
        <h2><i class="fa fa-plug"></i> API 测试</h2>
        <button class="test-btn" @click="testApi">测试仪表盘 API</button>
        <pre v-if="apiResult" class="api-result">{{ JSON.stringify(apiResult, null, 2) }}</pre>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';

const metrics = ref([
  {
    label: '总订单数',
    value: '1,234',
    trend: '+12%',
    trendClass: 'trend-up',
    trendIcon: 'fa-arrow-up',
    icon: 'fa-shopping-cart',
    color: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)'
  },
  {
    label: '总产品数',
    value: '567',
    trend: '+5%',
    trendClass: 'trend-up',
    trendIcon: 'fa-arrow-up',
    icon: 'fa-cubes',
    color: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)'
  },
  {
    label: '总客户数',
    value: '890',
    trend: '+8%',
    trendClass: 'trend-up',
    trendIcon: 'fa-arrow-up',
    icon: 'fa-users',
    color: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)'
  },
  {
    label: '今日营收',
    value: '¥99,999',
    trend: '+15%',
    trendClass: 'trend-up',
    trendIcon: 'fa-arrow-up',
    icon: 'fa-yen',
    color: 'linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)'
  }
]);

const features = ref([
  '高级数据分析',
  '自定义报表',
  '批量处理',
  '智能推荐',
  '自动化工作流',
  '高级权限管理',
  '数据导出增强',
  'API 访问增强'
]);

const apiResult = ref(null);

const testApi = async () => {
  try {
    const response = await fetch('/api/mod/sz-qsm-pro/dashboard');
    const data = await response.json();
    apiResult.value = data;
  } catch (error) {
    apiResult.value = { error: error.message };
  }
};

const handleBatchProcess = () => {
  alert('批量处理功能 - 即将开放');
};

const handleSmartRecommend = () => {
  alert('智能推荐功能 - 即将开放');
};

const handleExportReport = () => {
  alert('导出报表功能 - 即将开放');
};

const handleSettings = () => {
  alert('高级设置 - 即将开放');
};

onMounted(() => {
  testApi();
});
</script>

<style scoped>
.qsm-pro-dashboard {
  padding: 20px;
  max-width: 1400px;
  margin: 0 auto;
}

.dashboard-header {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 30px;
  padding-bottom: 20px;
  border-bottom: 2px solid #e5e7eb;
}

.dashboard-header h1 {
  margin: 0;
  font-size: 28px;
  color: #1f2937;
  display: flex;
  align-items: center;
  gap: 12px;
}

.pro-badge {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 6px 16px;
  border-radius: 999px;
  font-size: 14px;
  font-weight: 600;
}

.dashboard-content {
  display: flex;
  flex-direction: column;
  gap: 30px;
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 20px;
}

.metric-card {
  background: white;
  border-radius: 12px;
  padding: 20px;
  display: flex;
  gap: 16px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  transition: transform 0.2s, box-shadow 0.2s;
}

.metric-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

.metric-icon {
  width: 60px;
  height: 60px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 24px;
  flex-shrink: 0;
}

.metric-info {
  flex: 1;
}

.metric-label {
  font-size: 14px;
  color: #6b7280;
  margin-bottom: 8px;
}

.metric-value {
  font-size: 28px;
  font-weight: 700;
  color: #1f2937;
  margin-bottom: 8px;
}

.metric-trend {
  font-size: 13px;
  display: flex;
  align-items: center;
  gap: 4px;
}

.metric-trend.trend-up {
  color: #10b981;
}

.metric-trend.trend-down {
  color: #ef4444;
}

.pro-features,
.quick-actions,
.api-test {
  background: white;
  border-radius: 12px;
  padding: 24px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.pro-features h2,
.quick-actions h2,
.api-test h2 {
  margin: 0 0 20px 0;
  font-size: 20px;
  color: #1f2937;
  display: flex;
  align-items: center;
  gap: 8px;
}

.features-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 12px;
}

.feature-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px;
  background: #f9fafb;
  border-radius: 8px;
  color: #374151;
}

.feature-item i {
  color: #10b981;
}

.actions-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 16px;
}

.action-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 20px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  border-radius: 12px;
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s;
  font-size: 14px;
}

.action-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(102, 126, 234, 0.4);
}

.action-btn i {
  font-size: 24px;
}

.api-test {
  background: #f9fafb;
}

.test-btn {
  background: #3b82f6;
  color: white;
  border: none;
  padding: 10px 20px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
}

.test-btn:hover {
  background: #2563eb;
}

.api-result {
  margin-top: 16px;
  padding: 16px;
  background: #1f2937;
  color: #10b981;
  border-radius: 8px;
  overflow-x: auto;
  font-size: 13px;
  line-height: 1.6;
}
</style>
<!-- 4243342 -->
