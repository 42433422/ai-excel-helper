const app = getApp()

// 是否启用 Mock 数据（开发模式）
const USE_MOCK = true

/**
 * Mock 数据
 */
const mockData = {
  // 商品列表
  '/products/list': {
    success: true,
    data: {
      items: [
        {
          id: 1,
          name: '高性能涂料 A',
          price: 29900,
          original_price: 39900,
          image: 'https://placehold.co/400x400/f5f5f5/999999?text=Product+1',
          sales: 1234,
          is_hot: true
        },
        {
          id: 2,
          name: '环保固化剂 B',
          price: 15900,
          original_price: 19900,
          image: 'https://placehold.co/400x400/f5f5f5/999999?text=Product+2',
          sales: 856,
          is_hot: false
        },
        {
          id: 3,
          name: '快速稀释剂 C',
          price: 8900,
          original_price: 12900,
          image: 'https://placehold.co/400x400/f5f5f5/999999?text=Product+3',
          sales: 2341,
          is_hot: true
        },
        {
          id: 4,
          name: '多功能助剂 D',
          price: 12900,
          original_price: 16900,
          image: 'https://placehold.co/400x400/f5f5f5/999999?text=Product+4',
          sales: 567,
          is_hot: false
        }
      ],
      total: 4,
      page: 1,
      per_page: 10
    }
  },
  
  // 分类列表
  '/categories': {
    success: true,
    data: [
      { id: 1, name: '全部', icon: 'https://placehold.co/100x100/1890ff/ffffff?text=All' },
      { id: 2, name: '涂料', icon: 'https://placehold.co/100x100/1890ff/ffffff?text=Paint' },
      { id: 3, name: '固化剂', icon: 'https://placehold.co/100x100/1890ff/ffffff?text=Curing' },
      { id: 4, name: '稀释剂', icon: 'https://placehold.co/100x100/1890ff/ffffff?text=Diluent' },
      { id: 5, name: '助剂', icon: 'https://placehold.co/100x100/1890ff/ffffff?text=Auxiliary' },
      { id: 6, name: '工具', icon: 'https://placehold.co/100x100/1890ff/ffffff?text=Tool' }
    ]
  },
  
  // 轮播图
  '/banners': {
    success: true,
    data: [
      { id: 1, image: 'https://via.placeholder.com/750x400/1890ff/ffffff?text=Banner+1' },
      { id: 2, image: 'https://via.placeholder.com/750x400/096dd9/ffffff?text=Banner+2' },
      { id: 3, image: 'https://via.placeholder.com/750x400/1890ff/ffffff?text=Banner+3' }
    ]
  }
}

/**
 * Mock 请求
 */
function mockRequest(url, method, data = {}) {
  return new Promise((resolve, reject) => {
    // 模拟网络延迟
    setTimeout(() => {
      // 查找匹配的 Mock 数据
      for (const [key, value] of Object.entries(mockData)) {
        if (url.includes(key)) {
          console.log('[Mock]', method.toUpperCase(), url)
          resolve(value)
          return
        }
      }
      
      // 未找到 Mock 数据
      console.warn('[Mock] 未找到 Mock 数据:', url)
      reject({ message: '未找到数据' })
    }, 300)
  })
}

/**
 * 封装请求
 * @param {Object} options - 请求配置
 * @returns {Promise}
 */
function request(options) {
  // 如果启用 Mock，则使用 Mock 数据
  if (USE_MOCK) {
    return mockRequest(options.url, options.method || 'GET', options.data)
  }
  
  return new Promise((resolve, reject) => {
    const header = {
      'Content-Type': 'application/json',
    }
    
    // 添加认证 token
    if (app.globalData.token && !options.noAuth) {
      header['Authorization'] = `Bearer ${app.globalData.token}`
    }

    wx.request({
      url: `${app.globalData.baseUrl}${options.url}`,
      method: options.method || 'GET',
      data: options.data,
      header: header,
      timeout: options.timeout || 10000,
      success(res) {
        // 处理 401 未授权
        if (res.statusCode === 401) {
          app.clearToken()
          wx.reLaunch({ url: '/pages/index/index' })
          reject({ code: 401, message: '登录已过期' })
          return
        }
        
        // 处理成功响应
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(res.data)
        } else {
          const errorMessage = res.data?.error || res.data?.message || '请求失败'
          wx.showToast({
            title: errorMessage,
            icon: 'none',
            duration: 2000
          })
          reject(res.data || { message: errorMessage })
        }
      },
      fail(err) {
        console.error('请求失败', err)
        wx.showToast({
          title: '网络错误，请稍后重试',
          icon: 'none',
          duration: 2000
        })
        reject(err)
      }
    })
  })
}

/**
 * GET 请求
 * @param {String} url - 请求地址
 * @param {Object} data - 请求参数
 */
function get(url, data = {}) {
  return request({ url, method: 'GET', data })
}

/**
 * POST 请求
 * @param {String} url - 请求地址
 * @param {Object} data - 请求数据
 */
function post(url, data = {}) {
  return request({ url, method: 'POST', data })
}

/**
 * PUT 请求
 * @param {String} url - 请求地址
 * @param {Object} data - 请求数据
 */
function put(url, data = {}) {
  return request({ url, method: 'PUT', data })
}

/**
 * DELETE 请求
 * @param {String} url - 请求地址
 * @param {Object} data - 请求参数
 */
function del(url, data = {}) {
  return request({ url, method: 'DELETE', data })
}

/**
 * 上传文件
 * @param {String} url - 上传地址
 * @param {String} filePath - 文件路径
 * @param {Object} formData - 表单数据
 */
function uploadFile(url, filePath, formData = {}) {
  return new Promise((resolve, reject) => {
    const header = {
      'Content-Type': 'multipart/form-data',
    }
    
    if (app.globalData.token) {
      header['Authorization'] = `Bearer ${app.globalData.token}`
    }

    wx.uploadFile({
      url: `${app.globalData.baseUrl}${url}`,
      filePath: filePath,
      name: 'file',
      formData: formData,
      header: header,
      success(res) {
        try {
          const data = JSON.parse(res.data)
          resolve(data)
        } catch (e) {
          reject({ message: '解析响应失败' })
        }
      },
      fail(err) {
        console.error('上传失败', err)
        wx.showToast({
          title: '上传失败',
          icon: 'none'
        })
        reject(err)
      }
    })
  })
}

/**
 * 图片预览
 * @param {Array} urls - 图片地址数组
 * @param {Number} current - 当前显示图片的索引
 */
function previewImage(urls, current = 0) {
  wx.previewImage({
    urls: urls,
    current: current
  })
}

/**
 * 页面跳转
 * @param {String} url - 页面地址
 */
function navigateTo(url) {
  wx.navigateTo({ url })
}

/**
 * 返回上一页
 */
function navigateBack() {
  wx.navigateBack()
}

/**
 * 重定向页面
 * @param {String} url - 页面地址
 */
function redirectTo(url) {
  wx.redirectTo({ url })
}

/**
 * 跳转到 tabBar 页面
 * @param {String} url - 页面地址
 */
function switchTab(url) {
  wx.switchTab({ url })
}

/**
 * 关闭所有页面，打开到应用内的某个页面
 * @param {String} url - 页面地址
 */
function reLaunch(url) {
  wx.reLaunch({ url })
}

module.exports = {
  request,
  get,
  post,
  put,
  del,
  uploadFile,
  previewImage,
  navigateTo,
  navigateBack,
  redirectTo,
  switchTab,
  reLaunch
}
