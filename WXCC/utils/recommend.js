/**
 * 智能推荐算法工具
 */

// 推荐算法配置
const RECOMMEND_CONFIG = {
  // 权重配置
  weights: {
    popularity: 0.3,    // 热度权重
    similarity: 0.4,    // 相似度权重
    personal: 0.2,      // 个性化权重
    recency: 0.1        // 时效性权重
  },
  
  // 相似度计算配置
  similarity: {
    category: 0.6,      // 分类相似度权重
    price: 0.3,        // 价格相似度权重
    tags: 0.1          // 标签相似度权重
  }
}

/**
 * 基于用户行为的协同过滤推荐
 * @param {Array} userHistory - 用户历史行为
 * @param {Array} allProducts - 所有商品
 * @param {Number} limit - 推荐数量
 * @returns {Array} 推荐商品列表
 */
function collaborativeFiltering(userHistory, allProducts, limit = 10) {
  if (!userHistory || userHistory.length === 0) {
    return popularityBased(allProducts, limit)
  }
  
  // 计算用户偏好向量
  const userVector = calculateUserVector(userHistory)
  
  // 计算商品与用户偏好的相似度
  const scoredProducts = allProducts.map(product => {
    const similarity = calculateSimilarity(userVector, product)
    return {
      ...product,
      score: similarity
    }
  })
  
  // 按相似度排序并返回前N个
  return scoredProducts
    .sort((a, b) => b.score - a.score)
    .slice(0, limit)
}

/**
 * 基于热度的推荐
 * @param {Array} products - 商品列表
 * @param {Number} limit - 推荐数量
 * @returns {Array} 热门商品列表
 */
function popularityBased(products, limit = 10) {
  return products
    .sort((a, b) => {
      // 综合热度评分：销量 + 评分 + 时间衰减
      const scoreA = calculatePopularityScore(a)
      const scoreB = calculatePopularityScore(b)
      return scoreB - scoreA
    })
    .slice(0, limit)
}

/**
 * 基于内容的推荐
 * @param {Object} targetProduct - 目标商品
 * @param {Array} allProducts - 所有商品
 * @param {Number} limit - 推荐数量
 * @returns {Array} 相似商品列表
 */
function contentBased(targetProduct, allProducts, limit = 10) {
  const scoredProducts = allProducts
    .filter(product => product.id !== targetProduct.id)
    .map(product => ({
      ...product,
      score: calculateContentSimilarity(targetProduct, product)
    }))
    .sort((a, b) => b.score - a.score)
    .slice(0, limit)
  
  return scoredProducts
}

/**
 * 混合推荐算法
 * @param {Object} user - 用户信息
 * @param {Array} products - 商品列表
 * @param {Number} limit - 推荐数量
 * @returns {Array} 推荐结果
 */
function hybridRecommend(user, products, limit = 10) {
  const results = []
  
  // 1. 协同过滤推荐
  const cfResults = collaborativeFiltering(user.history, products, limit * 2)
  
  // 2. 基于内容的推荐
  const cbResults = contentBased(user.lastViewed || products[0], products, limit * 2)
  
  // 3. 热度推荐
  const popResults = popularityBased(products, limit * 2)
  
  // 混合评分
  const scoredMap = new Map()
  
  // 合并结果并加权
  ;[cfResults, cbResults, popResults].forEach((resultSet, index) => {
    const weight = [0.4, 0.3, 0.3][index] // 权重分配
    
    resultSet.forEach((product, rank) => {
      const score = (limit - rank) / limit * weight
      
      if (scoredMap.has(product.id)) {
        scoredMap.set(product.id, scoredMap.get(product.id) + score)
      } else {
        scoredMap.set(product.id, score)
      }
    })
  })
  
  // 转换为数组并排序
  const finalResults = Array.from(scoredMap.entries())
    .map(([id, score]) => {
      const product = products.find(p => p.id === parseInt(id))
      return { ...product, score }
    })
    .sort((a, b) => b.score - a.score)
    .slice(0, limit)
  
  return finalResults
}

/**
 * 计算用户偏好向量
 */
function calculateUserVector(userHistory) {
  const vector = {
    categories: {},
    priceRange: { min: Infinity, max: 0 },
    tags: {}
  }
  
  userHistory.forEach(behavior => {
    // 分类偏好
    if (behavior.product?.category) {
      vector.categories[behavior.product.category] = 
        (vector.categories[behavior.product.category] || 0) + behavior.weight
    }
    
    // 价格偏好
    if (behavior.product?.price) {
      vector.priceRange.min = Math.min(vector.priceRange.min, behavior.product.price)
      vector.priceRange.max = Math.max(vector.priceRange.max, behavior.product.price)
    }
    
    // 标签偏好
    if (behavior.product?.tags) {
      behavior.product.tags.forEach(tag => {
        vector.tags[tag] = (vector.tags[tag] || 0) + behavior.weight
      })
    }
  })
  
  return vector
}

