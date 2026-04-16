Component({
  properties: {
    // 柱状图配置
    title: {
      type: String,
      value: ''
    },
    data: {
      type: Array,
      value: []
    },
    type: {
      type: String,
      value: 'bar' // bar, pie, line
    },
    
    // 环形图配置
    size: {
      type: Number,
      value: 200
    },
    total: {
      type: Number,
      value: 0
    },
    
    // 数据卡片配置
    value: {
      type: [String, Number],
      value: ''
    },
    unit: {
      type: String,
      value: ''
    },
    trend: {
      type: String,
      value: 'up' // up, down, stable
    },
    trendText: {
      type: String,
      value: ''
    },
    description: {
      type: String,
      value: ''
    }
  },

  data: {
    trendClass: 'trend-up'
  },

  observers: {
    'trend': function(trend) {
      const trendClass = `trend-${trend}`
      this.setData({ trendClass })
    }
  },

  methods: {
    // 计算柱状图百分比
    calculateBarPercent(data, maxValue) {
      if (!maxValue) {
        maxValue = Math.max(...data.map(item => item.value))
      }
      
      return data.map(item => ({
        ...item,
        percent: (item.value / maxValue) * 100
      }))
    },

    // 计算环形图角度
    calculatePieData(data) {
      const total = data.reduce((sum, item) => sum + item.value, 0)
      let currentAngle = 0
      
      return data.map(item => {
        const percent = (item.value / total) * 100
        const angle = (item.value / total) * 360
        const segment = {
          ...item,
          percent: percent,
          startAngle: currentAngle,
          endAngle: currentAngle + angle
        }
        currentAngle += angle
        return segment
      })
    }
  },

  lifetimes: {
    attached() {
      if (this.data.type === 'bar' && this.data.data.length > 0) {
        const processedData = this.calculateBarPercent(this.data.data)
        this.setData({ data: processedData })
      }
      
      if (this.data.type === 'pie' && this.data.data.length > 0) {
        const processedData = this.calculatePieData(this.data.data)
        this.setData({ 
          data: processedData,
          total: this.data.data.reduce((sum, item) => sum + item.value, 0)
        })
      }
    }
  }
})