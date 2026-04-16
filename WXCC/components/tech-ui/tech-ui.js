Component({
  properties: {
    // 科技卡片配置
    glow: {
      type: Boolean,
      value: false
    },
    hover: {
      type: Boolean,
      value: true
    },
    customStyle: {
      type: String,
      value: ''
    },
    
    // 数据流动画配置
    lineCount: {
      type: Number,
      value: 5
    },
    
    // 进度条配置
    percent: {
      type: Number,
      value: 0
    },
    color: {
      type: String,
      value: '#1890ff'
    },
    text: {
      type: String,
      value: ''
    },
    
    // 计数器配置
    value: {
      type: Number,
      value: 0
    },
    label: {
      type: String,
      value: ''
    },
    duration: {
      type: Number,
      value: 1000
    },
    
    // 加载动画配置
    size: {
      type: String,
      value: 'medium' // small, medium, large
    },
    loadingText: {
      type: String,
      value: ''
    }
  },

  data: {
    lines: [],
    animatedValue: 0
  },

  lifetimes: {
    attached() {
      this.initDataFlow()
      this.startCounter()
    }
  },

  observers: {
    'value': function(newVal) {
      this.startCounter()
    },
    'lineCount': function(newVal) {
      this.initDataFlow()
    }
  },

  methods: {
    // 初始化数据流动画
    initDataFlow() {
      const lines = []
      for (let i = 0; i < this.data.lineCount; i++) {
        lines.push({
          delay: Math.random() * 2,
          dotDelay: Math.random() * 1
        })
      }
      this.setData({ lines })
    },

    // 数字计数器动画
    startCounter() {
      const startValue = this.data.animatedValue
      const endValue = this.data.value
      const duration = this.data.duration
      const startTime = Date.now()

      const animate = () => {
        const currentTime = Date.now()
        const elapsed = currentTime - startTime
        const progress = Math.min(elapsed / duration, 1)

        // 缓动函数
        const easeOut = 1 - Math.pow(1 - progress, 3)
        const currentValue = Math.floor(startValue + (endValue - startValue) * easeOut)

        this.setData({ animatedValue: currentValue })

        if (progress < 1) {
          requestAnimationFrame(animate)
        }
      }

      animate()
    },

    // 卡片点击事件
    onCardTap() {
      this.triggerEvent('tap')
    }
  }
})