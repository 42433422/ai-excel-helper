Component({
  properties: {
    items: {
      type: Array,
      value: [],
      observer: 'onItemsChange'
    },
    itemHeight: {
      type: Number,
      value: 160
    },
    height: {
      type: Number,
      value: 600
    },
    keyField: {
      type: String,
      value: 'id'
    },
    bufferSize: {
      type: Number,
      value: 5
    }
  },

  data: {
    visibleItems: [],
    scrollTop: 0,
    totalHeight: 0,
    startIndex: 0,
    endIndex: 0
  },

  lifetimes: {
    attached() {
      this.calculateTotalHeight()
      this.renderVisibleItems()
    }
  },

  methods: {
    onItemsChange(newItems) {
      this.calculateTotalHeight()
      this.renderVisibleItems()
    },

    calculateTotalHeight() {
      const totalHeight = this.data.items.length * this.data.itemHeight
      this.setData({ totalHeight })
    },

    renderVisibleItems() {
      const { items, itemHeight, height, bufferSize, startIndex } = this.data
      
      // 计算可见区域能容纳多少项
      const visibleCount = Math.ceil(height / itemHeight)
      const bufferCount = bufferSize * 2
      
      // 计算结束索引
      let endIndex = startIndex + visibleCount + bufferCount
      endIndex = Math.min(endIndex, items.length)

      // 获取可见项
      const visibleItems = items.slice(startIndex, endIndex).map((item, index) => ({
        data: item,
        offsetTop: (startIndex + index) * itemHeight
      }))

      this.setData({
        visibleItems,
        endIndex
      })
    },

    onScroll(e) {
      const scrollTop = e.detail.scrollTop
      const { itemHeight, items, height, bufferSize } = this.data
      
      // 计算新的起始索引
      const newStartIndex = Math.floor(scrollTop / itemHeight)
      const visibleCount = Math.ceil(height / itemHeight)
      
      // 确保不会超出范围
      const maxStartIndex = Math.max(0, items.length - visibleCount)
      const startIndex = Math.min(newStartIndex, maxStartIndex)

      if (startIndex !== this.data.startIndex) {
        this.setData({ startIndex }, () => {
          this.renderVisibleItems()
        })
      }
    }
  }
})
