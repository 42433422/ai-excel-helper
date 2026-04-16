Page({
  data: {
    banners: [],
    categories: [],
    notice: [],
    products: [],
    loading: false,
    hasMore: true,
    page: 1,
    pageSize: 10
  },

  onLoad() {
    this.loadCategories()
    this.loadBanners()
    this.loadNotice()
    this.loadProducts()
  },

  onPullDownRefresh() {
    this.setData({ page: 1, products: [], hasMore: true })
    Promise.all([
      this.loadBanners(),
      this.loadNotice(),
      this.loadProducts()
    ]).finally(() => {
      wx.stopPullDownRefresh()
    })
  },

  onReachBottom() {
    if (this.data.hasMore && !this.data.loading) {
      this.setData({ page: this.data.page + 1 })
      this.loadProducts()
    }
  },

  async loadCategories() {
    try {
      const { get } = require('../../utils/request')
      const res = await get('/categories')
      
      if (res && res.success) {
        this.setData({
          categories: res.data
        })
      }
    } catch (error) {
      console.error('加载分类失败', error)
      this.setData({
        categories: [
          { id: 1, name: '全部', icon: 'https://placehold.co/100x100/1890ff/ffffff?text=All' },
          { id: 2, name: '涂料', icon: 'https://placehold.co/100x100/1890ff/ffffff?text=Paint' },
          { id: 3, name: '固化剂', icon: 'https://placehold.co/100x100/1890ff/ffffff?text=Curing' },
          { id: 4, name: '稀释剂', icon: 'https://placehold.co/100x100/1890ff/ffffff?text=Diluent' },
          { id: 5, name: '助剂', icon: 'https://placehold.co/100x100/1890ff/ffffff?text=Auxiliary' },
          { id: 6, name: '工具', icon: 'https://placehold.co/100x100/1890ff/ffffff?text=Tool' }
        ]
      })
    }
  },

  async loadBanners() {
    try {
      const { get } = require('../../utils/request')
      const res = await get('/banners')
      
      if (res && res.success) {
        this.setData({
          banners: res.data
        })
      }
    } catch (error) {
      console.error('加载轮播图失败', error)
      this.setData({
        banners: [
          { id: 1, image: 'https://placehold.co/750x400/1890ff/ffffff?text=Banner+1', url: '' },
          { id: 2, image: 'https://placehold.co/750x400/096dd9/ffffff?text=Banner+2', url: '' },
          { id: 3, image: 'https://placehold.co/750x400/1890ff/ffffff?text=Banner+3', url: '' }
        ]
      })
    }
  },

  async loadNotice() {
    // TODO: 从后端加载公告
    this.setData({
      notice: ['欢迎使用 XCAGI 智能采购商城', '新品上市，欢迎选购']
    })
  },

  async loadProducts() {
    if (this.data.loading) return

    this.setData({ loading: true })

    try {
      const { get } = require('../../utils/request')
      const res = await get('/products/list', {
        page: this.data.page,
        per_page: this.data.pageSize
      })

      if (res && res.success) {
        const newProducts = res.data || []
        const products = this.data.page === 1 
          ? newProducts 
          : [...this.data.products, ...newProducts]

        this.setData({
          products,
          hasMore: newProducts.length === this.data.pageSize
        })
      } else {
        wx.showToast({
          title: '加载失败',
          icon: 'none'
        })
      }
    } catch (error) {
      console.error('加载商品失败', error)
      if (this.data.page === 1) {
        // 模拟数据
        this.setData({
          products: this.getMockProducts()
        })
      }
    } finally {
      this.setData({ loading: false })
    }
  },

  getMockProducts() {
    return [
      {
        id: 1,
        name: '26-0200006A PE 白底漆',
        description: '高品质环保涂料',
        price: 299.00,
        sales: 1234,
        image: 'https://placehold.co/400x400/1890ff/ffffff?text=Product+1'
      },
      {
        id: 2,
        name: '26-0200008A PU 哑白面固化剂',
        description: '快速固化，持久耐用',
        price: 199.00,
        sales: 856,
        image: 'https://placehold.co/400x400/1890ff/ffffff?text=Product+2'
      },
      {
        id: 3,
        name: '26-0200010A PU 实木透明底漆',
        description: '透明度高，附着力强',
        price: 399.00,
        sales: 567,
        image: 'https://placehold.co/400x400/1890ff/ffffff?text=Product+3'
      },
      {
        id: 4,
        name: '26-0200014A PE 白底漆',
        description: '优质基材保护',
        price: 329.00,
        sales: 432,
        image: 'https://placehold.co/400x400/1890ff/ffffff?text=Product+4'
      }
    ]
  },

  goToSearch() {
    wx.navigateTo({ url: '/pages/search/search' })
  },

  goToCategory(e) {
    const categoryId = e.currentTarget.dataset.id
    wx.navigateTo({ 
      url: `/pages/category/category?categoryId=${categoryId}`
    })
  },

  goToNotice(e) {
    // TODO: 跳转到公告详情
    wx.showToast({
      title: '公告详情',
      icon: 'none'
    })
  },

  goToProductDetail(e) {
    const productId = e.currentTarget.dataset.id
    wx.navigateTo({ 
      url: `/pages/product/detail/detail?id=${productId}`
    })
  },

  goToRecommend() {
    // TODO: 跳转到推荐商品列表
    wx.navigateTo({ url: '/pages/category/category?tag=recommend' })
  },

  goToBanner(e) {
    const url = e.currentTarget.dataset.url
    if (url) {
      wx.navigateTo({ url })
    }
  }
})
