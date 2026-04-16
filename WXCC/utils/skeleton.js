/**
 * 骨架屏工具函数
 */

/**
 * 获取骨架屏数据
 * @param {String} type - 骨架屏类型：list, detail, cart
 * @returns {Array}
 */
function getSkeletonData(type = 'list') {
  switch (type) {
    case 'list':
      // 列表骨架屏
      return Array(6).fill({
        id: Math.random(),
        isLoading: true
      })

    case 'detail':
      // 详情页骨架屏
      return Array(1).fill({
        id: Math.random(),
        isLoading: true
      })

    case 'cart':
      // 购物车骨架屏
      return Array(3).fill({
        id: Math.random(),
        isLoading: true
      })

    default:
      return Array(6).fill({
        id: Math.random(),
        isLoading: true
      })
  }
}

module.exports = {
  getSkeletonData
}
