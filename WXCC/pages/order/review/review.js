Page({
  data: {
    orderId: null,
    orderInfo: {
      orderNo: '',
      productName: ''
    },
    rating: 0,
    ratingText: '请评分',
    comment: '',
    commentLength: 0,
    images: [],
    isAnonymous: false
  },

  onLoad(options) {
    if (options.id) {
      this.setData({ orderId: options.id })
      this.loadOrderInfo(options.id)
    }
  },

  async loadOrderInfo(id) {
    try {
      const { get } = require('../../../utils/request')
      const res = await get(`/orders/${id}`)

      if (res && res.success && res.data) {
        this.setData({
          orderInfo: {
            orderNo: res.data.order_no,
            productName: res.data.product_name
          }
        })
      }
    } catch (error) {
      console.error('加载订单信息失败', error)
      // 使用模拟数据
      this.setMockOrderInfo()
    }
  },

  setMockOrderInfo() {
    this.setData({
      orderInfo: {
        orderNo: 'ORD' + Date.now(),
        productName: '测试商品'
      }
    })
  },

  selectRating(e) {
    const rating = e.currentTarget.dataset.value
    const ratingTexts = ['非常差', '差', '一般', '好', '非常好']
    
    this.setData({
      rating: rating,
      ratingText: ratingTexts[rating - 1]
    })
  },

  onCommentInput(e) {
    this.setData({
      comment: e.detail.value,
      commentLength: e.detail.value.length
    })
  },

  onAnonymousChange(e) {
    this.setData({
      isAnonymous: e.detail.value
    })
  },

  addImage() {
    const maxCount = 9 - this.data.images.length
    
    wx.chooseImage({
      count: maxCount,
      sizeType: ['compressed'],
      sourceType: ['album', 'camera'],
      success: (res) => {
        const tempFilePaths = res.tempFilePaths
        this.setData({
          images: [...this.data.images, ...tempFilePaths]
        })
      }
    })
  },

  deleteImage(e) {
    const index = e.currentTarget.dataset.index
    const images = this.data.images
    images.splice(index, 1)
    this.setData({ images })
  },

  validateReview() {
    if (this.data.rating === 0) {
      wx.showToast({
        title: '请先评分',
        icon: 'none'
      })
      return false
    }

    if (!this.data.comment.trim()) {
      wx.showToast({
        title: '请填写评价内容',
        icon: 'none'
      })
      return false
    }

    return true
  },

  async submitReview() {
    if (!this.validateReview()) return

    app.showLoading('提交中...')

    try {
      const { post } = require('../../../utils/request')
      
      // 上传图片（如果有）
      let imageUrls = []
      if (this.data.images.length > 0) {
        // TODO: 实现图片上传
        imageUrls = this.data.images
      }

      await post('/reviews/create', {
        order_id: this.data.orderId,
        rating: this.data.rating,
        content: this.data.comment,
        images: imageUrls,
        is_anonymous: this.data.isAnonymous
      })

      app.hideLoading()

      wx.showToast({
        title: '评价成功',
        icon: 'success'
      })

      setTimeout(() => {
        wx.navigateBack()
      }, 1500)
    } catch (error) {
      app.hideLoading()
      console.error('提交评价失败', error)
      
      // 模拟提交成功
      wx.showToast({
        title: '评价成功（测试）',
        icon: 'success'
      })

      setTimeout(() => {
        wx.navigateBack()
      }, 1500)
    }
  }
})
