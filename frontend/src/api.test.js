import { describe, it, expect } from 'vitest'

describe('API Module Tests', () => {
  it('should export all API modules', async () => {
    const apiModules = await import('../src/api/index')
    expect(apiModules).toBeDefined()
  })

  it('should have chat API', async () => {
    const chatApi = await import('../src/api/chat')
    expect(chatApi).toBeDefined()
  })

  it('should have products API', async () => {
    const productsApi = await import('../src/api/products')
    expect(productsApi).toBeDefined()
  })

  it('should have customers API', async () => {
    const customersApi = await import('../src/api/customers')
    expect(customersApi).toBeDefined()
  })

  it('should have orders API', async () => {
    const ordersApi = await import('../src/api/orders')
    expect(ordersApi).toBeDefined()
  })

  it('should have print API', async () => {
    const printApi = await import('../src/api/print')
    expect(printApi).toBeDefined()
  })

  it('should have wechat API', async () => {
    const wechatApi = await import('../src/api/wechat')
    expect(wechatApi).toBeDefined()
  })

  it('should have materials API', async () => {
    const materialsApi = await import('../src/api/materials')
    expect(materialsApi).toBeDefined()
  })
})

describe('Utils Tests', () => {
  it('should export utils', async () => {
    const utils = await import('../src/utils/index')
    expect(utils).toBeDefined()
  })
})

describe('Composables Tests', () => {
  it('should export useApi', async () => {
    const useApi = await import('../src/composables/useApi')
    expect(useApi).toBeDefined()
  })

  it('should export useProducts', async () => {
    const useProducts = await import('../src/composables/useProducts')
    expect(useProducts).toBeDefined()
  })
})
