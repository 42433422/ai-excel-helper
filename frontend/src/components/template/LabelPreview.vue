<template>
  <div class="label-preview">
    <canvas ref="labelCanvas" class="label-canvas"></canvas>
  </div>
</template>

<script>
export default {
  name: 'LabelPreview',
  props: {
    fields: {
      type: Array,
      default: () => []
    },
    width: {
      type: Number,
      default: 300
    },
    height: {
      type: Number,
      default: 200
    }
  },
  data() {
    return {
      canvas: null,
      ctx: null
    }
  },
  mounted() {
    this.$nextTick(() => {
      this.initCanvas()
      this.render()
    })
  },
  watch: {
    fields: {
      handler() {
        this.render()
      },
      deep: true
    }
  },
  methods: {
    initCanvas() {
      this.canvas = this.$refs.labelCanvas
      if (this.canvas) {
        this.ctx = this.canvas.getContext('2d')
        this.canvas.width = this.width
        this.canvas.height = this.height
      }
    },

    render() {
      if (!this.ctx) return

      const ctx = this.ctx
      const w = this.canvas.width
      const h = this.canvas.height

      ctx.fillStyle = '#FFFFFF'
      ctx.fillRect(0, 0, w, h)

      ctx.strokeStyle = '#000000'
      ctx.lineWidth = 3
      ctx.strokeRect(0, 0, w - 1, h - 1)

      ctx.strokeStyle = '#333333'
      ctx.lineWidth = 1
      const innerPadding = 10
      ctx.strokeRect(
        innerPadding,
        innerPadding,
        w - innerPadding * 2,
        h - innerPadding * 2
      )

      this.renderFields(ctx, w, h)

      this.renderBorder(ctx, w, h)
    },

    renderFields(ctx, w, h) {
      const fields = this.fields.length > 0 ? this.fields : this.getDefaultFields()

      let yOffset = 20
      const lineHeight = 24
      const leftMargin = 15

      ctx.font = 'bold 14px sans-serif'
      ctx.fillStyle = '#333333'

      const fixedFields = fields.filter(f => f.type === 'fixed')
      const dynamicFields = fields.filter(f => f.type === 'dynamic')

      const allFields = [
        ...fixedFields.map(f => ({ ...f, isLabel: true })),
        ...dynamicFields.map(f => ({ ...f, isLabel: false }))
      ]

      for (const field of allFields) {
        if (yOffset > h - 30) break

        if (field.isLabel) {
          ctx.font = 'bold 13px sans-serif'
          ctx.fillStyle = '#333333'
          ctx.fillText(field.label + ': ', leftMargin, yOffset)
          ctx.font = '13px sans-serif'
          ctx.fillStyle = '#000000'
          const labelWidth = ctx.measureText(field.label + ': ').width
          ctx.fillText(field.value || '', leftMargin + labelWidth, yOffset)
        } else {
          ctx.font = 'bold 13px sans-serif'
          ctx.fillStyle = '#333333'
          ctx.fillText(field.label + ': ', leftMargin, yOffset)
          ctx.font = '13px sans-serif'
          ctx.fillStyle = '#0066cc'
          const labelWidth = ctx.measureText(field.label + ': ').width
          ctx.fillText(field.value || '______', leftMargin + labelWidth, yOffset)
        }

        yOffset += lineHeight
      }

      if (fixedFields.length > 0 && dynamicFields.length > 0) {
        yOffset += 5
        ctx.strokeStyle = '#cccccc'
        ctx.beginPath()
        ctx.moveTo(leftMargin, yOffset)
        ctx.lineTo(w - leftMargin, yOffset)
        ctx.stroke()
        yOffset += 8
      }

      for (const field of dynamicFields) {
        if (yOffset > h - 30) break

        ctx.font = 'bold 13px sans-serif'
        ctx.fillStyle = '#333333'
        ctx.fillText(field.label + ': ', leftMargin, yOffset)
        ctx.font = '13px sans-serif'
        ctx.fillStyle = '#0066cc'
        const labelWidth = ctx.measureText(field.label + ': ').width
        ctx.fillText(field.value || '______', leftMargin + labelWidth, yOffset)

        yOffset += lineHeight
      }
    },

    renderBorder(ctx, w, h) {
      ctx.strokeStyle = '#000000'
      ctx.lineWidth = 3
      ctx.strokeRect(0, 0, w - 1, h - 1)

      ctx.strokeStyle = '#cccccc'
      ctx.lineWidth = 1
      ctx.strokeRect(5, 5, w - 10, h - 10)
    },

    getDefaultFields() {
      return [
        { label: '品名', value: 'XX运动鞋', type: 'fixed' },
        { label: '货号', value: '1635', type: 'dynamic' },
        { label: '颜色', value: '白色', type: 'dynamic' },
        { label: '码段', value: '00001', type: 'dynamic' },
        { label: '等级', value: '合格品', type: 'fixed' },
        { label: '统一零售价', value: '¥199', type: 'dynamic' }
      ]
    },

    getImageData() {
      if (this.canvas) {
        return this.canvas.toDataURL('image/png')
      }
      return ''
    }
  }
}
</script>

<style scoped>
.label-preview {
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 10px;
  background: #f5f5f5;
  border-radius: 4px;
}

.label-canvas {
  background: white;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  max-width: 100%;
}
</style>
