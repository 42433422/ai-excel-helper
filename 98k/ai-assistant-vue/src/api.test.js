import { describe, it, expect, vi } from 'vitest'

describe('API Module Tests', () => {
  it('should export all API modules', () => {
    const apiModules = require('../src/api/index.js')
    expect(apiModules).toBeDefined()
  })

  it('should have chat API', () => {
    const chatApi = require('../src/api/chat.js')
    expect(chatApi).toBeDefined()
  })

  it('should have products API', () => {
    const productsApi = require('../src/api/products.js')
    expect(productsApi).toBeDefined()
  })

  it('should have customers API', () => {
    const customersApi = require('../src/api/customers.js')
    expect(customersApi).toBeDefined()
  })

  it('should have orders API', () => {
    const ordersApi = require('../src/api/orders.js')
    expect(ordersApi).toBeDefined()
  })

  it('should have print API', () => {
    const printApi = require('../src/api/print.js')
    expect(printApi).toBeDefined()
  })

  it('should have wechat API', () => {
    const wechatApi = require('../src/api/wechat.js')
    expect(wechatApi).toBeDefined()
  })

  it('should have materials API', () => {
    const materialsApi = require('../src/api/materials.js')
    expect(materialsApi).toBeDefined()
  })
})

describe('Utils Tests', () => {
  it('should export utils', () => {
    const utils = require('../src/utils/index.js')
    expect(utils).toBeDefined()
  })
})

describe('Composables Tests', () => {
  it('should export useApi', () => {
    const useApi = require('../src/composables/useApi.js')
    expect(useApi).toBeDefined()
  })

  it('should export useProducts', () => {
    const useProducts = require('../src/composables/useProducts.js')
    expect(useProducts).toBeDefined()
  })
})
