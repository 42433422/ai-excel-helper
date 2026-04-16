Page({
  data: {
    addressId: null,
    formData: {
      name: '',
      phone: '',
      region: '',
      detail: '',
      isDefault: false
    }
  },

  onLoad(options) {
    if (options.id) {
      this.setData({ addressId: options.id })
      this.loadAddress(options.id)
    }
  },

  async loadAddress(id) {
    try {
      const { get } = require('../../../../utils/request')
      const res = await get(`/address/${id}`)

      if (res && res.success && res.data) {
        const data = res.data
        this.setData({
          formData: {
            name: data.name || '',
            phone: data.phone || '',
            region: data.region || '',
            detail: data.detail || '',
            isDefault: data.is_default || false
          }
        })
      }
    } catch (error) {
      console.error('加载地址失败', error)
      // 使用模拟数据
      this.setMockAddress()
    }
  },

  setMockAddress() {
    this.setData({
      formData: {
        name: '张三',
        phone: '13800138000',
        region: '北京市朝阳区',
        detail: '某某街道某某小区 1 号楼 1 单元 101 室',
        isDefault: true
      }
    })
  },

  onNameInput(e) {
    this.setData({
      'formData.name': e.detail.value
    })
  },

  onPhoneInput(e) {
    this.setData({
      'formData.phone': e.detail.value
    })
  },

  pickRegion() {
    // TODO: 实现地区选择器
    wx.showToast({
      title: '功能开发中',
      icon: 'none'
    })
  },

  onDetailInput(e) {
    this.setData({
      'formData.detail': e.detail.value
    })
  },

  onDefaultChange(e) {
    this.setData({
      'formData.isDefault': e.detail.value
    })
  },

  validateForm() {
    const { name, phone, region, detail } = this.data.formData

    if (!name.trim()) {
      wx.showToast({
        title: '请填写收货人姓名',
        icon: 'none'
      })
      return false
    }

    if (!phone.trim()) {
      wx.showToast({
        title: '请填写手机号码',
        icon: 'none'
      })
      return false
    }

    if (!/^1[3-9]\d{9}$/.test(phone)) {
      wx.showToast({
        title: '请输入正确的手机号',
        icon: 'none'
      })
      return false
    }

    if (!region.trim()) {
      wx.showToast({
        title: '请选择所在地区',
        icon: 'none'
      })
      return false
    }

    if (!detail.trim()) {
      wx.showToast({
        title: '请填写详细地址',
        icon: 'none'
      })
      return false
    }

    return true
  },

  async saveAddress() {
    if (!this.validateForm()) return

    app.showLoading('保存中...')

    try {
      const { post, put } = require('../../../../utils/request')
      const url = this.data.addressId 
        ? `/address/${this.data.addressId}`
        : '/address/create'
      const method = this.data.addressId ? put : post

      const res = await method(url, this.data.formData)

      app.hideLoading()

      if (res && res.success) {
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
      let addresses = wx.getStorageSync('addresses') || []
      
      if (this.data.addressId) {
        const index = addresses.findIndex(item => item.id === this.data.addressId)
        if (index > -1) {
          addresses[index] = { id: this.data.addressId, ...this.data.formData }
        }
      } else {
        const newId = addresses.length > 0 
          ? Math.max(...addresses.map(item => item.id)) + 1 
          : 1
        addresses.push({ id: newId, ...this.data.formData })
      }
      
      wx.setStorageSync('addresses', addresses)
      
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
