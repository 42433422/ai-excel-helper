Page({
  data: {
    favorites: [],
    loading: false
  },

  onShow() {
    this.loadFavorites()
  },

  onPullDownRefresh() {
    this.loadFavorites().finally(() => {
      wx.stopPullDownRefresh()
    })
  },

  async loadFavorites() {
    this.setData({ loading: true })

    try {
      const { get } = require('../../../utils/request')
      const res = await get('/favorites/list')

      if (res && res.success) {
        this.setData({ favorites: res.data || [] })
      }
    } catch (error) {
      console.error('加载收藏失败', error)
      // 使用本地收藏数据
      this.loadLocalFavorites()
    } finally {
      this.setData({ loading: false })
    }
  },

  loadLocalFavorites() {
    const { getFavorites } = require('../../../utils/favorite')
    this.setData({
      favorites: getFavorites()
    })
  },

  goToProduct(e) {
    const productId = e.currentTarget.dataset.id
    wx.navigateTo({
      url: `/pages/product/detail/detail?id=${productId}`
    })
  },

  async addToCart(e) {
    const productId = e.currentTarget.dataset.id
    const product = this.data.favorites.find(item => item.id === productId)

    if (!product) return

    app.showLoading('添加中...')

    try {
      const { post } = require('../../../utils/request')
      await post('/cart/add', {
        product_id: productId,
        quantity: 1
      })

      app.hideLoading()
      wx.showToast({
        title: '已加入购物车',
        icon: 'success'
      })
    } catch (error) {
      app.hideLoading()
      console.error('加入购物车失败', error)
      
      // 本地添加
      let cart = wx.getStorageSync('cart') || []
      const exists = cart.find(item => item.product_id === productId)
      
      if (exists) {
        exists.quantity += 1
      } else {
        cart.push({
          product_id: productId,
          name: product.name,
          image: product.image,
          price: product.price,
          quantity: 1
        })
      }
      
      wx.setStorageSync('cart', cart)
      
      wx.showToast({
        title: '已加入购物车',
        icon: 'success'
      })
    }
  },

  async removeFavorite(e) {
    const productId = e.currentTarget.dataset.id

    try {
      const { del } = require('../../../utils/request')
      await del(`/favorites/${productId}`)

      // 重新加载列表
      this.loadFavorites()

      wx.showToast({
        title: '已取消收藏',
        icon: 'success'
      })
    } catch (error) {
      console.error('取消收藏失败', error)
      
      // 本地取消
      const { removeFavorite } = require('../../../utils/favorite')
      removeFavorite(productId)
      this.loadLocalFavorites()

      wx.showToast({
        title: '已取消收藏',
        icon: 'success'
      })
    }
  },

  goShopping() {
    wx.switchTab({
      url: '/pages/index/index'
    })
  }
})
