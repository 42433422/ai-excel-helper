Page({
  data: {
    products: [],
    address: null,
    remark: '',
    productTotal: '0.00',
    totalPrice: '0.00'
  },

  onLoad(options) {
    if (options.data) {
      const orderData = JSON.parse(decodeURIComponent(options.data))
      const products = orderData.products || []
      
      this.setData({ 
        products,
        productTotal: this.calculateTotal(products),
        totalPrice: this.calculateTotal(products)
      })
    }
    
    this.loadDefaultAddress()
  },

  calculateTotal(products) {
    const total = products.reduce((sum, item) => {
      return sum + (item.price || 0) * (item.quantity || 1)
    }, 0)
    return total.toFixed(2)
  },

  async loadDefaultAddress() {
    try {
      const { get } = require('../../../utils/request')
      const res = await get('/address/default')

      if (res && res.success && res.data) {
        this.setData({ address: res.data })
      }
    } catch (error) {
      console.error('加载地址失败', error)
      // 使用本地存储的默认地址
      const defaultAddress = wx.getStorageSync('default_address')
      if (defaultAddress) {
        this.setData({ address: defaultAddress })
      }
    }
  },

  selectAddress() {
    wx.navigateTo({
      url: '/pages/my/address/list/list'
    })
  },

  onRemarkInput(e) {
    this.setData({
      remark: e.detail.value
    })
  },

  async submitOrder() {
    // 验证地址
    if (!this.data.address) {
      wx.showToast({
        title: '请选择收货地址',
        icon: 'none'
      })
      return
    }

    // 验证商品
    if (!this.data.products || this.data.products.length === 0) {
      wx.showToast({
        title: '商品不能为空',
        icon: 'none'
      })
      return
    }

    app.showLoading('提交中...')

    try {
      const { post } = require('../../../utils/request')
      const orderData = {
        addressId: this.data.address.id,
        products: this.data.products.map(item => ({
          productId: item.productId || item.id,
          quantity: item.quantity,
          spec: item.spec
        })),
        remark: this.data.remark,
        totalPrice: parseFloat(this.data.totalPrice)
      }

      const res = await post('/orders/create', orderData)

      app.hideLoading()

      if (res && res.success) {
        // 清除购物车中已购买的商品
        this.clearCart()

        // 跳转到订单结果页
        wx.redirectTo({
          url: `/pages/order/result/result?orderId=${res.data.id}&status=success`
        })
      } else {
        wx.showToast({
          title: res.error || '提交失败',
          icon: 'none'
        })
      }
    } catch (error) {
      app.hideLoading()
      console.error('提交订单失败', error)
      wx.showToast({
        title: '提交失败，请稍后重试',
        icon: 'none'
      })
    }
  },

  clearCart() {
    const cart = wx.getStorageSync('cart') || []
    const newCart = cart.filter(item => {
      return !this.data.products.find(p => p.id === item.id && p.spec === item.spec)
    })
    wx.setStorageSync('cart', newCart)
    wx.setStorageSync('cart_count', newCart.reduce((sum, item) => sum + item.quantity, 0))
  }
})
