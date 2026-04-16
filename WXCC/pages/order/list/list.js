Page({
  data: {
    orders: [],
    currentStatus: 'all',
    orderTabs: [
      { label: '全部', value: 'all' },
      { label: '待付款', value: 'pending' },
      { label: '待发货', value: 'processing' },
      { label: '待收货', value: 'shipping' },
      { label: '已完成', value: 'completed' }
    ],
    loading: false,
    page: 1,
    pageSize: 10,
    hasMore: true
  },

  onLoad(options) {
    if (options.status) {
      this.setData({ currentStatus: options.status })
    }
    this.loadOrders()
  },

  onPullDownRefresh() {
    this.setData({ page: 1, orders: [], hasMore: true })
    this.loadOrders().finally(() => {
      wx.stopPullDownRefresh()
    })
  },

  onReachBottom() {
    if (this.data.hasMore && !this.data.loading) {
      this.setData({ page: this.data.page + 1 })
      this.loadOrders()
    }
  },

  async loadOrders() {
    if (this.data.loading) return

    this.setData({ loading: true })

    try {
      const { get } = require('../../../utils/request')
      const res = await get('/orders', {
        page: this.data.page,
        per_page: this.data.pageSize,
        status: this.data.currentStatus === 'all' ? '' : this.data.currentStatus
      })

      if (res && res.success) {
        const newOrders = (res.data || []).map(order => this.formatOrder(order))
        const orders = this.data.page === 1 
          ? newOrders 
          : [...this.data.orders, ...newOrders]

        this.setData({
          orders,
          hasMore: newOrders.length === this.data.pageSize
        })
      }
    } catch (error) {
      console.error('加载订单失败', error)
      // 使用模拟数据
      if (this.data.page === 1) {
        this.setMockOrders()
      }
    } finally {
      this.setData({ loading: false })
    }
  },

  formatOrder(order) {
    const statusMap = {
      'pending': { text: '待付款', class: 'status-pending', canCancel: true, canPay: true },
      'processing': { text: '待发货', class: 'status-processing' },
      'shipping': { text: '待收货', class: 'status-shipping', canReceive: true },
      'completed': { text: '已完成', class: 'status-completed' },
      'cancelled': { text: '已取消', class: 'status-cancelled' }
    }

    const statusInfo = statusMap[order.status] || { text: '未知', class: '' }

    return {
      id: order.id,
      orderNumber: order.order_number,
      status: order.status,
      statusText: statusInfo.text,
      statusClass: statusInfo.class,
      products: order.products || [],
      totalPrice: order.total_price || 0,
      createTime: order.create_time,
      canCancel: statusInfo.canCancel || false,
      canPay: statusInfo.canPay || false,
      canReceive: statusInfo.canReceive || false
    }
  },

  setMockOrders() {
    this.setData({
      orders: [
        {
          id: 1,
          orderNumber: 'ORD202401010001',
          status: 'pending',
          statusText: '待付款',
          statusClass: 'status-pending',
          products: [
            {
              name: '26-0200006A PE 白底漆',
              spec: '5L',
              quantity: 2,
              price: 299.00,
              image: '/assets/product/1.jpg'
            }
          ],
          totalPrice: 598.00,
          createTime: '2024-01-01 10:00:00',
          canCancel: true,
          canPay: true
        },
        {
          id: 2,
          orderNumber: 'ORD202401010002',
          status: 'shipping',
          statusText: '待收货',
          statusClass: 'status-shipping',
          products: [
            {
              name: '26-0200008A PU 哑白面固化剂',
              spec: '1L',
              quantity: 3,
              price: 199.00,
              image: '/assets/product/2.jpg'
            }
          ],
          totalPrice: 597.00,
          createTime: '2024-01-01 09:00:00',
          canReceive: true
        }
      ]
    })
  },

  selectTab(e) {
    const status = e.currentTarget.dataset.status
    this.setData({
      currentStatus: status,
      page: 1,
      orders: [],
      hasMore: true
    })
    this.loadOrders()
  },

  goToDetail(e) {
    const orderId = e.currentTarget.dataset.id
    wx.navigateTo({
      url: `/pages/order/detail/detail?id=${orderId}`
    })
  },

  goShopping() {
    wx.switchTab({
      url: '/pages/index/index'
    })
  }
})
