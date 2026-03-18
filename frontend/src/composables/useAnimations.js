import { ref, onMounted, onUnmounted } from 'vue'

export function useAnimation(elementRef, options = {}) {
  const isAnimating = ref(false)
  const animationId = ref(null)
  const progress = ref(0)
  
  const startAnimation = () => {
    if (isAnimating.value) return
    isAnimating.value = true
    progress.value = 0
    
    const startTime = performance.now()
    const duration = options.duration || 1000
    const easing = options.easing || ((t) => t)
    
    const animate = (currentTime) => {
      const elapsed = currentTime - startTime
      progress.value = Math.min(elapsed / duration, 1)
      const easedProgress = easing(progress.value)
      
      if (elementRef.value && options.onFrame) {
        options.onFrame(elementRef.value, easedProgress)
      }
      
      if (progress.value < 1) {
        animationId.value = requestAnimationFrame(animate)
      } else {
        isAnimating.value = false
        if (options.onComplete) {
          options.onComplete()
        }
      }
    }
    
    animationId.value = requestAnimationFrame(animate)
  }
  
  const stopAnimation = () => {
    if (animationId.value) {
      cancelAnimationFrame(animationId.value)
      animationId.value = null
    }
    isAnimating.value = false
  }
  
  const resetAnimation = () => {
    stopAnimation()
    progress.value = 0
  }
  
  const animateTo = (targetValue, duration = 1000, easing = ((t) => t)) => {
    return new Promise((resolve) => {
      const startValue = options.startValue || 0
      const startTime = performance.now()
      
      const animate = (currentTime) => {
        const elapsed = currentTime - startTime
        const progress = Math.min(elapsed / duration, 1)
        const easedProgress = easing(progress)
        const currentValue = startValue + (targetValue - startValue) * easedProgress
        
        if (options.onFrame) {
          options.onFrame(currentValue, easedProgress)
        }
        
        if (progress < 1) {
          animationId.value = requestAnimationFrame(animate)
        } else {
          isAnimating.value = false
          resolve(currentValue)
        }
      }
      
      isAnimating.value = true
      animationId.value = requestAnimationFrame(animate)
    })
  }
  
  const animateLoop = (callback, duration = 1000) => {
    const startTime = performance.now()
    
    const animate = (currentTime) => {
      const elapsed = currentTime - startTime
      const progress = (elapsed % duration) / duration
      
      if (callback) {
        callback(progress)
      }
      
      animationId.value = requestAnimationFrame(animate)
    }
    
    isAnimating.value = true
    animationId.value = requestAnimationFrame(animate)
  }
  
  onUnmounted(() => {
    stopAnimation()
  })
  
  return {
    isAnimating,
    progress,
    startAnimation,
    stopAnimation,
    resetAnimation,
    animateTo,
    animateLoop
  }
}

export function useCSSAnimation(elementRef, animationName, options = {}) {
  const isAnimating = ref(false)
  
  const play = () => {
    if (!elementRef.value) return
    
    isAnimating.value = true
    elementRef.value.style.animation = `${animationName} ${options.duration || 0.3}s ${options.easing || 'ease-out'} ${options.delay || 0}s ${options.fillMode || 'forwards'}`
    
    if (options.onComplete) {
      const duration = (options.duration || 0.3) * 1000 + (options.delay || 0) * 1000
      setTimeout(() => {
        isAnimating.value = false
        options.onComplete()
      }, duration)
    }
  }
  
  const pause = () => {
    if (elementRef.value) {
      elementRef.value.style.animationPlayState = 'paused'
    }
  }
  
  const resume = () => {
    if (elementRef.value) {
      elementRef.value.style.animationPlayState = 'running'
    }
  }
  
  const reset = () => {
    if (elementRef.value) {
      elementRef.value.style.animation = 'none'
      isAnimating.value = false
    }
  }
  
  return {
    isAnimating,
    play,
    pause,
    resume,
    reset
  }
}

export function useTransition(elementRef, options = {}) {
  const isTransitioning = ref(false)
  
  const transition = (toValue, duration = 300) => {
    if (!elementRef.value) return
    
    isTransitioning.value = true
    
    const startValue = parseFloat(elementRef.value.style[options.property] || '0')
    const startTime = performance.now()
    
    const animate = (currentTime) => {
      const elapsed = currentTime - startTime
      const progress = Math.min(elapsed / duration, 1)
      const easedProgress = options.easing ? options.easing(progress) : progress
      const currentValue = startValue + (toValue - startValue) * easedProgress
      
      elementRef.value.style[options.property] = `${currentValue}${options.unit || 'px'}`
      
      if (progress < 1) {
        requestAnimationFrame(animate)
      } else {
        isTransitioning.value = false
        if (options.onComplete) {
          options.onComplete()
        }
      }
    }
    
    requestAnimationFrame(animate)
  }
  
  return {
    isTransitioning,
    transition
  }
}

export const easingFunctions = {
  linear: (t) => t,
  easeInQuad: (t) => t * t,
  easeOutQuad: (t) => t * (2 - t),
  easeInOutQuad: (t) => t < 0.5 ? 2 * t * t : -1 + (4 - 2 * t) * t,
  easeInCubic: (t) => t * t * t,
  easeOutCubic: (t) => (--t) * t * t + 1,
  easeInOutCubic: (t) => t < 0.5 ? 4 * t * t * t : (t - 1) * (2 * t - 2) * (2 * t - 2) + 1,
  easeInElastic: (t) => {
    const c4 = (2 * Math.PI) / 3
    return t === 0 ? 0 : t === 1 ? 1 : -Math.pow(2, 10 * t - 10) * Math.sin((t * 10 - 10.75) * c4)
  },
  easeOutElastic: (t) => {
    const c4 = (2 * Math.PI) / 3
    return t === 0 ? 0 : t === 1 ? 1 : Math.pow(2, -10 * t) * Math.sin((t * 10 - 0.75) * c4) + 1
  },
  easeOutBounce: (x) => {
    const n1 = 7.5625
    const d1 = 2.75
    if (x < 1 / d1) {
      return n1 * x * x
    } else if (x < 2 / d1) {
      return n1 * (x -= 1.5 / d1) * x + 0.75
    } else if (x < 2.5 / d1) {
      return n1 * (x -= 2.25 / d1) * x + 0.9375
    } else {
      return n1 * (x -= 2.625 / d1) * x + 0.984375
    }
  }
}
