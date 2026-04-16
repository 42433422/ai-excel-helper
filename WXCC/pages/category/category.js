Page({
  data: {
    categories: [],
    products: [],
    currentCategory: 0,
    loading: false,
    hasMore: true,
    page: 1,
    pageSize: 20
  },

  onLoad(options) {
    if (options.categoryId) {
      this.setData({ currentCategory: parseInt(options.categoryId) })
    }
    this.loadCategories()
    this.loadProducts()
  },

  async loadCategories() {
    // 使用 Mock 数据
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
      // 使用模拟数据
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

  async loadProducts() {
    if (this.data.loading) return

    this.setData({ loading: true })

    try {
      const { get } = require('../../utils/request')
      const res = await get('/products/list', {
        page: this.data.page,
        per_page: this.data.pageSize,
        category: this.data.currentCategory
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
      }
    } catch (error) {
      console.error('加载商品失败', error)
      // 使用模拟数据
      if (this.data.page === 1) {
        this.setMockProducts()
      }
    } finally {
      this.setData({ loading: false })
    }
  },

  setMockProducts() {
    const mockProducts = [
      {
        id: 1,
        name: '26-0200006A PE 白底漆',
        description: '高品质环保涂料',
        price: 299.00,
        image: 'https://placehold.co/400x400/f5f5f5/999999?text=Product+1'
      },
      {
        id: 2,
        name: '26-0200008A PU 哑白面固化剂',
        description: '快速固化，持久耐用',
        price: 199.00,
        image: 'https://placehold.co/400x400/f5f5f5/999999?text=Product+2'
      }
    ]

    this.setData({ products: mockProducts })
  },

  selectCategory(e) {
    const categoryId = e.currentTarget.dataset.id
    this.setData({
      currentCategory: categoryId,
      page: 1,
      products: [],
      hasMore: true
    })
    this.loadProducts()
  },

  loadMore() {
    if (this.data.hasMore && !this.data.loading) {
      this.setData({ page: this.data.page + 1 })
      this.loadProducts()
    }
  },

  goToProduct(e) {
    const productId = e.currentTarget.dataset.id
    wx.navigateTo({
      url: `/pages/product/detail/detail?id=${productId}`
    })
  }
})
