/**
 * 图片懒加载和缓存工具
 */

const lazyLoadQueue = []
let observer = null

// 缓存配置
const CACHE_CONFIG = {
  maxSize: 50 * 1024 * 1024, // 最大缓存大小 50MB
  maxAge: 7 * 24 * 60 * 60 * 1000, // 缓存有效期 7 天
  cacheDir: 'cached_images' // 缓存目录
}

// 缓存索引
let cacheIndex = {}

/**
 * 初始化图片缓存
 */
function initCache() {
  const fs = wx.getFileSystemManager()
  const cachePath = `${wx.env.USER_DATA_PATH}/${CACHE_CONFIG.cacheDir}`
  
  try {
    // 检查缓存目录是否存在
    fs.accessSync(cachePath)
  } catch (e) {
    // 创建缓存目录
    fs.mkdirSync(cachePath, true)
  }
  
  // 加载缓存索引
  try {
    const indexPath = `${cachePath}/index.json`
    fs.accessSync(indexPath)
    const indexData = fs.readFileSync(indexPath, 'utf8')
    cacheIndex = JSON.parse(indexData)
  } catch (e) {
    cacheIndex = {}
  }
  
  // 清理过期缓存
  cleanExpiredCache()
}

/**
 * 保存缓存索引
 */
function saveCacheIndex() {
  const fs = wx.getFileSystemManager()
  const indexPath = `${wx.env.USER_DATA_PATH}/${CACHE_CONFIG.cacheDir}/index.json`
  
  try {
    fs.writeFileSync(indexPath, JSON.stringify(cacheIndex), 'utf8')
  } catch (e) {
    console.error('保存缓存索引失败', e)
  }
}

/**
 * 清理过期缓存
 */
function cleanExpiredCache() {
  const fs = wx.getFileSystemManager()
  const now = Date.now()
  const cachePath = `${wx.env.USER_DATA_PATH}/${CACHE_CONFIG.cacheDir}`
  
  Object.keys(cacheIndex).forEach(url => {
    const cache = cacheIndex[url]
    if (now - cache.timestamp > CACHE_CONFIG.maxAge) {
      // 删除过期文件
      try {
        fs.unlinkSync(cache.path)
        delete cacheIndex[url]
      } catch (e) {
        console.error('删除过期缓存失败', e)
      }
    }
  })
  
  saveCacheIndex()
}

/**
 * 检查缓存大小
 */
function checkCacheSize() {
  const fs = wx.getFileSystemManager()
  const cachePath = `${wx.env.USER_DATA_PATH}/${CACHE_CONFIG.cacheDir}`
  
  try {
    const files = fs.readdirSync(cachePath)
    let totalSize = 0
    
    files.forEach(file => {
      if (file !== 'index.json') {
        const filePath = `${cachePath}/${file}`
        const stat = fs.statSync(filePath)
        totalSize += stat.size
      }
    })
    
    return totalSize
  } catch (e) {
    return 0
  }
}

/**
 * 清理缓存以释放空间
 */
function cleanCacheIfNeeded() {
  const currentSize = checkCacheSize()
  
  if (currentSize > CACHE_CONFIG.maxSize) {
    // 按时间排序，删除最旧的缓存
    const sorted = Object.entries(cacheIndex)
      .sort((a, b) => a[1].timestamp - b[1].timestamp)
    
    const fs = wx.getFileSystemManager()
    const cachePath = `${wx.env.USER_DATA_PATH}/${CACHE_CONFIG.cacheDir}`
    
    for (const [url, cache] of sorted) {
      if (currentSize <= CACHE_CONFIG.maxSize * 0.8) break
      
      try {
        fs.unlinkSync(cache.path)
        delete cacheIndex[url]
        currentSize -= cache.size
      } catch (e) {
        console.error('清理缓存失败', e)
      }
    }
    
    saveCacheIndex()
  }
}

/**
 * 从缓存获取图片
 * @param {String} url - 图片 URL
 * @returns {String|null} 缓存路径或 null
 */
function getCachedImage(url) {
  const cache = cacheIndex[url]
  
  if (!cache) return null
  
  const fs = wx.getFileSystemManager()
  
  try {
    fs.accessSync(cache.path)
    return cache.path
  } catch (e) {
    // 文件不存在，删除索引
    delete cacheIndex[url]
    saveCacheIndex()
    return null
  }
}

/**
 * 缓存图片
 * @param {String} url - 图片 URL
 * @param {String} tempPath - 临时文件路径
 * @returns {String} 缓存路径
 */
function cacheImage(url, tempPath) {
  const fs = wx.getFileSystemManager()
  const cachePath = `${wx.env.USER_DATA_PATH}/${CACHE_CONFIG.cacheDir}`
  const fileName = `${Date.now()}_${Math.random().toString(36).substr(2, 9)}.png`
  const filePath = `${cachePath}/${fileName}`
  
  try {
    // 复制文件到缓存目录
    fs.copyFileSync(tempPath, filePath)
    
    // 获取文件大小
    const stat = fs.statSync(filePath)
    
    // 更新索引
    cacheIndex[url] = {
      path: filePath,
      timestamp: Date.now(),
      size: stat.size
    }
    
    saveCacheIndex()
    
    // 检查是否需要清理
    cleanCacheIfNeeded()
    
    return filePath
  } catch (e) {
    console.error('缓存图片失败', e)
    return null
  }
}

