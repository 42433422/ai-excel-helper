Page({
  data: {
    cartItems: [],
    selectAll: false,
    totalPrice: '0.00',
    selectedCount: 0
  },

  onShow() {
    this.loadCart()
  },

  loadCart() {
    const cart = wx.getStorageSync('cart') || []
    const cartItems = cart.map(item => ({
      ...item,
      checked: item.checked !== undefined ? item.checked : true
    }))

    this.setData({ cartItems })
    this.calculateTotal()
  },

  toggleCheck(e) {
    const index = e.currentTarget.dataset.index
    const key = `cartItems[${index}].checked`
    this.setData({
      [key]: !this.data.cartItems[index].checked
    })
    
    // 保存到本地存储
    this.saveCart()
    this.calculateTotal()
  },

  toggleSelectAll() {
    const selectAll = !this.data.selectAll
    const cartItems = this.data.cartItems.map(item => ({
      ...item,
      checked: selectAll
    }))

    this.setData({ 
      cartItems,
      selectAll 
    })

    this.saveCart()
    this.calculateTotal()
  },

  increaseQuantity(e) {
    const index = e.currentTarget.dataset.index
    const key = `cartItems[${index}].quantity`
    this.setData({
      [key]: this.data.cartItems[index].quantity + 1
    })

    this.saveCart()
    this.calculateTotal()
  },

  decreaseQuantity(e) {
    const index = e.currentTarget.dataset.index
    const item = this.data.cartItems[index]
    
    if (item.quantity > 1) {
      const key = `cartItems[${index}].quantity`
      this.setData({
        [key]: item.quantity - 1
      })
      this.saveCart()
      this.calculateTotal()
    } else {
      this.deleteItem(e)
    }
  },

  deleteItem(e) {
    const index = e.currentTarget.dataset.index
    
    wx.showModal({
      title: '提示',
      content: '确定要删除该商品吗？',
      success: (res) => {
        if (res.confirm) {
          const cartItems = this.data.cartItems
          cartItems.splice(index, 1)
          this.setData({ cartItems })
          this.saveCart()
          this.calculateTotal()
        }
      }
    })
  },

  calculateTotal() {
    const selectedItems = this.data.cartItems.filter(item => item.checked)
    const totalPrice = selectedItems.reduce((sum, item) => {
      return sum + item.price * item.quantity
    }, 0)

    this.setData({
      totalPrice: totalPrice.toFixed(2),
      selectedCount: selectedItems.length
    })
  },

  saveCart() {
    const cart = this.data.cartItems.map(({ id, productId, name, price, image, spec, quantity, checked }) => ({
      id,
      productId,
      name,
      price,
      image,
      spec,
      quantity,
      checked
    }))
    
    wx.setStorageSync('cart', cart)
    
    // 更新购物车数量
    const cartCount = cart.reduce((sum, item) => sum + item.quantity, 0)
    wx.setStorageSync('cart_count', cartCount)
  },

  checkout() {
    if (this.data.selectedCount === 0) {
      wx.showToast({
        title: '请选择商品',
        icon: 'none'
      })
      return
    }

    const selectedItems = this.data.cartItems.filter(item => item.checked)
    
    // 跳转到订单确认页
    const orderData = {
      products: selectedItems
    }

    wx.navigateTo({
      url: `/pages/order/confirm/confirm?data=${encodeURIComponent(JSON.stringify(orderData))}`
    })
  },

  goToProduct(e) {
    const productId = e.currentTarget.dataset.id
    wx.navigateTo({
      url: `/pages/product/detail/detail?id=${productId}`
    })
  },

  goShopping() {
    wx.switchTab({
      url: '/pages/index/index'
    })
  }
})
