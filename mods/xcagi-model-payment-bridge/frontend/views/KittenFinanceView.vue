<template>
  <div class="kitten-simple">
    <!-- 顶部标题栏 -->
    <header class="k-header">
      <div class="k-brand">
        <span class="k-icon">🐱</span>
        <div>
          <h1>小猫财务分析</h1>
          <p>一键查看本月经营状况</p>
        </div>
      </div>
      <button class="k-btn k-btn-primary" @click="generate" :disabled="loading">
        {{ loading ? '⏳ 分析中...' : '🚀 开始分析' }}
      </button>
    </header>

    <!-- 加载动画 -->
    <div v-if="loading" class="k-loading">
      <div class="k-spinner"></div>
      <p>正在读取数据...</p>
    </div>

    <!-- 主内容区 -->
    <main v-if="!loading && hasData" class="k-main">
      <!-- 核心指标 - 一行6个卡片 -->
      <section class="k-metrics">
        <div class="k-card k-card-green">
          <div class="k-label">本月营收</div>
          <div class="k-value">{{ fmt(m.total_revenue) }}</div>
          <div class="k-sub">{{ m.order_count }} 笔订单</div>
        </div>
        <div class="k-card k-card-red">
          <div class="k-label">成本估算</div>
          <div class="k-value">{{ fmt(m.total_cost) }}</div>
          <div class="k-sub">约30%库存值</div>
        </div>
        <div class="k-card" :class="m.gross_profit >= 0 ? 'k-card-blue' : 'k-card-red'">
          <div class="k-label">毛利润</div>
          <div class="k-value">{{ fmt(m.gross_profit) }}</div>
          <div class="k-sub">毛利率 {{ m.profit_margin.toFixed(1) }}%</div>
        </div>
        <div class="k-card k-card-orange">
          <div class="k-label">平均订单</div>
          <div class="k-value">{{ fmt(m.avg_order_value) }}</div>
          <div class="k-sub">每笔均值</div>
        </div>
        <div class="k-card k-card-purple">
          <div class="k-label">热销产品</div>
          <div class="k-value">{{ topProduct }}</div>
          <div class="k-sub">Top 1 产品</div>
        </div>
        <div class="k-card k-card-teal">
          <div class="k-label">大客户</div>
          <div class="k-value">{{ topCustomer }}</div>
          <div class="k-sub">Top 1 客户</div>
        </div>
      </section>

      <!-- 简洁图表区域 -->
      <section class="k-chart-section">
        <div class="k-section-header">
          <h2>📈 营收趋势</h2>
          <button class="k-btn-sm" @click="toggleChart">{{ showChart ? '收起' : '展开' }}</button>
        </div>
        <div v-show="showChart" class="k-chart-box" ref="chartEl"></div>
      </section>

      <!-- 排行榜表格 -->
      <section class="k-tables">
        <div class="k-half">
          <h3>🏆 产品排行 Top 5</h3>
          <table class="k-table">
            <tr v-for="(p, i) in products.slice(0, 5)" :key="i">
              <td class="k-rank">{{ i + 1 }}</td>
              <td>{{ p.product_name }}</td>
              <td class="k-money">{{ fmt(p.total_revenue) }}</td>
            </tr>
            <tr v-if="products.length === 0"><td colspan="3" class="k-empty">暂无数据</td></tr>
          </table>
        </div>
        <div class="k-half">
          <h3>🤝 客户排行 Top 5</h3>
          <table class="k-table">
            <tr v-for="(c, i) in customers.slice(0, 5)" :key="i">
              <td class="k-rank">{{ i + 1 }}</td>
              <td>{{ c.customer }}</td>
              <td class="k-money">{{ fmt(c.total_amount) }}</td>
            </tr>
            <tr v-if="customers.length === 0"><td colspan="3" class="k-empty">暂无数据</td></tr>
          </table>
        </div>
      </section>

      <!-- 预警提示 -->
      <section v-if="alerts.length > 0" class="k-alerts">
        <h3>⚠️ 低库存预警 ({{ alerts.length }}项)</h3>
        <div class="k-alert-list">
          <div v-for="(a, i) in alerts.slice(0, 5)" :key="i" class="k-alert-item">
            <strong>{{ a.name }}</strong>
            <span>当前 {{ a.current }} / 最低 {{ a.min_required }}</span>
          </div>
        </div>
      </section>

      <!-- 底部操作 -->
      <footer class="k-actions">
        <button class="k-btn k-btn-outline" @click="doExport">📥 导出 Excel 报表</button>
        <button class="k-btn k-btn-ghost" @click="generate">🔄 刷新数据</button>
        <span class="k-time">更新于 {{ updateTime }}</span>
      </footer>
    </main>

    <!-- 空状态 -->
    <div v-if="!loading && !hasData" class="k-empty-state">
      <div class="k-empty-icon">🐱</div>
      <h2>还没有分析数据</h2>
      <p>点击上方「开始分析」按钮，一键生成财务报告</p>
      <button class="k-btn k-btn-primary k-btn-lg" @click="generate">立即开始</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, nextTick } from 'vue'
