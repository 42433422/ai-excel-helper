Page({
  data: {
    productId: '',
    product: {
      id: '',
      name: '',
      description: '',
      price: 0,
      originalPrice: null,
      images: [],
      sales: 0,
      stock: 0,
      brand: '',
      specs: [],
      detail: ''
    },
    selectedSpec: '',
    cartCount: 0,
    loading: false
  },

  onLoad(options) {
    this.setData({ productId: options.id })
    this.loadProductDetail()
    this.loadCartCount()
  },

  onShareAppMessage() {
    const { shareProduct } = require('../../../utils/share')
    return shareProduct(this.data.product)
  },

  async loadProductDetail() {
    this.setData({ loading: true })

    try {
      const { get } = require('../../../utils/request')
      const res = await get(`/products/${this.data.productId}`)

      if (res && res.success) {
        const product = res.data
        this.setData({
          product: {
            id: product.id,
            name: product.product_name || product.name,
            description: product.description || '',
            price: product.price || 0,
            originalPrice: product.original_price || null,
            images: product.images || ['/assets/product/default.jpg'],
            sales: product.sales || 0,
            stock: product.stock || 999,
            brand: product.brand || '未知',
            specs: product.specs || [],
            detail: product.detail || ''
          },
          selectedSpec: product.specs && product.specs.length > 0 ? product.specs[0] : ''
        })
      } else {
        wx.showToast({
          title: '加载失败',
          icon: 'none'
        })
      }
    } catch (error) {
      console.error('加载商品详情失败', error)
      // 使用模拟数据
      this.setMockProduct()
    } finally {
      this.setData({ loading: false })
    }
  },

  setMockProduct() {
    this.setData({
      product: {
        id: this.data.productId,
        name: '26-0200006A PE 白底漆',
        description: '高品质环保涂料，适用于各种木材表面',
        price: 299.00,
        originalPrice: 399.00,
        images: ['/assets/product/1.jpg', '/assets/product/1-2.jpg'],
        sales: 1234,
        stock: 999,
        brand: 'XCAGI',
        specs: ['1L', '5L', '10L'],
        detail: '<div>商品详情内容</div>'
      }
    })
  },

  loadCartCount() {
    // TODO: 从本地存储或后端获取购物车数量
    const cartCount = wx.getStorageSync('cart_count') || 0
    this.setData({ cartCount })
  },

  previewImage(e) {
    const index = e.currentTarget.dataset.index
    wx.previewImage({
      urls: this.data.product.images,
      current: index
    })
  },

  selectSpec(e) {
    const spec = e.currentTarget.dataset.spec
    this.setData({ selectedSpec: spec })
  },

  addToCart() {
    if (!this.data.selectedSpec && this.data.product.specs.length > 0) {
      wx.showToast({
        title: '请选择规格',
        icon: 'none'
      })
      return
    }

    // TODO: 添加到购物车
    const cartItem = {
      productId: this.data.product.id,
      name: this.data.product.name,
      price: this.data.product.price,
      image: this.data.product.images[0],
      spec: this.data.selectedSpec,
      quantity: 1
    }

    // 保存到本地存储
    let cart = wx.getStorageSync('cart') || []
    const existIndex = cart.findIndex(item => 
      item.productId === cartItem.productId && item.spec === cartItem.spec
    )

    if (existIndex > -1) {
      cart[existIndex].quantity += 1
    } else {
      cart.push(cartItem)
    }

    wx.setStorageSync('cart', cart)
    this.setData({ cartCount: cart.reduce((sum, item) => sum + item.quantity, 0) })
    
    wx.showToast({
      title: '已加入购物车',
      icon: 'success'
    })
  },

  buyNow() {
    if (!this.data.selectedSpec && this.data.product.specs.length > 0) {
      wx.showToast({
        title: '请选择规格',
        icon: 'none'
      })
      return
    }

    // 跳转到订单确认页
    const orderData = {
      products: [{
        productId: this.data.product.id,
        name: this.data.product.name,
        price: this.data.product.price,
        image: this.data.product.images[0],
        spec: this.data.selectedSpec,
        quantity: 1
      }]
    }

    wx.navigateTo({
      url: `/pages/order/confirm/confirm?data=${encodeURIComponent(JSON.stringify(orderData))}`
    })
  },

  goToCart() {
    wx.switchTab({
      url: '/pages/cart/cart'
    })
  }
})
