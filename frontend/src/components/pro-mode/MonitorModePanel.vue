<template>
  <div class="monitor-mode-panel" :class="{ 'monitor-mode': isMonitorMode }">
    <div class="monitor-header">
      <h3 class="monitor-title">⚡ 系统监控面板</h3>
      <button class="close-btn" @click="handleClose">×</button>
    </div>

    <div class="monitor-body">
      <div class="metrics-grid">
        <div class="metric-card cpu" @click="refreshData">
          <div class="metric-icon">🖥️</div>
          <div class="metric-info">
            <div class="metric-label">CPU 使用率</div>
            <div class="metric-value">{{ metrics.cpu }}%</div>
            <div class="metric-bar">
              <div class="metric-bar-fill" :style="{ width: metrics.cpu + '%' }"></div>
            </div>
          </div>
        </div>

        <div class="metric-card memory">
          <div class="metric-icon">💾</div>
          <div class="metric-info">
            <div class="metric-label">内存使用</div>
            <div class="metric-value">{{ metrics.memory }}%</div>
            <div class="metric-bar">
              <div class="metric-bar-fill" :style="{ width: metrics.memory + '%' }"></div>
            </div>
          </div>
        </div>

        <div class="metric-card disk">
          <div class="metric-icon">💿</div>
          <div class="metric-info">
            <div class="metric-label">磁盘使用</div>
            <div class="metric-value">{{ metrics.disk }}%</div>
            <div class="metric-bar">
              <div class="metric-bar-fill" :style="{ width: metrics.disk + '%' }"></div>
            </div>
          </div>
        </div>

        <div class="metric-card requests">
          <div class="metric-icon">📊</div>
          <div class="metric-info">
            <div class="metric-label">活跃请求</div>
            <div class="metric-value">{{ metrics.activeRequests }}</div>
          </div>
        </div>
      </div>

      <div class="services-section">
        <div class="section-header">
          <span class="section-title">服务状态</span>
          <span class="refresh-hint">点击指标卡刷新</span>
        </div>
        <div class="services-list">
          <div
            v-for="service in services"
            :key="service.name"
            class="service-item"
            :class="service.status"
          >
            <div class="service-status-dot"></div>
            <div class="service-name">{{ service.name }}</div>
            <div class="service-status">{{ service.statusText }}</div>
          </div>
        </div>
      </div>

      <div class="alerts-section">
        <div class="section-header">
          <span class="section-title">📢 最近告警</span>
          <span class="alert-count" v-if="alerts.length > 0">{{ alerts.length }}</span>
        </div>
        <div class="alerts-list">
          <div v-if="alerts.length === 0" class="no-alerts">
            ✅ 暂无告警
          </div>
          <div
            v-for="alert in alerts"
            :key="alert.id"
            class="alert-item"
            :class="alert.severity"
          >
            <div class="alert-time">{{ alert.time }}</div>
            <div class="alert-message">{{ alert.message }}</div>
          </div>
        </div>
      </div>

      <div class="logs-section">
        <div class="section-header">
          <span class="section-title">📋 最近日志</span>
        </div>
        <div class="logs-list">
          <div
            v-for="log in recentLogs"
            :key="log.id"
            class="log-item"
            :class="log.level"
          >
            <span class="log-time">{{ log.time }}</span>
            <span class="log-level">[{{ log.level.toUpperCase() }}]</span>
            <span class="log-message">{{ log.message }}</span>
          </div>
        </div>
      </div>

      <div class="actions-bar">
        <button class="action-btn refresh" @click="refreshData">
          🔄 刷新数据
        </button>
        <button class="action-btn history" @click="viewHistory">
          📈 历史趋势
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'

const props = defineProps({
  isMonitorMode: {
    type: Boolean,
    default: true
  }
})

const emit = defineEmits(['close', 'viewHistory'])

const metrics = ref({
  cpu: 0,
  memory: 0,
  disk: 0,
  activeRequests: 0
})

const services = ref([
  { name: 'Backend API', status: 'healthy', statusText: '运行中' },
  { name: 'MySQL Database', status: 'healthy', statusText: '运行中' },
  { name: 'Redis Cache', status: 'healthy', statusText: '运行中' },
  { name: 'AI Service', status: 'healthy', statusText: '运行中' }
])

const alerts = ref([])

const recentLogs = ref([])

let refreshInterval = null

