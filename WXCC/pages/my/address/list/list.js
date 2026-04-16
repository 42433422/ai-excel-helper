Page({
  data: {
    addresses: [],
    isSelectMode: false
  },

  onLoad(options) {
    if (options.selectMode === 'true') {
      this.setData({ isSelectMode: true })
    }
    this.loadAddresses()
  },

  async loadAddresses() {
    try {
      const { get } = require('../../../../utils/request')
      const res = await get('/address/list')

      if (res && res.success) {
        this.setData({ addresses: res.data || [] })
      }
    } catch (error) {
      console.error('加载地址失败', error)
      // 使用模拟数据
      this.setMockAddresses()
    }
  },

  setMockAddresses() {
    this.setData({
      addresses: [
        {
          id: 1,
          name: '张三',
          phone: '13800138000',
          detail: '北京市朝阳区某某街道某某小区 1 号楼 1 单元 101 室',
          isDefault: true
        },
        {
          id: 2,
          name: '李四',
          phone: '13900139000',
          detail: '上海市浦东新区某某路某某大厦 A 座 2001 室',
          isDefault: false
        }
      ]
    })
  },

  selectAddress(e) {
    if (!this.data.isSelectMode) return

    const addressId = e.currentTarget.dataset.id
    const address = this.data.addresses.find(item => item.id === addressId)

    // 设置默认地址
    wx.setStorageSync('default_address', address)

    // 返回上一页
    wx.navigateBack()
  },

  editAddress(e) {
    const addressId = e.currentTarget.dataset.id
    wx.navigateTo({
      url: `/pages/my/address/edit/edit?id=${addressId}`
    })
  },

  deleteAddress(e) {
    const addressId = e.currentTarget.dataset.id

    wx.showModal({
      title: '提示',
      content: '确定要删除该地址吗？',
      success: async (res) => {
        if (res.confirm) {
          try {
            const { del } = require('../../../../utils/request')
            const response = await del(`/address/${addressId}`)

            if (response && response.success) {
              this.loadAddresses()
              wx.showToast({
                title: '删除成功',
                icon: 'success'
              })
            }
          } catch (error) {
            console.error('删除失败', error)
            // 本地删除
            let addresses = this.data.addresses
            addresses = addresses.filter(item => item.id !== addressId)
            this.setData({ addresses })
            wx.showToast({
              title: '删除成功',
              icon: 'success'
            })
          }
        }
      }
    })
  },

  addAddress() {
    wx.navigateTo({
      url: '/pages/my/address/edit/edit'
    })
  }
})