import kittenApi from '@/api/kitten'
import { appAlert } from '@/utils/appDialog'

const loading = ref(false)
const hasData = ref(false)
const showChart = ref(true)
const updateTime = ref('')

const m = ref({
  total_revenue: 0,
  total_cost: 0,
  gross_profit: 0,
  profit_margin: 0,
  order_count: 0,
  avg_order_value: 0,
})

const products = ref<any[]>([])
const customers = ref<any[]>([])
const alerts = ref<any[]>([])

let chartInstance: any = null
const chartEl = ref<HTMLElement>()

const topProduct = computed(() => products.value[0]?.product_name?.slice(0, 8) || '-')
const topCustomer = computed(() => customers.value[0]?.customer?.slice(0, 8) || '-')

function fmt(n: number): string {
  if (!n && n !== 0) return '¥0'
  if (Math.abs(n) >= 10000) return `¥${(n / 10000).toFixed(1)}万`
  return `¥${n.toFixed(0)}`
}

async function loadECharts() {
  if ((window as any).echarts) return
  return new Promise(r => {
    const s = document.createElement('script')
    s.src = 'https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js'
    s.onload = r; s.onerror = r
    document.head.appendChild(s)
  })
}

function toggleChart() { showChart.value = !showChart.value }

async function generate() {
  loading.value = true
  try {
    const res = await kittenApi.generateFinancialReport()
    const d = res.data
    if (d?.success) {
      const fin = d.data?.financial_report?.details
      if (fin?.metrics) m.value = fin.metrics
      if (fin?.product_analysis) products.value = fin.product_analysis
      if (fin?.customer_analysis) customers.value = fin.customer_analysis

      const inv = d.data?.inventory_valuation?.details
      if (inv?.low_stock_alerts) alerts.value = inv.low_stock_alerts

      hasData.value = true
      updateTime.value = new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })

      await nextTick()
      renderChart()
    }
  } catch (e) { console.error(e) }
  finally { loading.value = false }
}

async function renderChart() {
  if (!chartEl.value) return
  await loadECharts()
  const ec = (window as any).echarts
  if (!ec) return

  if (chartInstance) chartInstance.dispose()
  chartInstance = ec.init(chartEl.value)

  try {
    const res = await kittenApi.getRevenueChart(6)
    const d = res.data
    if (!d?.data) return

    chartInstance.setOption({
      grid: { left: 50, right: 20, top: 20, bottom: 30 },
      xAxis: { type: 'category', data: d.data.labels, axisLabel: { fontSize: 11 } },
      yAxis: {
        type: 'value',
        axisLabel: { formatter: (v: number) => (v >= 10000 ? v / 10000 + '万' : v) }
      },
      tooltip: { trigger: 'axis' },
      series: [{
        type: 'bar',
        data: d.data.revenue,
        itemStyle: { color: '#4472C4', borderRadius: [4, 4, 0, 0] },
        barMaxWidth: 40,
      }]
    })
  } catch {}
}

async function doExport() {
  try {
    const res = await kittenApi.exportReport({})
    const blob = new Blob([res.data], { type: 'application/octet-stream' })
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = `小猫财务报告_${new Date().toISOString().slice(0,10)}.xlsx`
    a.click()
    URL.revokeObjectURL(a.href)
  } catch (e) { await appAlert('导出失败：' + e) }
}

onMounted(() => {})
</script>

<style scoped>
.kitten-simple {
  min-height: 100vh;
  background: #f5f7fa;
  font-family: -apple-system, "PingFang SC", "Microsoft YaHei", sans-serif;
  color: #333;
}

/* ====== 顶部 ====== */
.k-header {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 24px 32px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  color: #fff;
}
.k-brand {
  display: flex; gap: 16px; align-items: center;
}
.k-icon {
  font-size: 42px;
}
.k-brand h1 {
  margin: 0; font-size: 22px; font-weight: 700;
}
.k-brand p {
  margin: 2px 0 0; font-size: 13px; opacity: 0.85;
}

