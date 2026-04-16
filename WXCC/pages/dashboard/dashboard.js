const { hybridRecommend, realTimeRecommend } = require('../../utils/recommend')

Page({
  data: {
    // 统计数据
    stats: {
      todaySales: 0,
      orderCount: 0,
      salesTrend: 'up',
      salesTrendText: '+12.5%',
      salesChange: 12.5,
      orderTrend: 'stable',
      orderTrendText: '持平'
    },
    
    // 销售数据
    salesData: [
      { label: '周一', value: 12500, color: '#1890ff' },
      { label: '周二', value: 18900, color: '#52c41a' },
      { label: '周三', value: 15600, color: '#faad14' },
      { label: '周四', value: 23400, color: '#f5222d' },
      { label: '周五', value: 19800, color: '#722ed1' },
      { label: '周六', value: 26700, color: '#13c2c2' },
      { label: '周日', value: 18900, color: '#eb2f96' }
    ],
    
    // 分类数据
    categoryData: [
      { label: '涂料', value: 35, color: '#1890ff' },
      { label: '固化剂', value: 25, color: '#52c41a' },
      { label: '稀释剂', value: 20, color: '#faad14' },
      { label: '助剂', value: 15, color: '#f5222d' },
      { label: '工具', value: 5, color: '#722ed1' }
    ],
    
    // 实时订单
    recentOrders: [
      { id: '1001', time: '14:30:25', status: 'pending', statusText: '待处理' },
      { id: '1002', time: '14:28:10', status: 'shipping', statusText: '配送中' },
      { id: '1003', time: '14:25:45', status: 'completed', statusText: '已完成' },
      { id: '1004', time: '14:22:30', status: 'pending', statusText: '待处理' }
    ],
    
    // 性能数据
    performance: {
      apiResponse: 45,
      memoryUsage: 68,
      concurrentUsers: 234
    },
    
    // 推荐统计
    recommendStats: {
      clickRate: 15.8,
      conversionRate: 3.2,
      avgViewTime: 45
    }
  },

  onLoad() {
    this.startRealTimeUpdates()
    this.loadDashboardData()
  },

  onShow() {
    this.startRealTimeUpdates()
  },

  onHide() {
    this.stopRealTimeUpdates()
  },

  onUnload() {
    this.stopRealTimeUpdates()
  },

  // 实时数据更新
  startRealTimeUpdates() {
    // 销售数据更新
    this.salesInterval = setInterval(() => {
      this.updateSalesData()
    }, 5000)
    
    // 订单数据更新
    this.orderInterval = setInterval(() => {
      this.updateOrderData()
    }, 3000)
    
    // 性能数据更新
    this.performanceInterval = setInterval(() => {
      this.updatePerformanceData()
    }, 10000)
  },

  stopRealTimeUpdates() {
    clearInterval(this.salesInterval)
    clearInterval(this.orderInterval)
    clearInterval(this.performanceInterval)
  },

  // 加载仪表板数据
  async loadDashboardData() {
    try {
      // 模拟API调用
      await this.simulateApiCall()
      
      // 初始化数据
      this.setData({
        'stats.todaySales': 12890,
        'stats.orderCount': 156
      })
      
      // 启动数字动画
      this.animateCounters()
      
    } catch (error) {
      console.error('加载仪表板数据失败', error)
    }
  },

  // 更新销售数据
  updateSalesData() {
    const randomIncrement = Math.floor(Math.random() * 100) + 50
    const currentSales = this.data.stats.todaySales
    
    this.setData({
      'stats.todaySales': currentSales + randomIncrement
    })
  },

  // 更新订单数据
  updateOrderData() {
    const randomOrder = Math.random() > 0.7 ? 1 : 0
    const currentOrders = this.data.stats.orderCount
    
    if (randomOrder > 0) {
      this.setData({
        'stats.orderCount': currentOrders + randomOrder
      })
      
      // 添加新订单到实时监控
      this.addNewOrder()
    }
  },

  // 添加新订单
  addNewOrder() {
    const newOrder = {
      id: String(1000 + this.data.recentOrders.length + 1),
      time: this.getCurrentTime(),
      status: 'pending',
      statusText: '待处理'
    }
    
    const recentOrders = [newOrder, ...this.data.recentOrders.slice(0, 9)]
    this.setData({ recentOrders })
  },

  // 更新性能数据
  updatePerformanceData() {
    const performance = {
      apiResponse: Math.floor(Math.random() * 30) + 20,
      memoryUsage: Math.floor(Math.random() * 20) + 60,
      concurrentUsers: Math.floor(Math.random() * 50) + 200
    }
    
    this.setData({ performance })
  },

  // 数字计数器动画
  animateCounters() {
    const targets = {
      'stats.todaySales': 12890,
      'stats.orderCount': 156,
      'recommendStats.clickRate': 15.8,
      'recommendStats.conversionRate': 3.2,
      'recommendStats.avgViewTime': 45
    }
    
    Object.keys(targets).forEach(key => {
      this.animateValue(key, 0, targets[key], 2000)
    })
  },

  // 数值动画
  animateValue(key, start, end, duration) {
    const startTime = Date.now()
    const animate = () => {
      const currentTime = Date.now()
      const progress = Math.min((currentTime - startTime) / duration, 1)
      
      // 缓动函数
      const easeOut = 1 - Math.pow(1 - progress, 3)
      const currentValue = Math.floor(start + (end - start) * easeOut)
      
      this.setData({
        [key]: currentValue
      })
      
      if (progress < 1) {
        requestAnimationFrame(animate)
      }
    }
    
    animate()
  },

  // 获取当前时间
  getCurrentTime() {
    const now = new Date()
    return now.toTimeString().split(' ')[0]
  },

  // 模拟API调用
  simulateApiCall() {
    return new Promise(resolve => {
      setTimeout(resolve, 500)
    })
  },

  // 刷新数据
  onRefresh() {
    wx.showLoading({ title: '刷新中...' })
    
    this.loadDashboardData().then(() => {
      wx.hideLoading()
      wx.showToast({ title: '刷新成功', icon: 'success' })
    })
  }
})