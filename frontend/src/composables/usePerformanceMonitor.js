import { ref, onMounted, onUnmounted } from 'vue'

export function usePerformanceMonitor(options = {}) {
  const {
    sampleRate = 1000,
    enableFPS = true,
    enableMemory = true,
    enableLongTask = true,
    onPerformanceUpdate = null,
    fpsThreshold = 30,
    longTaskThreshold = 50
  } = options

  const fps = ref(60)
  const memory = ref(0)
  const longTasks = ref([])
  const isMonitoring = ref(false)
  const performanceMetrics = ref({
    avgFPS: 60,
    minFPS: 60,
    maxFPS: 60,
    totalLongTasks: 0,
    memoryUsage: 0
  })

  let frameCount = 0
  let lastTime = performance.now()
  let animationId = null
  let memoryInterval = null
  let sampleInterval = null
  let fpsHistory = []

  const measureFPS = () => {
    if (!isMonitoring.value) return

    frameCount++
    const currentTime = performance.now()
    const elapsed = currentTime - lastTime

    if (elapsed >= 1000) {
      const currentFPS = Math.round((frameCount * 1000) / elapsed)
      fps.value = currentFPS
      fpsHistory.push(currentFPS)

      if (fpsHistory.length > 60) {
        fpsHistory.shift()
      }

      const avg = fpsHistory.reduce((a, b) => a + b, 0) / fpsHistory.length
      const min = Math.min(...fpsHistory)
      const max = Math.max(...fpsHistory)

      performanceMetrics.value = {
        ...performanceMetrics.value,
        avgFPS: Math.round(avg),
        minFPS: min,
        maxFPS: max,
        totalLongTasks: longTasks.value.length
      }

      if (onPerformanceUpdate && currentFPS < fpsThreshold) {
        onPerformanceUpdate({
          type: 'fps',
          value: currentFPS,
          threshold: fpsThreshold
        })
      }

      frameCount = 0
      lastTime = currentTime
    }

    if (isMonitoring.value) {
      animationId = requestAnimationFrame(measureFPS)
    }
  }

  const measureMemory = () => {
    if (!enableMemory) return

    if (performance.memory) {
      memory.value = Math.round(performance.memory.usedJSHeapSize / 1048576)
      performanceMetrics.value.memoryUsage = memory.value

      if (onPerformanceUpdate) {
        onPerformanceUpdate({
          type: 'memory',
          value: memory.value
        })
      }
    }
  }

  const detectLongTask = (entry) => {
    if (!enableLongTask) return

    if (entry.duration > longTaskThreshold) {
      const task = {
        startTime: entry.startTime,
        duration: entry.duration,
        entryType: entry.entryType
      }
      longTasks.value.push(task)
      performanceMetrics.value.totalLongTasks = longTasks.value.length

      if (onPerformanceUpdate) {
        onPerformanceUpdate({
          type: 'longTask',
          value: task
        })
      }
    }
  }

  const startMonitoring = () => {
    if (isMonitoring.value) return

    isMonitoring.value = true

    if (enableFPS) {
      lastTime = performance.now()
      frameCount = 0
      animationId = requestAnimationFrame(measureFPS)
    }

    if (enableMemory) {
      measureMemory()
      memoryInterval = setInterval(measureMemory, 5000)
    }

    if (enableLongTask && 'PerformanceObserver' in window) {
      try {
        const observer = new PerformanceObserver((list) => {
          for (const entry of list.getEntries()) {
            detectLongTask(entry)
          }
        })
        observer.observe({ entryTypes: ['longtask'] })
      } catch (e) {
        console.warn('Long task detection not supported')
      }
    }

    sampleInterval = setInterval(() => {
      if (onPerformanceUpdate && isMonitoring.value) {
        onPerformanceUpdate({
          type: 'sample',
          metrics: { ...performanceMetrics.value }
        })
      }
    }, sampleRate)
  }

  const stopMonitoring = () => {
    isMonitoring.value = false

    if (animationId) {
      cancelAnimationFrame(animationId)
      animationId = null
    }

    if (memoryInterval) {
      clearInterval(memoryInterval)
      memoryInterval = null
    }

    if (sampleInterval) {
      clearInterval(sampleInterval)
      sampleInterval = null
    }
  }

  const resetMetrics = () => {
    fps.value = 60
    memory.value = 0
    longTasks.value = []
    fpsHistory = []
    performanceMetrics.value = {
      avgFPS: 60,
      minFPS: 60,
      maxFPS: 60,
      totalLongTasks: 0,
      memoryUsage: 0
    }
  }

  const getMetrics = () => {
    return {
      ...performanceMetrics.value,
      fps: fps.value,
      memory: memory.value,
      longTasks: longTasks.value
    }
  }

  onMounted(() => {
    if (options.autoStart !== false) {
      startMonitoring()
    }
  })

  onUnmounted(() => {
    stopMonitoring()
  })

  return {
    fps,
    memory,
    longTasks,
    isMonitoring,
    performanceMetrics,
    startMonitoring,
    stopMonitoring,
    resetMetrics,
    getMetrics
  }
}

export function useFrameRateLimiter(targetFPS = 60) {
  const frameInterval = 1000 / targetFPS
  let lastFrameTime = 0
  let animationId = null

  const shouldRender = (timestamp) => {
    const elapsed = timestamp - lastFrameTime
    if (elapsed >= frameInterval) {
      lastFrameTime = timestamp - (elapsed % frameInterval)
      return true
    }
    return false
  }

  const throttle = (callback) => {
    return (timestamp) => {
      if (shouldRender(timestamp)) {
        callback(timestamp)
      }
    }
  }

  const cancelThrottle = () => {
    if (animationId) {
      cancelAnimationFrame(animationId)
      animationId = null
    }
  }

  return {
    shouldRender,
    throttle,
    cancelThrottle,
    frameInterval
  }
}

export function useAnimationFrame() {
  const isRunning = ref(false)
  let animationId = null
  let callback = null

  const start = (cb) => {
    if (isRunning.value) return

    callback = cb
    isRunning.value = true
    let lastTime = performance.now()

    const animate = (currentTime) => {
      if (!isRunning.value) return

      const deltaTime = currentTime - lastTime
      lastTime = currentTime

      if (callback) {
        callback(deltaTime, currentTime)
      }

      animationId = requestAnimationFrame(animate)
    }

    animationId = requestAnimationFrame(animate)
  }

  const stop = () => {
    isRunning.value = false
    if (animationId) {
      cancelAnimationFrame(animationId)
      animationId = null
    }
  }

  const updateCallback = (cb) => {
    callback = cb
  }

  onUnmounted(() => {
    stop()
  })

  return {
    isRunning,
    start,
    stop,
    updateCallback
  }
}