/* 按钮 */
.k-btn {
  padding: 12px 28px;
  border-radius: 10px;
  border: none;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  white-space: nowrap;
}
.k-btn-primary {
  background: #fff;
  color: #667eea;
  box-shadow: 0 4px 15px rgba(0,0,0,0.15);
}
.k-btn-primary:hover:not(:disabled) { transform: translateY(-2px); box-shadow: 0 6px 20px rgba(0,0,0,0.2); }
.k-btn-primary:disabled { opacity: 0.6; cursor: not-allowed; }
.k-btn-outline { background: transparent; border: 2px solid #ddd; color: #555; }
.k-btn-outline:hover { border-color: #667eea; color: #667eea; }
.k-btn-ghost { background: transparent; color: #888; font-size: 14px; }
.k-btn-ghost:hover { color: #667eea; }
.k-btn-lg { padding: 16px 48px; font-size: 18px; }
.k-btn-sm {
  padding: 6px 16px;
  font-size: 13px;
  border-radius: 8px;
  background: rgba(255,255,255,0.15);
  color: #fff;
  border: 1px solid rgba(255,255,255,0.3);
  cursor: pointer;
}
.k-btn-sm:hover { background: rgba(255,255,255,0.25); }

/* 加载 */
.k-loading {
  text-align: center; padding: 80px 20px; color: #888;
}
.k-spinner {
  width: 44px; height: 44px;
  border: 4px solid #e0e0e0;
  border-top-color: #667eea;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin: 0 auto 16px;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* 主内容 */
.k-main { max-width: 1100px; margin: 0 auto; padding: 24px; }

/* 指标卡片区 */
.k-metrics {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}
.k-card {
  background: #fff;
  border-radius: 14px;
  padding: 20px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.05);
  transition: transform 0.2s;
}
.k-card:hover { transform: translateY(-3px); }
.k-label { font-size: 13px; color: #888; margin-bottom: 6px; }
.k-value { font-size: 26px; font-weight: 800; margin-bottom: 4px; }
.k-sub { font-size: 12px; color: #aaa; }

.k-card-green .k-value { color: #27ae60; }
.k-card-red .k-value { color: #e74c3c; }
.k-card-blue .k-value { color: #3498db; }
.k-card-orange .k-value { color: #f39c12; }
.k-card-purple .k-value { color: #9b59b6; }
.k-card-teal .k-value { color: #1abc9c; }

/* 图表 */
.k-chart-section {
  background: #fff;
  border-radius: 14px;
  padding: 20px;
  margin-bottom: 24px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.05);
}
.k-section-header {
  display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;
}
.k-section-header h2 { margin: 0; font-size: 17px; }
.k-chart-box { height: 280px; }

/* 表格 */
.k-tables {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
  margin-bottom: 24px;
}
.k-tables > div {
  background: #fff;
  border-radius: 14px;
  padding: 20px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.05);
}
.k-tables h3 { margin: 0 0 14px; font-size: 16px; color: #444; }

.k-table {
  width: 100%; border-collapse: collapse;
}
.k-table td {
  padding: 10px 8px;
  border-bottom: 1px solid #f0f0f0;
  font-size: 14px;
}
.k-rank {
  width: 36px; text-align: center; font-weight: 700; color: #999;
}
.k-money { text-align: right; color: #27ae60; font-weight: 600; font-family: monospace; }
.k-empty { text-align: center; color: #bbb; padding: 24px !important; }

/* 预警 */
.k-alerts {
  background: #fffbe6;
  border-radius: 14px;
  padding: 20px;
  margin-bottom: 24px;
  border-left: 4px solid #ffc107;
}
.k-alerts h3 { margin: 0 0 12px; color: #856404; }
.k-alert-item {
  display: flex; justify-content: space-between;
  padding: 8px 0;
  font-size: 14px;
  border-bottom: 1px dashed #e0c680;
}
.k-alert-item:last-child { border-bottom: none; }

/* 底部操作 */
.k-actions {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 16px;
  padding: 20px;
}
.k-time { font-size: 13px; color: #aaa; }

/* 空状态 */
.k-empty-state {
  text-align: center;
  padding: 100px 20px;
  color: #888;
}
.k-empty-icon { font-size: 72px; margin-bottom: 16px; }
.k-empty-state h2 { margin: 0 0 8px; font-size: 22px; color: #555; }
.k-empty-state p { margin: 0 0 28px; color: #999; }

/* 响应式 */
@media (max-width: 900px) {
  .k-metrics { grid-template-columns: repeat(2, 1fr); }
  .k-tables { grid-template-columns: 1fr; }
  .k-header { flex-direction: column; gap: 16px; text-align: center; }
  .k-brand { flex-direction: column; }
}
@media (max-width: 500px) {
  .k-metrics { grid-template-columns: 1fr; }
  .k-value { font-size: 22px; }
  .k-actions { flex-direction: column; }
}
</style>
