Page({
  data: {
    orderId: '',
    status: 'success',
    resultTitle: '下单成功',
    resultDesc: '我们会尽快为您发货'
  },

  onLoad(options) {
    if (options.orderId) {
      this.setData({ orderId: options.orderId })
    }
    
    if (options.status === 'fail') {
      this.setData({
        status: 'fail',
        resultTitle: '下单失败',
        resultDesc: '请稍后重试'
      })
    }
  },

  copyOrderId() {
    wx.setClipboardData({
      data: this.data.orderId,
      success: () => {
        wx.showToast({
          title: '已复制',
          icon: 'success'
        })
      }
    })
  },

  goToOrders() {
    wx.navigateTo({
      url: '/pages/order/list/list'
    })
  },

  goToIndex() {
    wx.switchTab({
      url: '/pages/index/index'
    })
  },

  retry() {
    wx.switchTab({
      url: '/pages/index/index'
    })
  }
})