async function fetchHealthData() {
  try {
    const response = await fetch('/health/details')
    if (response.ok) {
      const data = await response.json()
      if (data.system) {
        metrics.value.cpu = Math.round(data.system.cpu_percent || 0)
        metrics.value.memory = Math.round(data.system.memory_percent || 0)
        metrics.value.disk = Math.round(data.system.disk_percent || 0)
      }
      if (data.checks) {
        services.value = services.value.map(svc => {
          const check = data.checks[svc.name.toLowerCase().replace(' ', '_')]
          return {
            ...svc,
            status: check?.status === 'healthy' ? 'healthy' : 'warning',
            statusText: check?.status === 'healthy' ? '运行中' : '异常'
          }
        })
      }
    }
  } catch (e) {
    console.warn('Failed to fetch health data:', e)
  }
}

async function fetchMetrics() {
  try {
    const response = await fetch('/metrics')
    if (response.ok) {
      const text = await response.text()
      const activeReqMatch = text.match(/active_requests (\d+)/)
      if (activeReqMatch) {
        metrics.value.activeRequests = parseInt(activeReqMatch[1]) || 0
      }
    }
  } catch (e) {
    console.warn('Failed to fetch metrics:', e)
  }
}

function generateMockData() {
  metrics.value = {
    cpu: Math.round(30 + Math.random() * 40),
    memory: Math.round(40 + Math.random() * 35),
    disk: Math.round(50 + Math.random() * 20),
    activeRequests: Math.round(Math.random() * 10)
  }

  services.value = [
    { name: 'Backend API', status: 'healthy', statusText: '运行中' },
    { name: 'MySQL Database', status: 'healthy', statusText: '运行中' },
    { name: 'Redis Cache', status: 'healthy', statusText: '运行中' },
    { name: 'AI Service', status: Math.random() > 0.9 ? 'warning' : 'healthy', statusText: Math.random() > 0.9 ? '响应慢' : '运行中' }
  ]

  if (metrics.value.cpu > 60) {
    alerts.value = [
      { id: 1, severity: 'warning', time: '13:32:15', message: 'CPU 使用率偏高 (65%)' }
    ]
  } else {
    alerts.value = []
  }

  const levels = ['info', 'info', 'info', 'warning', 'error']
  const logMessages = [
    'User login: admin',
    'API request: GET /api/products',
    'Database query executed',
    'Slow query detected: 2.5s',
    'Connection timeout: redis://cache'
  ]
  recentLogs.value = Array.from({ length: 5 }, (_, i) => ({
    id: i,
    time: `13:${30 + i}:${Math.floor(Math.random() * 60)}`,
    level: levels[Math.floor(Math.random() * levels.length)],
    message: logMessages[Math.floor(Math.random() * logMessages.length)]
  }))
}

function refreshData() {
  fetchHealthData()
  fetchMetrics()
  generateMockData()
}

function handleClose() {
  emit('close')
}

function viewHistory() {
  emit('viewHistory')
}

onMounted(() => {
  refreshData()
  refreshInterval = setInterval(refreshData, 10000)
})

onUnmounted(() => {
  if (refreshInterval) {
    clearInterval(refreshInterval)
  }
})
</script>

<style scoped>
.monitor-mode-panel {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 520px;
  max-height: 600px;
  background: rgba(10, 14, 39, 0.95);
  border: 1px solid rgba(255, 215, 0, 0.5);
  border-radius: 12px;
  box-shadow: 0 0 30px rgba(255, 215, 0, 0.3);
  backdrop-filter: blur(10px);
  overflow: hidden;
  z-index: 100;
}

.monitor-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  background: rgba(255, 215, 0, 0.1);
  border-bottom: 1px solid rgba(255, 215, 0, 0.3);
}

.monitor-title {
  margin: 0;
  font-size: 16px;
  font-weight: bold;
  color: rgba(255, 215, 0, 0.9);
}

.close-btn {
  background: transparent;
  border: none;
  color: rgba(255, 215, 0, 0.7);
  font-size: 24px;
  cursor: pointer;
  padding: 0;
  line-height: 1;
}

.close-btn:hover {
  color: rgba(255, 215, 0, 0.9);
}

.monitor-body {
  padding: 16px;
  max-height: 540px;
  overflow-y: auto;
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
  margin-bottom: 16px;
}

.metric-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  background: rgba(255, 215, 0, 0.05);
  border: 1px solid rgba(255, 215, 0, 0.2);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.metric-card:hover {
  background: rgba(255, 215, 0, 0.1);
  transform: scale(1.02);
}

