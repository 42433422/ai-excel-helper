export class ResourceManager {
  constructor() {
    this.resources = new Map()
    this.listeners = new Map()
    this.timers = new Map()
    this.observers = []
    this.isDisposed = false
  }

  register(id, resource, type = 'generic') {
    if (this.isDisposed) {
      console.warn(`ResourceManager: Cannot register resource "${id}" - manager is disposed`)
      return false
    }

    if (this.resources.has(id)) {
      console.warn(`ResourceManager: Resource "${id}" already registered, replacing`)
      this.release(id)
    }

    this.resources.set(id, {
      resource,
      type,
      createdAt: Date.now(),
      lastAccessed: Date.now()
    })

    return true
  }

  get(id) {
    const entry = this.resources.get(id)
    if (entry) {
      entry.lastAccessed = Date.now()
      return entry.resource
    }
    return null
  }

  has(id) {
    return this.resources.has(id)
  }

  release(id) {
    const entry = this.resources.get(id)
    if (!entry) return false

    const { resource, type } = entry

    try {
      if (resource && typeof resource.dispose === 'function') {
        resource.dispose()
      } else if (resource && typeof resource.destroy === 'function') {
        resource.destroy()
      } else if (resource && typeof resource.cleanup === 'function') {
        resource.cleanup()
      } else if (resource instanceof HTMLElement && resource.remove) {
        resource.remove()
      } else if (resource && resource instanceof EventTarget && resource.removeEventListener) {
        this.removeAllListeners(resource)
      }
    } catch (error) {
      console.error(`ResourceManager: Error releasing resource "${id}":`, error)
    }

    this.resources.delete(id)
    return true
  }

  releaseByType(type) {
    const toRelease = []
    for (const [id, entry] of this.resources) {
      if (entry.type === type) {
        toRelease.push(id)
      }
    }
    toRelease.forEach(id => this.release(id))
    return toRelease.length
  }

  releaseAll() {
    const count = this.resources.size
    for (const [id] of this.resources) {
      this.release(id)
    }
    this.listeners.clear()
    this.timers.forEach(timer => clearInterval(timer))
    this.timers.clear()
    this.observers.forEach(obs => {
      if (obs.disconnect) obs.disconnect()
    })
    this.observers = []
    return count
  }

  dispose() {
    this.releaseAll()
    this.isDisposed = true
  }

  addListener(target, event, handler, options = {}) {
    const key = `${target}-${event}-${Date.now()}`
    target.addEventListener(event, handler, options)
    this.listeners.set(key, { target, event, handler, options })
    return key
  }

  removeListener(key) {
    const listener = this.listeners.get(key)
    if (!listener) return false

    listener.target.removeEventListener(listener.event, listener.handler, listener.options)
    this.listeners.delete(key)
    return true
  }

  removeAllListeners(target) {
    const toRemove = []
    for (const [key, listener] of this.listeners) {
      if (listener.target === target) {
        toRemove.push(key)
      }
    }
    toRemove.forEach(key => this.removeListener(key))
  }

  registerTimer(id, timer) {
    if (this.timers.has(id)) {
      this.clearTimer(id)
    }
    this.timers.set(id, timer)
  }

  clearTimer(id) {
    const timer = this.timers.get(id)
    if (timer) {
      clearInterval(timer)
      clearTimeout(timer)
      this.timers.delete(id)
    }
  }

  clearAllTimers() {
    this.timers.forEach(timer => {
      clearInterval(timer)
      clearTimeout(timer)
    })
    this.timers.clear()
  }

  registerObserver(observer) {
    this.observers.push(observer)
  }

  disconnectAllObservers() {
    this.observers.forEach(obs => {
      if (obs.disconnect) obs.disconnect()
    })
    this.observers = []
  }

  getStats() {
    const stats = {
      total: this.resources.size,
      byType: {},
      oldest: null,
      newest: null,
      listeners: this.listeners.size,
      timers: this.timers.size,
      observers: this.observers.length
    }

    let oldestTime = Infinity
    let newestTime = 0

    for (const [id, entry] of this.resources) {
      if (!stats.byType[entry.type]) {
        stats.byType[entry.type] = 0
      }
      stats.byType[entry.type]++

      if (entry.createdAt < oldestTime) {
        oldestTime = entry.createdAt
        stats.oldest = id
      }
      if (entry.createdAt > newestTime) {
        newestTime = entry.createdAt
        stats.newest = id
      }
    }

    return stats
  }
}

export const globalResourceManager = new ResourceManager()

export function createResourceManager() {
  return new ResourceManager()
}

export function useCleanup() {
  const cleanupFns = []

  const register = (fn) => {
    if (typeof fn === 'function') {
      cleanupFns.push(fn)
    }
  }

  const cleanup = () => {
    cleanupFns.forEach(fn => {
      try {
        fn()
      } catch (e) {
        console.error('Cleanup error:', e)
      }
    })
    cleanupFns.length = 0
  }

  return { register, cleanup }
}

export function cleanupCanvas(ctx) {
  if (!ctx) return

  const canvas = ctx.canvas
  ctx.clearRect(0, 0, canvas.width, canvas.height)

  if (canvas.width !== 0) {
    canvas.width = 0
    canvas.height = 0
  }
}

export function cleanupAnimationFrame(id) {
  if (id && typeof cancelAnimationFrame === 'function') {
    cancelAnimationFrame(id)
  }
}

export function cleanupInterval(id) {
  if (id) {
    clearInterval(id)
  }
}

export function cleanupTimeout(id) {
  if (id) {
    clearTimeout(id)
  }
}

export function cleanupEventListener(target, event, handler) {
  if (target && event && handler) {
    target.removeEventListener(event, handler)
  }
}

export function cleanupObject(obj) {
  if (!obj) return

  for (const key in obj) {
    if (obj[key] && typeof obj[key] === 'object') {
      cleanupObject(obj[key])
    }
    obj[key] = null
  }
}
