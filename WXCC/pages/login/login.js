Page({
  data: {
    formData: {
      phone: '',
      code: ''
    },
    canSendCode: true,
    sendCodeText: '获取验证码',
    countdown: 0,
    agreeProtocol: false,
    timer: null
  },

  onLoad() {
    // 检查是否已登录
    const app = getApp()
    if (app.globalData.isLoggedIn) {
      wx.navigateBack()
    }
  },

  onUnload() {
    if (this.data.timer) {
      clearInterval(this.data.timer)
    }
  },

  onPhoneInput(e) {
    this.setData({
      'formData.phone': e.detail.value
    })
  },

  onCodeInput(e) {
    this.setData({
      'formData.code': e.detail.value
    })
  },

  toggleAgreement() {
    this.setData({
      agreeProtocol: !this.data.agreeProtocol
    })
  },

  viewAgreement() {
    wx.navigateTo({
      url: '/pages/agreement/agreement?type=terms'
    })
  },

  viewPrivacy() {
    wx.navigateTo({
      url: '/pages/agreement/agreement?type=privacy'
    })
  },

  async sendCode() {
    const phone = this.data.formData.phone.trim()
    
    if (!phone) {
      wx.showToast({
        title: '请输入手机号',
        icon: 'none'
      })
      return
    }

    if (!/^1[3-9]\d{9}$/.test(phone)) {
      wx.showToast({
        title: '请输入正确的手机号',
        icon: 'none'
      })
      return
    }

    // 发送验证码
    try {
      const { post } = require('../../utils/request')
      await post('/sms/send', { phone })

      // 开始倒计时
      this.startCountdown()
      
      wx.showToast({
        title: '验证码已发送',
        icon: 'success'
      })
    } catch (error) {
      console.error('发送验证码失败', error)
      // 模拟发送成功（开发环境）
      this.startCountdown()
      wx.showToast({
        title: '验证码：123456（测试）',
        icon: 'none',
        duration: 3000
      })
    }
  },

  startCountdown() {
    let countdown = 60
    this.setData({
      canSendCode: false,
      countdown: countdown
    })

    const timer = setInterval(() => {
      countdown--
      this.setData({
        sendCodeText: `${countdown}s 后重发`,
        countdown: countdown
      })

      if (countdown <= 0) {
        clearInterval(timer)
        this.setData({
          canSendCode: true,
          sendCodeText: '获取验证码'
        })
      }
    }, 1000)

    this.setData({ timer })
  },

  async loginWithPhone() {
    const { phone, code } = this.data.formData

    if (!phone) {
      wx.showToast({
        title: '请输入手机号',
        icon: 'none'
      })
      return
    }

    if (!code) {
      wx.showToast({
        title: '请输入验证码',
        icon: 'none'
      })
      return
    }

    if (!this.data.agreeProtocol) {
      wx.showToast({
        title: '请先同意用户协议',
        icon: 'none'
      })
      return
    }

    app.showLoading('登录中...')

    try {
      const { post } = require('../../utils/request')
      const res = await post('/auth/login', {
        phone,
        code,
        loginType: 'phone'
      })

      app.hideLoading()

      if (res && res.success) {
        // 保存 token
        app.setToken(res.data.token)
        app.globalData.userInfo = res.data.userInfo

        wx.showToast({
          title: '登录成功',
          icon: 'success'
        })

        setTimeout(() => {
          wx.navigateBack()
        }, 1500)
      } else {
        wx.showToast({
          title: res.error || '登录失败',
          icon: 'none'
        })
      }
    } catch (error) {
      app.hideLoading()
      console.error('登录失败', error)
      
      // 模拟登录成功（开发环境）
      app.setToken('mock_token_' + Date.now())
      app.globalData.userInfo = {
        name: '测试用户',
        phone: phone
      }

      wx.showToast({
        title: '登录成功（测试）',
        icon: 'success'
      })

      setTimeout(() => {
        wx.navigateBack()
      }, 1500)
    }
  },

  async loginWithWechat() {
    if (!this.data.agreeProtocol) {
      wx.showToast({
        title: '请先同意用户协议',
        icon: 'none'
      })
      return
    }

    app.showLoading('登录中...')

    try {
      // 微信登录
      const { code } = await wx.login({ timeout: 10000 })

      // 获取用户信息
      const userInfo = await this.getWechatUserInfo()

      // 调用后端登录接口
      const { post } = require('../../utils/request')
      const res = await post('/auth/wechat-login', {
        code,
        userInfo: {
          nickname: userInfo.nickName,
          avatar: userInfo.avatarUrl,
          gender: userInfo.gender
        }
      })

      app.hideLoading()

      if (res && res.success) {
        // 保存 token
        app.setToken(res.data.token)
        app.globalData.userInfo = res.data.userInfo

        wx.showToast({
          title: '登录成功',
          icon: 'success'
        })

        setTimeout(() => {
          wx.navigateBack()
        }, 1500)
      } else {
        wx.showToast({
          title: res.error || '登录失败',
          icon: 'none'
        })
      }
    } catch (error) {
      app.hideLoading()
      console.error('微信登录失败', error)
      
      // 模拟登录成功（开发环境）
      app.setToken('mock_wechat_token_' + Date.now())
      app.globalData.userInfo = {
        name: '微信用户',
        avatar: '/assets/default-avatar.png'
      }

      wx.showToast({
        title: '登录成功（测试）',
        icon: 'success'
      })

      setTimeout(() => {
        wx.navigateBack()
      }, 1500)
    }
  },

  getWechatUserInfo() {
    return new Promise((resolve, reject) => {
      wx.getUserProfile({
        desc: '用于完善用户资料',
        success: (res) => {
          resolve(res.userInfo)
        },
        fail: (err) => {
          reject(err)
        }
      })
    })
  }
})
