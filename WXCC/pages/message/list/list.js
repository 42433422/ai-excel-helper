Page({
  data: {
    messages: [],
    loading: false,
    page: 1,
    pageSize: 20,
    hasMore: true
  },

  onLoad() {
    this.loadMessages()
  },

  onPullDownRefresh() {
    this.setData({ page: 1, messages: [], hasMore: true })
    this.loadMessages().finally(() => {
      wx.stopPullDownRefresh()
    })
  },

  onReachBottom() {
    if (this.data.hasMore && !this.data.loading) {
      this.setData({ page: this.data.page + 1 })
      this.loadMessages()
    }
  },

  async loadMessages() {
    if (this.data.loading) return

    this.setData({ loading: true })

    try {
      const { get } = require('../../../utils/request')
      const res = await get('/messages', {
        page: this.data.page,
        per_page: this.data.pageSize
      })

      if (res && res.success) {
        const newMessages = (res.data || []).map(msg => this.formatMessage(msg))
        const messages = this.data.page === 1 
          ? newMessages 
          : [...this.data.messages, ...newMessages]

        this.setData({
          messages,
          hasMore: newMessages.length === this.data.pageSize
        })
      }
    } catch (error) {
      console.error('加载消息失败', error)
      // 使用模拟数据
      if (this.data.page === 1) {
        this.setMockMessages()
      }
    } finally {
      this.setData({ loading: false })
    }
  },

  formatMessage(msg) {
    const typeIcons = {
      'order': 'icon-order',
      'system': 'icon-system',
      'promotion': 'icon-promotion',
      'logistics': 'icon-logistics'
    }

    return {
      id: msg.id,
      type: msg.type || 'system',
      icon: typeIcons[msg.type] || 'icon-system',
      title: msg.title,
      content: msg.content,
      time: msg.create_time,
      read: msg.is_read
    }
  },

  setMockMessages() {
    this.setData({
      messages: [
        {
          id: 1,
          type: 'order',
          icon: 'icon-order',
          title: '订单通知',
          content: '您的订单已发货，请注意查收',
          time: '10:30',
          read: false
        },
        {
          id: 2,
          type: 'system',
          icon: 'icon-system',
          title: '系统消息',
          content: '欢迎使用 XCAGI 智能采购商城',
          time: '昨天',
          read: true
        },
        {
          id: 3,
          type: 'promotion',
          icon: 'icon-promotion',
          title: '优惠活动',
          content: '新品上市，限时优惠，快来选购吧！',
          time: '3 天前',
          read: false
        }
      ]
    })
  },

  goToDetail(e) {
    const messageId = e.currentTarget.dataset.id
    const message = this.data.messages.find(item => item.id === messageId)

    // 标记为已读
    if (!message.read) {
      message.read = true
      this.setData({ messages: this.data.messages })
    }

    // TODO: 跳转到消息详情页
    wx.showToast({
      title: message.content,
      icon: 'none',
      duration: 3000
    })
  }
})
