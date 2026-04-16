/**
 * 收藏工具函数
 */

const FAVORITE_KEY = 'mp_favorites'

/**
 * 获取收藏列表
 * @returns {Array}
 */
function getFavorites() {
  return wx.getStorageSync(FAVORITE_KEY) || []
}

/**
 * 添加收藏
 * @param {Object} product - 商品信息
 * @returns {boolean}
 */
function addFavorite(product) {
  const favorites = getFavorites()
  
  // 检查是否已收藏
  const exists = favorites.some(item => item.id === product.id)
  if (exists) {
    return false
  }

  favorites.unshift({
    id: product.id,
    name: product.name,
    image: product.image,
    price: product.price,
    createTime: Date.now()
  })

  wx.setStorageSync(FAVORITE_KEY, favorites)
  return true
}

/**
 * 取消收藏
 * @param {Number} productId - 商品 ID
 * @returns {boolean}
 */
function removeFavorite(productId) {
  const favorites = getFavorites()
  const index = favorites.findIndex(item => item.id === productId)
  
  if (index === -1) {
    return false
  }

  favorites.splice(index, 1)
  wx.setStorageSync(FAVORITE_KEY, favorites)
  return true
}

/**
 * 检查是否已收藏
 * @param {Number} productId - 商品 ID
 * @returns {boolean}
 */
function isFavorite(productId) {
  const favorites = getFavorites()
  return favorites.some(item => item.id === productId)
}

/**
 * 清空收藏
 */
function clearFavorites() {
  wx.removeStorageSync(FAVORITE_KEY)
}

/**
 * 从服务器同步收藏列表
 * @returns {Promise}
 */
function syncFavorites() {
  const { get } = require('./request')
  
  return new Promise((resolve, reject) => {
    get('/favorites/list')
      .then(res => {
        if (res && res.success) {
          wx.setStorageSync(FAVORITE_KEY, res.data || [])
          resolve(res.data)
        } else {
          reject(res)
        }
      })
      .catch(err => reject(err))
  })
}

module.exports = {
  getFavorites,
  addFavorite,
  removeFavorite,
  isFavorite,
  clearFavorites,
  syncFavorites
}
