Component({
  properties: {
    src: {
      type: String,
      value: ''
    },
    placeholder: {
      type: String,
      value: '/assets/placeholder.svg'
    },
    mode: {
      type: String,
      value: 'aspectFill'
    }
  },

  data: {
    loaded: false
  },

  methods: {
    onLoad(e) {
      this.setData({ loaded: true })
      this.triggerEvent('load', e.detail)
    },

    onError(e) {
      console.error('图片加载失败', e.detail)
      this.triggerEvent('error', e.detail)
    }
  }
})
