Page({
  data: {
    keyword: '',
    products: [],
    searchHistory: [],
    hotKeywords: ['涂料', '固化剂', '稀释剂', '底漆', '面漆'],
    searching: false,
    loading: false,
    page: 1,
    pageSize: 20,
    hasMore: true
  },

  onLoad() {
    this.loadSearchHistory()
  },

  loadSearchHistory() {
    const history = wx.getStorageSync('search_history') || []
    this.setData({ searchHistory: history })
  },

  onKeywordInput(e) {
    this.setData({
      keyword: e.detail.value
    })
  },

  clearKeyword() {
    this.setData({ keyword: '' })
  },

  search() {
    const keyword = this.data.keyword.trim()
    if (!keyword) {
      wx.showToast({
        title: '请输入搜索关键词',
        icon: 'none'
      })
      return
    }

    // 保存搜索历史
    this.saveSearchHistory(keyword)

    this.setData({
      searching: true,
      page: 1,
      products: [],
      hasMore: true
    })

    this.searchProducts()
  },

  async searchProducts() {
    if (this.data.loading) return

    this.setData({ loading: true })

    try {
      const { get } = require('../../utils/request')
      const res = await get('/products/list', {
        page: this.data.page,
        per_page: this.data.pageSize,
        keyword: this.data.keyword
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
      console.error('搜索失败', error)
      // 使用模拟数据
      if (this.data.page === 1) {
        this.setMockProducts()
      }
    } finally {
      this.setData({ loading: false })
    }
  },

  setMockProducts() {
    this.setData({
      products: [
        {
          id: 1,
          name: '26-0200006A PE 白底漆',
          description: '高品质环保涂料',
          price: 299.00,
          image: '/assets/product/1.jpg'
        },
        {
          id: 2,
          name: '26-0200008A PU 哑白面固化剂',
          description: '快速固化，持久耐用',
          price: 199.00,
          image: '/assets/product/2.jpg'
        }
      ]
    })
  },

  saveSearchHistory(keyword) {
    let history = this.data.searchHistory
    const index = history.indexOf(keyword)
    
    if (index > -1) {
      history.splice(index, 1)
    }
    
    history.unshift(keyword)
    
    if (history.length > 10) {
      history.pop()
    }
    
    this.setData({ searchHistory: history })
    wx.setStorageSync('search_history', history)
  },

  searchHistory(e) {
    const keyword = e.currentTarget.dataset.keyword
    this.setData({ keyword })
    this.search()
  },

  searchHot(e) {
    const keyword = e.currentTarget.dataset.keyword
    this.setData({ keyword })
    this.search()
  },

  deleteHistory(e) {
    const index = e.currentTarget.dataset.index
    let history = this.data.searchHistory
    history.splice(index, 1)
    this.setData({ searchHistory: history })
    wx.setStorageSync('search_history', history)
  },

  clearHistory() {
    wx.showModal({
      title: '提示',
      content: '确定要清除搜索历史吗？',
      success: (res) => {
        if (res.confirm) {
          this.setData({ searchHistory: [] })
          wx.removeStorageSync('search_history')
        }
      }
    })
  },

  goToProduct(e) {
    const productId = e.currentTarget.dataset.id
    wx.navigateTo({
      url: `/pages/product/detail/detail?id=${productId}`
    })
  },

  onReachBottom() {
    if (this.data.hasMore && !this.data.loading) {
      this.setData({ page: this.data.page + 1 })
      this.searchProducts()
    }
  }
})