/**
 * 计算商品与用户偏好的相似度
 */
function calculateSimilarity(userVector, product) {
  let similarity = 0
  
  // 分类相似度
  if (product.category && userVector.categories[product.category]) {
    similarity += RECOMMEND_CONFIG.similarity.category * 
      userVector.categories[product.category]
  }
  
  // 价格相似度
  if (product.price) {
    const priceSimilarity = calculatePriceSimilarity(userVector.priceRange, product.price)
    similarity += RECOMMEND_CONFIG.similarity.price * priceSimilarity
  }
  
  // 标签相似度
  if (product.tags) {
    const tagSimilarity = calculateTagSimilarity(userVector.tags, product.tags)
    similarity += RECOMMEND_CONFIG.similarity.tags * tagSimilarity
  }
  
  return similarity
}

/**
 * 计算价格相似度
 */
function calculatePriceSimilarity(priceRange, price) {
  if (price >= priceRange.min && price <= priceRange.max) {
    return 1
  }
  
  const rangeSize = priceRange.max - priceRange.min
  if (rangeSize === 0) return 0
  
  const distance = Math.min(
    Math.abs(price - priceRange.min),
    Math.abs(price - priceRange.max)
  )
  
  return Math.max(0, 1 - distance / rangeSize)
}

/**
 * 计算标签相似度
 */
function calculateTagSimilarity(userTags, productTags) {
  if (!productTags || productTags.length === 0) return 0
  
  let matchScore = 0
  let totalWeight = 0
  
  productTags.forEach(tag => {
    if (userTags[tag]) {
      matchScore += userTags[tag]
    }
    totalWeight += 1
  })
  
  return totalWeight > 0 ? matchScore / totalWeight : 0
}

/**
 * 计算商品热度评分
 */
function calculatePopularityScore(product) {
  const now = Date.now()
  const daysSinceUpdate = (now - (product.updatedAt || now)) / (1000 * 60 * 60 * 24)
  
  // 时间衰减因子
  const timeDecay = Math.exp(-daysSinceUpdate / 30) // 30天衰减周期
  
  return (
    (product.sales || 0) * 0.5 +           // 销量权重
    (product.rating || 5) * 20 +          // 评分权重
    (product.viewCount || 0) * 0.1 +      // 浏览量权重
    timeDecay * 100                       // 时间衰减权重
  )
}

/**
 * 计算内容相似度
 */
function calculateContentSimilarity(productA, productB) {
  let similarity = 0
  
  // 分类相似度
  if (productA.category === productB.category) {
    similarity += 0.4
  }
  
  // 价格相似度（价格差在20%以内）
  const priceDiff = Math.abs(productA.price - productB.price) / Math.max(productA.price, productB.price)
  if (priceDiff <= 0.2) {
    similarity += 0.3
  }
  
  // 标签相似度
  const commonTags = productA.tags?.filter(tag => 
    productB.tags?.includes(tag)
  )?.length || 0
  const totalTags = new Set([...(productA.tags || []), ...(productB.tags || [])]).size
  
  if (totalTags > 0) {
    similarity += (commonTags / totalTags) * 0.3
  }
  
  return similarity
}

/**
 * 实时推荐（基于当前会话）
 */
function realTimeRecommend(sessionProducts, allProducts, limit = 5) {
  if (sessionProducts.length === 0) {
    return popularityBased(allProducts, limit)
  }
  
  // 使用最近浏览的商品作为基准
  const recentProduct = sessionProducts[sessionProducts.length - 1]
  return contentBased(recentProduct, allProducts, limit)
}

/**
 * A/B 测试推荐算法
 */
function abTestRecommend(user, products, limit = 10) {
  // 根据用户ID分配测试组
  const group = user.id % 3 // 0, 1, 2
  
  switch (group) {
    case 0:
      return collaborativeFiltering(user.history, products, limit)
    case 1:
      return contentBased(user.lastViewed || products[0], products, limit)
    case 2:
      return hybridRecommend(user, products, limit)
    default:
      return popularityBased(products, limit)
  }
}

module.exports = {
  collaborativeFiltering,
  popularityBased,
  contentBased,
  hybridRecommend,
  realTimeRecommend,
  abTestRecommend,
  calculatePopularityScore
}
