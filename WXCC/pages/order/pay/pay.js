Page({
  data: {
    orderId: null,
    orderInfo: {
      orderNo: '',
      productName: '',
      amount: '0.00'
    }
  },

  onLoad(options) {
    if (options.id) {
      this.setData({ orderId: options.id })
      this.loadOrderInfo(options.id)
    }
  },

  async loadOrderInfo(id) {
    try {
      const { get } = require('../../../utils/request')
      const res = await get(`/orders/${id}`)

      if (res && res.success && res.data) {
        this.setData({
          orderInfo: {
            orderNo: res.data.order_no,
            productName: res.data.product_name,
            amount: (res.data.amount / 100).toFixed(2)
          }
        })
      }
    } catch (error) {
      console.error('加载订单信息失败', error)
      // 使用模拟数据
      this.setMockOrderInfo()
    }
  },

  setMockOrderInfo() {
    this.setData({
      orderInfo: {
        orderNo: 'ORD' + Date.now(),
        productName: '测试商品',
        amount: '99.00'
      }
    })
  },

  async startPayment() {
    app.showLoading('正在支付...')

    try {
      const { requestPayment } = require('../../../utils/payment')
      
      await requestPayment({
        orderId: this.data.orderId,
        amount: parseFloat(this.data.orderInfo.amount) * 100,
        description: this.data.orderInfo.productName
      })

      app.hideLoading()

      // 支付成功
      wx.showToast({
        title: '支付成功',
        icon: 'success'
      })

      // 跳转到支付结果页
      setTimeout(() => {
        wx.redirectTo({
          url: `/pages/order/result/result?type=success&id=${this.data.orderId}`
        })
      }, 1500)
    } catch (error) {
      app.hideLoading()
      console.error('支付失败', error)

      if (error.code === 'cancel') {
        wx.showToast({
          title: '已取消支付',
          icon: 'none'
        })
      } else {
        wx.showModal({
          title: '支付失败',
          content: error.message || '支付过程中出现错误',
          showCancel: false
        })
      }
    }
  }
})
