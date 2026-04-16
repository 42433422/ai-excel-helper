Component({
  properties: {
    isLoading: {
      type: Boolean,
      value: false
    },
    type: {
      type: String,
      value: 'list' // list, detail, cart
    },
    count: {
      type: Number,
      value: 6
    }
  },

  data: {
    items: []
  },

  observer: {
    isLoading(newVal) {
      if (newVal && this.data.items.length === 0) {
        this.generateItems()
      }
    }
  },

  methods: {
    generateItems() {
      const items = Array(this.data.count).fill({
        id: Math.random(),
        isLoading: true
      })
      this.setData({ items })
    }
  }
})
