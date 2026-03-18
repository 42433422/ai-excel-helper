import { ref, onMounted, onUnmounted } from 'vue'

export function useDigitalRain(canvasRef, options = {}) {
  const ctx = ref(null)
  const columns = ref([])
  const drops = ref([])
  const fontSize = ref(options.fontSize || 14)
  const chars = ref(options.chars || ['0', '1'])
  const isRunning = ref(false)
  const animationId = ref(null)
  const isWorkMode = ref(false)
  
  const init = () => {
    if (!canvasRef.value) return
    
    const canvas = canvasRef.value
    ctx.value = canvas.getContext('2d')
    
    canvas.width = options.width || window.innerWidth
    canvas.height = options.height || window.innerHeight
    
    const columnCount = Math.floor(canvas.width / fontSize.value)
    columns.value = Array(columnCount).fill(1)
    drops.value = Array(columnCount).fill(0)
  }
  
  const draw = () => {
    if (!ctx.value || !canvasRef.value) return
    
    const canvas = canvasRef.value
    const context = ctx.value
    
    context.fillStyle = isWorkMode.value ? 'rgba(255, 0, 0, 0.05)' : 'rgba(0, 0, 0, 0.05)'
    context.fillRect(0, 0, canvas.width, canvas.height)
    
    context.fillStyle = isWorkMode.value ? '#ff0000' : '#0f0'
    context.font = `${fontSize.value}px monospace`
    
    for (let i = 0; i < drops.value.length; i++) {
      const text = chars.value[Math.floor(Math.random() * chars.value.length)]
      const x = i * fontSize.value
      const y = drops.value[i] * fontSize.value
      
      context.fillText(text, x, y)
      
      if (y > canvas.height && Math.random() > 0.975) {
        drops.value[i] = 0
      }
      
      drops.value[i]++
    }
    
    animationId.value = requestAnimationFrame(draw)
  }
  
  const start = () => {
    if (isRunning.value) return
    
    init()
    isRunning.value = true
    draw()
  }
  
  const stop = () => {
    if (!isRunning.value) return
    
    isRunning.value = false
    if (animationId.value) {
      cancelAnimationFrame(animationId.value)
      animationId.value = null
    }
  }
  
  const setWorkMode = (enabled) => {
    isWorkMode.value = enabled
  }
  
  const resize = () => {
    if (!canvasRef.value) return
    
    const canvas = canvasRef.value
    canvas.width = options.width || window.innerWidth
    canvas.height = options.height || window.innerHeight
    
    const columnCount = Math.floor(canvas.width / fontSize.value)
    columns.value = Array(columnCount).fill(1)
    drops.value = Array(columnCount).fill(0)
  }
  
  const clear = () => {
    if (!ctx.value || !canvasRef.value) return
    
    const canvas = canvasRef.value
    const context = ctx.value
    
    context.fillStyle = isWorkMode.value ? 'rgba(255, 0, 0, 1)' : 'rgba(0, 0, 0, 1)'
    context.fillRect(0, 0, canvas.width, canvas.height)
  }
  
  onMounted(() => {
    window.addEventListener('resize', resize)
  })
  
  onUnmounted(() => {
    stop()
    window.removeEventListener('resize', resize)
  })
  
  return {
    isRunning,
    start,
    stop,
    setWorkMode,
    resize,
    clear
  }
}
