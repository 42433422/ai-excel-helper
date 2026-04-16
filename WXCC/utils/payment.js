/**
 * 支付工具函数
 */

/**
 * 发起微信支付
 * @param {Object} options - 支付选项
 * @param {String} options.orderId - 订单 ID
 * @param {Number} options.amount - 支付金额（单位：分）
 * @param {String} options.description - 商品描述
 * @returns {Promise}
 */
function requestPayment(options) {
  return new Promise((resolve, reject) => {
    const { orderId, amount, description } = options

    // 调用后端获取支付参数
    const { post } = require('./request')
    
    post('/payment/wechat', {
      order_id: orderId,
      amount: amount,
      description: description
    })
      .then(res => {
        if (res && res.success) {
          // 调起微信支付
          wx.requestPayment({
            timeStamp: res.data.timeStamp,
            nonceStr: res.data.nonceStr,
            package: res.data.package,
            signType: res.data.signType,
            paySign: res.data.paySign,
            success: (payRes) => {
              console.log('支付成功', payRes)
              resolve({ success: true, data: payRes })
            },
            fail: (payErr) => {
              console.error('支付失败', payErr)
              if (payErr.errMsg.includes('cancel')) {
                reject({ code: 'cancel', message: '用户取消支付' })
              } else {
                reject({ code: 'fail', message: '支付失败' })
              }
            }
          })
        } else {
          reject({ code: 'error', message: res?.error || '获取支付参数失败' })
        }
      })
      .catch(err => {
        console.error('获取支付参数失败', err)
        reject({ code: 'error', message: '获取支付参数失败' })
      })
  })
}

/**
 * 查询支付结果
 * @param {String} orderId - 订单 ID
 * @returns {Promise}
 */
function queryPaymentResult(orderId) {
  const { get } = require('./request')
  
  return get('/payment/query', { order_id: orderId })
}

/**
 * 申请退款
 * @param {Object} options - 退款选项
 * @param {String} options.orderId - 订单 ID
 * @param {Number} options.amount - 退款金额（单位：分）
 * @param {String} options.reason - 退款原因
 * @returns {Promise}
 */
function requestRefund(options) {
  const { post } = require('./request')
  
  return post('/payment/refund', options)
}

module.exports = {
  requestPayment,
  queryPaymentResult,
  requestRefund
}
