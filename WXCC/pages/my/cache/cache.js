Page({
  data: {
    cacheInfo: {
      count: 0,
      size: 0,
      sizeText: '0 B',
      maxSize: 50 * 1024 * 1024,
      maxSizeText: '50.00 MB'
    },
    autoClean: true
  },

  onLoad() {
    this.refreshCacheInfo()
  },

  onShow() {
    this.refreshCacheInfo()
  },

  refreshCacheInfo() {
    const { getCacheInfo } = require('../../../utils/image')
    const cacheInfo = getCacheInfo()
    this.setData({ cacheInfo })
  },

  clearCache() {
    wx.showModal({
      title: '清除缓存',
      content: `确定要清除所有缓存吗？（共 ${this.data.cacheInfo.sizeText}）`,
      success: (res) => {
        if (res.confirm) {
          wx.showLoading({
            title: '清除中...',
            mask: true
          })

          const { clearCache } = require('../../../utils/image')
          clearCache()

          wx.hideLoading()
          
          wx.showToast({
            title: '缓存已清除',
            icon: 'success'
          })

          this.refreshCacheInfo()
        }
      }
    })
  },

  onAutoCleanChange(e) {
    this.setData({
      autoClean: e.detail.value
    })
    
    wx.setStorageSync('auto_clean_cache', e.detail.value)
    
    wx.showToast({
      title: '设置已保存',
      icon: 'success'
    })
  }
})