/**
 * 获取图片（带缓存）
 * @param {String} url - 图片 URL
 * @returns {Promise<String>} 图片路径
 */
function getImage(url) {
  return new Promise((resolve, reject) => {
    // 检查缓存
    const cached = getCachedImage(url)
    if (cached) {
      console.log('[图片缓存] 命中缓存:', url)
      resolve(cached)
      return
    }
    
    // 下载图片
    console.log('[图片缓存] 未命中缓存，下载:', url)
    wx.downloadFile({
      url: url,
      success(res) {
        if (res.statusCode === 200) {
          // 缓存图片
          const cachedPath = cacheImage(url, res.tempFilePath)
          resolve(cachedPath || res.tempFilePath)
        } else {
          reject(new Error('下载失败'))
        }
      },
      fail: reject
    })
  })
}

/**
 * 清除所有缓存
 */
function clearCache() {
  const fs = wx.getFileSystemManager()
  const cachePath = `${wx.env.USER_DATA_PATH}/${CACHE_CONFIG.cacheDir}`
  
  try {
    // 删除所有文件
    const files = fs.readdirSync(cachePath)
    files.forEach(file => {
      if (file !== 'index.json') {
        fs.unlinkSync(`${cachePath}/${file}`)
      }
    })
    
    // 清空索引
    cacheIndex = {}
    saveCacheIndex()
    
    console.log('[图片缓存] 已清除所有缓存')
  } catch (e) {
    console.error('清除缓存失败', e)
  }
}

/**
 * 获取缓存统计信息
 * @returns {Object} 缓存信息
 */
function getCacheInfo() {
  const fs = wx.getFileSystemManager()
  const cachePath = `${wx.env.USER_DATA_PATH}/${CACHE_CONFIG.cacheDir}`
  
  try {
    const files = fs.readdirSync(cachePath)
    let totalSize = 0
    let count = 0
    
    files.forEach(file => {
      if (file !== 'index.json') {
        const filePath = `${cachePath}/${file}`
        const stat = fs.statSync(filePath)
        totalSize += stat.size
        count++
      }
    })
    
    return {
      count: Object.keys(cacheIndex).length,
      size: totalSize,
      sizeText: formatSize(totalSize),
      maxSize: CACHE_CONFIG.maxSize,
      maxSizeText: formatSize(CACHE_CONFIG.maxSize)
    }
  } catch (e) {
    return {
      count: 0,
      size: 0,
      sizeText: '0 B',
      maxSize: CACHE_CONFIG.maxSize,
      maxSizeText: formatSize(CACHE_CONFIG.maxSize)
    }
  }
}

/**
 * 格式化文件大小
 * @param {Number} bytes - 字节数
 * @returns {String} 格式化后的大小
 */
function formatSize(bytes) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(2)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`
}

/**
 * 初始化图片懒加载观察器
 */
function initLazyLoad() {
  if (observer) return observer

  observer = wx.createIntersectionObserver({
    thresholds: [0],
    initialRatio: 0,
    observeAll: false
  })

  return observer
}

/**
 * 观察图片元素
 * @param {String} selector - CSS 选择器
 * @param {Function} callback - 回调函数
 */
function observeImage(selector, callback) {
  const obs = initLazyLoad()
  
  obs.relativeToViewport({ bottom: 500 })
    .observe(selector, (res) => {
      if (res.intersectionRatio > 0) {
        callback()
        obs.disconnect()
      }
    })
}

/**
 * 批量观察图片
 * @param {Array} selectors - 选择器数组
 */
function observeImages(selectors) {
  const obs = initLazyLoad()
  
  selectors.forEach(selector => {
    obs.relativeToViewport({ bottom: 500 })
      .observe(selector, (res) => {
        if (res.intersectionRatio > 0) {
          obs.disconnect()
        }
      })
  })
}

/**
 * 图片预加载
 * @param {Array} urls - 图片 URL 数组
 * @returns {Promise}
 */
function preloadImages(urls) {
  return Promise.all(urls.map(url => {
    return new Promise((resolve, reject) => {
      wx.getImageInfo({
        src: url,
        success: resolve,
        fail: reject
      })
    })
  }))
}

/**
 * 清除观察器
 */
function clearObserver() {
  if (observer) {
    observer.disconnect()
    observer = null
  }
}

module.exports = {
  // 缓存相关
  initCache,
  getImage,
  getCachedImage,
  clearCache,
  getCacheInfo,
  
  // 懒加载相关
  initLazyLoad,
  observeImage,
  observeImages,
  preloadImages,
  clearObserver
}
