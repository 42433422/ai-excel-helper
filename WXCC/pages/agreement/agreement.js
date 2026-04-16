Page({
  data: {
    type: 'terms',
    title: '用户协议'
  },

  onLoad(options) {
    const type = options.type || 'terms'
    this.setData({
      type: type,
      title: type === 'terms' ? '用户协议' : '隐私政策'
    })
  }
})
