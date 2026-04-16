/**
 * 分享工具函数
 */

const app = getApp()

/**
 * 生成分享海报数据
 * @param {Object} options - 分享选项
 * @param {String} options.type - 分享类型：product, order, activity
 * @param {Object} options.data - 分享数据
 * @returns {Object}
 */
function generateShareData(options) {
  const { type, data } = options
  
  const shareData = {
    title: '',
    path: '',
    imageUrl: ''
  }

  switch (type) {
    case 'product':
      // 商品分享
      shareData.title = data.name || '精选好物'
      shareData.path = `/pages/product/detail/detail?id=${data.id}`
      shareData.imageUrl = data.image || ''
      break

    case 'order':
      // 订单分享
      shareData.title = `我在 XCAGI 购买了${data.productName}`
      shareData.path = `/pages/order/detail/detail?id=${data.id}`
      shareData.imageUrl = data.image || ''
      break

    case 'activity':
      // 活动分享
      shareData.title = data.title || '精彩活动'
      shareData.path = data.path || '/pages/index/index'
      shareData.imageUrl = data.image || ''
      break

    default:
      // 默认分享
      shareData.title = 'XCAGI 智能采购商城'
      shareData.path = '/pages/index/index'
      shareData.imageUrl = ''
  }

  return shareData
}

/**
 * 显示分享菜单
 * @param {Object} options - 分享选项
 */
function showShareMenu(options = {}) {
  const shareData = generateShareData(options)

  // 显示微信原生分享菜单
  wx.showShareMenu({
    withShareTicket: true,
    showShareItems: ['wechatFriends', 'wechatMoment']
  })

  // 保存到剪贴板
  if (options.copyLink) {
    const baseUrl = app.globalData.baseUrl.replace('/api/mp/v1', '')
    const fullUrl = `${baseUrl}${shareData.path}`
    
    wx.setClipboardData({
      data: fullUrl,
      success: () => {
        wx.showToast({
          title: '链接已复制',
          icon: 'success'
        })
      }
    })
  }
}

/**
 * 生成分享海报（需要 Canvas 支持）
 * @param {Object} options - 海报选项
 * @returns {Promise}
 */
function generateSharePoster(options) {
  return new Promise((resolve, reject) => {
    const { product, width = 750, height = 1200 } = options

    // 创建 Canvas 绘制海报
    const query = wx.createSelectorQuery()
    query.select('#posterCanvas')
      .fields({ node: true, size: true })
      .exec((res) => {
        if (!res[0]) {
          reject(new Error('Canvas 未找到'))
          return
        }

        const canvas = res[0].node
        const ctx = canvas.getContext('2d')

        // 设置 Canvas 尺寸
        const dpr = wx.getSystemInfoSync().pixelRatio
        canvas.width = width * dpr
        canvas.height = height * dpr
        ctx.scale(dpr, dpr)

        // 绘制背景
        ctx.fillStyle = '#ffffff'
        ctx.fillRect(0, 0, width, height)

        // 绘制商品图片
        if (product.image) {
          const img = canvas.createImage()
          img.src = product.image
          img.onload = () => {
            ctx.drawImage(img, 40, 40, width - 80, width - 80)

            // 绘制商品名称
            ctx.fillStyle = '#333333'
            ctx.font = 'bold 36px sans-serif'
            ctx.fillText(product.name, 40, width + 100)

            // 绘制价格
            ctx.fillStyle = '#f5222d'
            ctx.font = 'bold 48px sans-serif'
            ctx.fillText(`¥${product.price}`, 40, width + 180)

            // 绘制小程序码
            const codeImg = canvas.createImage()
            codeImg.src = '/assets/qrcode.png'
            codeImg.onload = () => {
              ctx.drawImage(codeImg, width / 2 - 100, height - 300, 200, 200)
              
              // 绘制提示文字
              ctx.fillStyle = '#999999'
              ctx.font = '24px sans-serif'
              ctx.fillText('长按识别小程序码', width / 2 - 100, height - 80)

              // 导出图片
              wx.canvasToTempFilePath({
                canvas: canvas,
                success: (res) => {
                  resolve(res.tempFilePath)
                },
                fail: reject
              })
            }
          }
        } else {
          reject(new Error('商品图片不存在'))
        }
      })
  })
}

/**
 * 分享商品到微信好友
 * @param {Object} product - 商品信息
 */
function shareProduct(product) {
  const shareData = generateShareData({
    type: 'product',
    data: product
  })

  return {
    title: shareData.title,
    path: shareData.path,
    imageUrl: shareData.imageUrl
  }
}

module.exports = {
  generateShareData,
  showShareMenu,
  generateSharePoster,
  shareProduct
}
