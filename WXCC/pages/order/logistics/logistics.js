Page({
  data: {
    orderId: null,
    logistics: {
      company: '',
      trackingNo: '',
      status: '',
      updateTime: ''
    },
    tracks: [],
    loading: false
  },

  onLoad(options) {
    if (options.id) {
      this.setData({ orderId: options.id })
      this.loadLogistics(options.id)
    }
  },

  onPullDownRefresh() {
    this.loadLogistics(this.data.orderId).finally(() => {
      wx.stopPullDownRefresh()
    })
  },

  async loadLogistics(orderId) {
    this.setData({ loading: true })

    try {
      const { get } = require('../../../utils/request')
      const res = await get(`/orders/${orderId}/logistics`)

      if (res && res.success && res.data) {
        this.setData({
          logistics: {
            company: res.data.company,
            trackingNo: res.data.tracking_no,
            status: res.data.status,
            updateTime: res.data.update_time
          },
          tracks: res.data.tracks || []
        })
      }
    } catch (error) {
      console.error('加载物流信息失败', error)
      // 使用模拟数据
      this.setMockLogistics()
    } finally {
      this.setData({ loading: false })
    }
  },

  setMockLogistics() {
    this.setData({
      logistics: {
        company: '顺丰速运',
        trackingNo: 'SF1234567890',
        status: '已签收',
        updateTime: '2024-01-10 10:30'
      },
      tracks: [
        {
          time: '2024-01-10 10:30',
          info: '已签收，签收人：本人'
        },
        {
          time: '2024-01-10 08:00',
          info: '快递员正在派送'
        },
        {
          time: '2024-01-10 06:00',
          info: '已到达【北京朝阳公司】'
        },
        {
          time: '2024-01-09 20:00',
          info: '已从【北京转运中心】发出'
        },
        {
          time: '2024-01-09 14:00',
          info: '已收件'
        }
      ]
    })
  },

  copyTrackingNo() {
    wx.setClipboardData({
      data: this.data.logistics.trackingNo,
      success: () => {
        wx.showToast({
          title: '已复制',
          icon: 'success'
        })
      }
    })
  }
})
