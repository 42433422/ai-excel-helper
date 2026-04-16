/**
 * 格式化日期时间
 * @param {Date|String|Number} date - 日期对象/时间戳/日期字符串
 * @param {String} format - 格式化模板，默认 'YYYY-MM-DD HH:mm:ss'
 */
function formatDateTime(date, format = 'YYYY-MM-DD HH:mm:ss') {
  if (!date) return ''
  
  const d = new Date(date)
  if (isNaN(d.getTime())) return ''
  
  const year = d.getFullYear()
  const month = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  const hours = String(d.getHours()).padStart(2, '0')
  const minutes = String(d.getMinutes()).padStart(2, '0')
  const seconds = String(d.getSeconds()).padStart(2, '0')
  
  return format
    .replace('YYYY', year)
    .replace('MM', month)
    .replace('DD', day)
    .replace('HH', hours)
    .replace('mm', minutes)
    .replace('ss', seconds)
}

/**
 * 格式化日期
 * @param {Date|String|Number} date - 日期对象
 */
function formatDate(date) {
  return formatDateTime(date, 'YYYY-MM-DD')
}

/**
 * 格式化时间
 * @param {Date|String|Number} date - 日期对象
 */
function formatTime(date) {
  return formatDateTime(date, 'HH:mm:ss')
}

/**
 * 格式化相对时间
 * @param {Date|String|Number} date - 日期对象
 */
function formatRelativeTime(date) {
  if (!date) return ''
  
  const d = new Date(date)
  const now = new Date()
  const diff = now - d
  
  const minute = 60 * 1000
  const hour = 60 * minute
  const day = 24 * hour
  const month = 30 * day
  const year = 12 * month
  
  if (diff < minute) {
    return '刚刚'
  } else if (diff < hour) {
    return `${Math.floor(diff / minute)}分钟前`
  } else if (diff < day) {
    return `${Math.floor(diff / hour)}小时前`
  } else if (diff < month) {
    return `${Math.floor(diff / day)}天前`
  } else if (diff < year) {
    return `${Math.floor(diff / month)}个月前`
  } else {
    return `${Math.floor(diff / year)}年前`
  }
}

/**
 * 格式化价格
 * @param {Number} price - 价格
 * @param {String} symbol - 货币符号
 */
function formatPrice(price, symbol = '¥') {
  if (price === null || price === undefined || isNaN(price)) {
    return `${symbol}0.00`
  }
  return `${symbol}${Number(price).toFixed(2)}`
}

/**
 * 格式化手机号
 * @param {String} phone - 手机号
 */
function formatPhone(phone) {
  if (!phone) return ''
  const str = String(phone)
  if (str.length === 11) {
    return str.replace(/(\d{3})\d{4}(\d{4})/, '$1****$2')
  }
  return str
}

/**
 * 截断文本
 * @param {String} text - 文本
 * @param {Number} length - 长度
 * @param {String} ellipsis - 省略号
 */
function truncate(text, length = 20, ellipsis = '...') {
  if (!text) return ''
  if (text.length <= length) return text
  return text.substring(0, length) + ellipsis
}

/**
 * 防抖函数
 * @param {Function} fn - 函数
 * @param {Number} delay - 延迟时间
 */
function debounce(fn, delay = 300) {
  let timer = null
  return function(...args) {
    if (timer) clearTimeout(timer)
    timer = setTimeout(() => {
      fn.apply(this, args)
    }, delay)
  }
}

/**
 * 节流函数
 * @param {Function} fn - 函数
 * @param {Number} delay - 延迟时间
 */
function throttle(fn, delay = 300) {
  let lastTime = 0
  return function(...args) {
    const now = Date.now()
    if (now - lastTime >= delay) {
      fn.apply(this, args)
      lastTime = now
    }
  }
}

/**
 * 深拷贝
 * @param {Any} obj - 对象
 */
function deepClone(obj) {
  if (obj === null || typeof obj !== 'object') return obj
  if (obj instanceof Date) return new Date(obj)
  if (obj instanceof Array) return obj.map(item => deepClone(item))
  if (obj instanceof Object) {
    const copy = {}
    Object.keys(obj).forEach(key => {
      copy[key] = deepClone(obj[key])
    })
    return copy
  }
  return obj
}

/**
 * 获取 URL 参数
 * @param {String} name - 参数名
 */
function getUrlParam(name) {
  const pages = getCurrentPages()
  const currentPage = pages[pages.length - 1]
  const options = currentPage.options
  return options[name] || ''
}

/**
 * 验证手机号
 * @param {String} phone - 手机号
 */
function validatePhone(phone) {
  return /^1[3-9]\d{9}$/.test(phone)
}

/**
 * 验证身份证号
 * @param {String} idCard - 身份证号
 */
function validateIdCard(idCard) {
  return /(^\d{15}$)|(^\d{18}$)|(^\d{17}(\d|X|x)$)/.test(idCard)
}

/**
 * 验证邮箱
 * @param {String} email - 邮箱
 */
function validateEmail(email) {
  return /^[a-zA-Z0-9_-]+@[a-zA-Z0-9_-]+(\.[a-zA-Z0-9_-]+)+$/.test(email)
}

/**
 * 计算购物车商品总数
 * @param {Array} cartList - 购物车列表
 */
function calculateCartTotal(cartList) {
  if (!cartList || cartList.length === 0) return 0
  return cartList.reduce((total, item) => total + (item.quantity || 0), 0)
}

/**
 * 计算订单总金额
 * @param {Array} products - 商品列表
 */
function calculateOrderTotal(products) {
  if (!products || products.length === 0) return 0
  return products.reduce((total, item) => {
    return total + (item.price || 0) * (item.quantity || 1)
  }, 0)
}

module.exports = {
  formatDateTime,
  formatDate,
  formatTime,
  formatRelativeTime,
  formatPrice,
  formatPhone,
  truncate,
  debounce,
  throttle,
  deepClone,
  getUrlParam,
  validatePhone,
  validateIdCard,
  validateEmail,
  calculateCartTotal,
  calculateOrderTotal
}
