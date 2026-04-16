Page({
  data: {
    userInfo: {},
    isLoggedIn: false,
    orderCount: {
      pending: 0,
      shipping: 0,
      completed: 0,
      refund: 0
    }
  },

  onShow() {
    this.loadUserInfo()
    this.loadOrderCount()
  },

  loadUserInfo() {
    const app = getApp()
    const userInfo = app.globalData.userInfo || {}
    const isLoggedIn = app.globalData.isLoggedIn

    this.setData({
      userInfo,
      isLoggedIn
    })
  },

  async loadOrderCount() {
    try {
      const { get } = require('../../../utils/request')
      const res = await get('/orders/count')

      if (res && res.success) {
        this.setData({ orderCount: res.data || this.data.orderCount })
      }
    } catch (error) {
      console.error('加载订单数量失败', error)
    }
  },

  goToProfile() {
    if (!this.data.isLoggedIn) {
      this.goToLogin()
    } else {
      wx.navigateTo({
        url: '/pages/my/info/info'
      })
    }
  },

  goToLogin() {
    wx.navigateTo({
      url: '/pages/login/login'
    })
  },

  goToOrders() {
    wx.navigateTo({
      url: '/pages/order/list/list'
    })
  },

  goToOrderStatus(e) {
    const status = e.currentTarget.dataset.status
    wx.navigateTo({
      url: `/pages/order/list/list?status=${status}`
    })
  },

  goToAddress() {
    wx.navigateTo({
      url: '/pages/my/address/list/list'
    })
  },

  goToFavorite() {
    wx.navigateTo({
      url: '/pages/my/favorite/favorite'
    })
  },

  goToCoupon() {
    wx.showToast({
      title: '功能开发中',
      icon: 'none'
    })
  },

  goToMessage() {
    wx.navigateTo({
      url: '/pages/message/list/list'
    })
  },

  goToCache() {
    wx.navigateTo({
      url: '/pages/my/cache/cache'
    })
  },

  goToFeedback() {
    wx.showToast({
      title: '功能开发中',
      icon: 'none'
    })
  },

  goToAbout() {
    wx.showToast({
      title: '功能开发中',
      icon: 'none'
    })
  },

  logout() {
    wx.showModal({
      title: '提示',
      content: '确定要退出登录吗？',
      success: (res) => {
        if (res.confirm) {
          const app = getApp()
          app.clearToken()
          this.setData({
            userInfo: {},
            isLoggedIn: false
          })
          wx.showToast({
            title: '已退出登录',
            icon: 'success'
          })
        }
      }
    })
  }
})