.metric-icon {
  font-size: 28px;
}

.metric-info {
  flex: 1;
}

.metric-label {
  font-size: 12px;
  color: rgba(255, 215, 0, 0.7);
  margin-bottom: 4px;
}

.metric-value {
  font-size: 20px;
  font-weight: bold;
  color: rgba(255, 255, 255, 0.9);
  margin-bottom: 6px;
}

.metric-bar {
  height: 4px;
  background: rgba(255, 215, 0, 0.2);
  border-radius: 2px;
  overflow: hidden;
}

.metric-bar-fill {
  height: 100%;
  background: linear-gradient(90deg, rgba(255, 215, 0, 0.6), rgba(255, 215, 0, 0.9));
  border-radius: 2px;
  transition: width 0.5s ease;
}

.services-section,
.alerts-section,
.logs-section {
  margin-bottom: 16px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.section-title {
  font-size: 14px;
  font-weight: bold;
  color: rgba(255, 215, 0, 0.9);
}

.refresh-hint {
  font-size: 11px;
  color: rgba(255, 215, 0, 0.5);
}

.alert-count {
  font-size: 12px;
  padding: 2px 8px;
  background: rgba(255, 0, 0, 0.3);
  border-radius: 10px;
  color: rgba(255, 255, 255, 0.9);
}

.services-list {
  background: rgba(0, 0, 0, 0.2);
  border-radius: 8px;
  overflow: hidden;
}

.service-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  border-bottom: 1px solid rgba(255, 215, 0, 0.1);
}

.service-item:last-child {
  border-bottom: none;
}

.service-status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: rgba(0, 255, 0, 0.6);
}

.service-item.warning .service-status-dot {
  background: rgba(255, 165, 0, 0.8);
}

.service-item.critical .service-status-dot {
  background: rgba(255, 0, 0, 0.8);
}

.service-name {
  flex: 1;
  font-size: 13px;
  color: rgba(255, 255, 255, 0.9);
}

.service-status {
  font-size: 12px;
  color: rgba(255, 215, 0, 0.7);
}

.alerts-list {
  background: rgba(0, 0, 0, 0.2);
  border-radius: 8px;
  overflow: hidden;
}

.no-alerts {
  padding: 16px;
  text-align: center;
  font-size: 13px;
  color: rgba(0, 255, 0, 0.7);
}

.alert-item {
  display: flex;
  gap: 10px;
  padding: 10px 14px;
  border-bottom: 1px solid rgba(255, 215, 0, 0.1);
}

.alert-item:last-child {
  border-bottom: none;
}

.alert-item.warning {
  background: rgba(255, 165, 0, 0.1);
}

.alert-item.critical {
  background: rgba(255, 0, 0, 0.1);
}

.alert-time {
  font-size: 11px;
  color: rgba(255, 215, 0, 0.6);
  white-space: nowrap;
}

.alert-message {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.9);
}

.logs-list {
  background: rgba(0, 0, 0, 0.3);
  border-radius: 8px;
  padding: 8px;
  max-height: 150px;
  overflow-y: auto;
  font-family: 'Monaco', 'Menlo', monospace;
  font-size: 11px;
}

.log-item {
  display: flex;
  gap: 8px;
  padding: 4px 6px;
  border-radius: 4px;
  margin-bottom: 4px;
}

.log-item:last-child {
  margin-bottom: 0;
}

.log-item:hover {
  background: rgba(255, 215, 0, 0.05);
}

.log-time {
  color: rgba(255, 215, 0, 0.5);
  white-space: nowrap;
}

.log-level {
  color: rgba(255, 215, 0, 0.7);
  font-weight: bold;
  min-width: 50px;
}

.log-item.warning .log-level {
  color: rgba(255, 165, 0, 0.9);
}

.log-item.error .log-level {
  color: rgba(255, 0, 0, 0.9);
}

.log-message {
  color: rgba(255, 255, 255, 0.8);
  word-break: break-all;
}

.actions-bar {
  display: flex;
  gap: 12px;
}

.action-btn {
  flex: 1;
  padding: 10px 16px;
  border: none;
  border-radius: 6px;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.3s ease;
  background: rgba(255, 215, 0, 0.15);
  color: rgba(255, 215, 0, 0.9);
  border: 1px solid rgba(255, 215, 0, 0.3);
}

.action-btn:hover {
  background: rgba(255, 215, 0, 0.25);
  transform: scale(1.02);
}
</style>
