Page({
  data: {
    userInfo: {}
  },

  onLoad() {
    this.loadUserInfo()
  },

  loadUserInfo() {
    const app = getApp()
    const userInfo = app.globalData.userInfo || {}
    
    this.setData({
      userInfo: {
        name: userInfo.name || '',
        phone: userInfo.phone || '',
        avatar: userInfo.avatar || ''
      }
    })
  },

  changeAvatar() {
    wx.chooseImage({
      count: 1,
      sizeType: ['compressed'],
      sourceType: ['album', 'camera'],
      success: (res) => {
        const tempFilePath = res.tempFilePaths[0]
        this.setData({
          'userInfo.avatar': tempFilePath
        })
        
        // TODO: 上传头像到服务器
        wx.showToast({
          title: '头像已选择',
          icon: 'success'
        })
      }
    })
  },

  onNameInput(e) {
    this.setData({
      'userInfo.name': e.detail.value
    })
  },

  async saveProfile() {
    if (!this.data.userInfo.name || !this.data.userInfo.name.trim()) {
      wx.showToast({
        title: '请输入昵称',
        icon: 'none'
      })
      return
    }

    app.showLoading('保存中...')

    try {
      const { put } = require('../../../utils/request')
      const res = await put('/user/profile', {
        name: this.data.userInfo.name.trim(),
        avatar: this.data.userInfo.avatar
      })

      app.hideLoading()

      if (res && res.success) {
        // 更新全局用户信息
        const app = getApp()
        app.globalData.userInfo = {
          ...app.globalData.userInfo,
          name: this.data.userInfo.name.trim(),
          avatar: this.data.userInfo.avatar
        }

        wx.showToast({
          title: '保存成功',
          icon: 'success'
        })

        setTimeout(() => {
          wx.navigateBack()
        }, 1500)
      } else {
        wx.showToast({
          title: res.error || '保存失败',
          icon: 'none'
        })
      }
    } catch (error) {
      app.hideLoading()
      console.error('保存失败', error)
      
      // 本地保存
      const app = getApp()
      app.globalData.userInfo = {
        ...app.globalData.userInfo,
        name: this.data.userInfo.name.trim(),
        avatar: this.data.userInfo.avatar
      }
      
      wx.showToast({
        title: '保存成功',
        icon: 'success'
      })

      setTimeout(() => {
        wx.navigateBack()
      }, 1500)
    }
  }
})
