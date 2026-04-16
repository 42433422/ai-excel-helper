Page({
  data: {
    orderId: null,
    orderInfo: {
      orderNo: '',
      status: 0,
      statusText: '',
      statusDesc: '',
      createTime: '',
      paymentMethod: '',
      productAmount: '0.00',
      freight: 0,
      totalAmount: '0.00'
    },
    products: [],
    address: null,
    showActions: false,
    showLogistics: false,
    showReview: false,
    showPay: false,
    showCancel: false,
    showDelete: false,
    showLogisticsBtn: false,
    showReviewBtn: false
  },

  onLoad(options) {
    if (options.id) {
      this.setData({ orderId: options.id })
      this.loadOrderDetail(options.id)
    }
  },

  async loadOrderDetail(id) {
    try {
      const { get } = require('../../../utils/request')
      const res = await get(`/orders/${id}`)

      if (res && res.success && res.data) {
        const order = res.data
        this.setData({
          orderInfo: {
            orderNo: order.order_no,
            status: order.status,
            statusText: this.getStatusText(order.status),
            statusDesc: order.status_desc || '',
            createTime: order.create_time,
            paymentMethod: order.payment_method || '未支付',
            productAmount: (order.product_amount / 100).toFixed(2),
            freight: order.freight ? (order.freight / 100).toFixed(2) : '0.00',
            totalAmount: (order.total_amount / 100).toFixed(2)
          },
          products: order.products || [],
          address: order.address
        })

        // 根据订单状态显示操作按钮
        this.updateActionButtons(order.status)
      }
    } catch (error) {
      console.error('加载订单详情失败', error)
      // 使用模拟数据
      this.setMockOrderDetail()
    }
  },

  setMockOrderDetail() {
    this.setData({
      orderInfo: {
        orderNo: 'ORD' + Date.now(),
        status: 1,
        statusText: '待支付',
        statusDesc: '订单等待支付，请尽快完成支付',
        createTime: '2024-01-10 10:30',
        paymentMethod: '微信支付',
        productAmount: '99.00',
        freight: '0.00',
        totalAmount: '99.00'
      },
      products: [
        {
          id: 1,
          name: '测试商品',
          spec: '规格：标准版',
          image: '/assets/product/default.jpg',
          price: '99.00',
          quantity: 1
        }
      ],
      address: {
        name: '张三',
        phone: '13800138000',
        detail: '北京市朝阳区某某街道某某小区 1 号楼 1 单元 101 室'
      }
    })

    this.updateActionButtons(1)
  },

  getStatusText(status) {
    const statusMap = {
      0: '已取消',
      1: '待支付',
      2: '待发货',
      3: '待收货',
      4: '已完成',
      5: '已退款'
    }
    return statusMap[status] || '未知状态'
  },

  updateActionButtons(status) {
    const buttons = {
      showActions: false,
      showLogistics: false,
      showReview: false,
      showPay: false,
      showCancel: false,
      showDelete: false,
      showLogisticsBtn: false,
      showReviewBtn: false
    }

    switch (status) {
      case 1: // 待支付
        buttons.showActions = true
        buttons.showPay = true
        buttons.showCancel = true
        break
      case 2: // 待发货
        buttons.showLogisticsBtn = true
        buttons.showCancel = true
        break
      case 3: // 待收货
        buttons.showLogistics = true
        buttons.showLogisticsBtn = true
        break
      case 4: // 已完成
        buttons.showReview = true
        buttons.showReviewBtn = true
        buttons.showDelete = true
        break
      case 0: // 已取消
      case 5: // 已退款
        buttons.showDelete = true
        break
    }

    this.setData(buttons)
  },

  async payOrder() {
    if (!this.data.orderId) return

    wx.navigateTo({
      url: `/pages/order/pay/pay?id=${this.data.orderId}`
    })
  },

  async cancelOrder() {
    wx.showModal({
      title: '取消订单',
      content: '确定要取消该订单吗？',
      success: async (res) => {
        if (res.confirm) {
          try {
            app.showLoading('取消中...')
            const { post } = require('../../../utils/request')
            await post('/orders/cancel', { order_id: this.data.orderId })
            app.hideLoading()

            wx.showToast({
              title: '订单已取消',
              icon: 'success'
            })

            setTimeout(() => {
              wx.navigateBack()
            }, 1500)
          } catch (error) {
            app.hideLoading()
            console.error('取消订单失败', error)
            wx.showToast({
              title: '取消失败',
              icon: 'none'
            })
          }
        }
      }
    })
  },

  async deleteOrder() {
    wx.showModal({
      title: '删除订单',
      content: '确定要删除该订单吗？',
      success: async (res) => {
        if (res.confirm) {
          try {
            app.showLoading('删除中...')
            const { del } = require('../../../utils/request')
            await del(`/orders/${this.data.orderId}`)
            app.hideLoading()

            wx.showToast({
              title: '订单已删除',
              icon: 'success'
            })

            setTimeout(() => {
              wx.navigateBack()
            }, 1500)
          } catch (error) {
            app.hideLoading()
            console.error('删除订单失败', error)
            wx.showToast({
              title: '删除失败',
              icon: 'none'
            })
          }
        }
      }
    })
  },

  viewLogistics() {
    wx.navigateTo({
      url: `/pages/order/logistics/logistics?id=${this.data.orderId}`
    })
  },

  writeReview() {
    wx.navigateTo({
      url: `/pages/order/review/review?id=${this.data.orderId}`
    })
  },

  contactSeller() {
    // TODO: 联系客服功能
    wx.showToast({
      title: '客服功能开发中',
      icon: 'none'
    })
  }
})
