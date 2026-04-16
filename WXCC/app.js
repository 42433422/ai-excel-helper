App({
  globalData: {
    userInfo: null,
    token: '',
    // 开发环境配置
    baseUrl: 'http://127.0.0.1:8000/api/mp/v1',
    // 生产环境请修改为实际域名
    // baseUrl: 'https://your-domain.com/api/mp/v1',
    isLoggedIn: false,
    systemInfo: null,
  },

  setToken(token) {
    this.globalData.token = token
    this.globalData.isLoggedIn = true
    wx.setStorageSync('mp_token', token)
  },

  clearToken() {
    this.globalData.token = ''
    this.globalData.isLoggedIn = false
    this.globalData.userInfo = null
    wx.removeStorageSync('mp_token')
  },

  showLoading(title = '加载中...') {
    wx.showLoading({
      title: title,
      mask: true
    })
  },

  hideLoading() {
    wx.hideLoading()
  },

  onLaunch() {
    // 初始化系统信息（使用新版 API）
    wx.getSystemInfo({
      success: (res) => {
        this.globalData.systemInfo = res
      }
    })
    
    // 初始化图片缓存
    const { initCache } = require('./utils/image')
    initCache()
    
    // 检查登录状态
    this.checkLoginStatus()
    
    // 初始化云开发（如需要）
    // wx.cloud.init({
    //   env: 'your-env-id',
    //   traceUser: true,
    // })
  },

  checkLoginStatus() {
    const token = wx.getStorageSync('mp_token')
    if (token) {
      this.globalData.token = token
      this.globalData.isLoggedIn = true
      this.getUserInfo()
    }
  },

  getUserInfo() {
    const that = this
    wx.request({
      url: `${this.globalData.baseUrl}/user/info`,
      method: 'GET',
      header: {
        'Authorization': `Bearer ${this.globalData.token}`
      },
      success(res) {
        if (res.data && res.data.success) {
          that.globalData.userInfo = res.data.data
        }
      },
      fail(err) {
        console.error('获取用户信息失败', err)
      }
    })
  },

  setToken(token) {
    this.globalData.token = token
    this.globalData.isLoggedIn = true
    wx.setStorageSync('mp_token', token)
  },

  clearToken() {
    this.globalData.token = ''
    this.globalData.isLoggedIn = false
    this.globalData.userInfo = null
    wx.removeStorageSync('mp_token')
  },

  // 显示提示消息
  showToast(title, icon = 'none', duration = 2000) {
    wx.showToast({
      title,
      icon,
      duration
    })
  },

  // 显示加载提示
  showLoading(title = '加载中') {
    wx.showLoading({
      title,
      mask: true
    })
  },

  // 隐藏加载提示
  hideLoading() {
    wx.hideLoading()
  },
})
