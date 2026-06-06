import { describe, expect, it, afterEach } from 'vitest'
import {
  erpDomainModStatusPath,
  resolveErpApiBase,
  resolveErpApiPath,
} from './erpDomainPaths'
import { XCAGI_ACTIVE_EXTENSION_MOD_ID_KEY } from '@/utils/xcagiStorageKeys'

const LS = 'xcagi_erp_domain_mod_facade_enabled'
const ACTIVE_LS = XCAGI_ACTIVE_EXTENSION_MOD_ID_KEY

describe('erpDomainPaths', () => {
  afterEach(() => {
    localStorage.removeItem(LS)
    localStorage.removeItem(ACTIVE_LS)
  })

  it('defaults to host /api when facade off', () => {
    expect(resolveErpApiBase()).toBe('/api')
    expect(resolveErpApiPath('/api/orders')).toBe('/api/orders')
    expect(resolveErpApiPath('/api/materials')).toBe('/api/materials')
  })

  it('maps products and shipment paths when facade on', () => {
    localStorage.setItem(LS, '1')
    expect(resolveErpApiBase()).toBe('/api/mod/xcagi-erp-domain-bridge')
    expect(resolveErpApiPath('/api/products/list')).toBe(
      '/api/mod/xcagi-erp-domain-bridge/products/list',
    )
    expect(resolveErpApiPath('/api/shipment/shipment-records/units')).toBe(
      '/api/mod/xcagi-erp-domain-bridge/shipment/shipment-records/units',
    )
    expect(resolveErpApiPath('/api/orders?limit=200')).toBe(
      '/api/mod/xcagi-erp-domain-bridge/orders?limit=200',
    )
  })

  it('maps purchase_units and wechat_contacts legacy paths', () => {
    localStorage.setItem(LS, '1')
    expect(resolveErpApiPath('/api/purchase_units')).toBe(
      '/api/mod/xcagi-erp-domain-bridge/purchase_units',
    )
    expect(resolveErpApiPath('/api/wechat_contacts/ensure_contact_cache')).toBe(
      '/api/mod/xcagi-erp-domain-bridge/wechat_contacts/ensure_contact_cache',
    )
  })

  it('keeps host-only prefixes on /api when facade on', () => {
    localStorage.setItem(LS, '1')
    expect(resolveErpApiPath('/api/materials')).toBe('/api/materials')
    expect(resolveErpApiPath('/api/print/label')).toBe('/api/print/label')
    expect(resolveErpApiPath('/api/approval/requests')).toBe('/api/approval/requests')
  })

  it('maps orders next_number when facade on', () => {
    localStorage.setItem(LS, '1')
    expect(resolveErpApiPath('/api/orders/next_number?suffix=A')).toBe(
      '/api/mod/xcagi-erp-domain-bridge/orders/next_number?suffix=A',
    )
  })

  it('exposes mod status probe path', () => {
    expect(erpDomainModStatusPath()).toBe('/api/mod/xcagi-erp-domain-bridge/status')
  })

  it('prefers active protected client mod for products/customers/units; orders via erp bridge', () => {
    localStorage.setItem(LS, '1')
    localStorage.setItem(ACTIVE_LS, 'taiyangniao-pro')
    const ids = ['taiyangniao-pro', 'xcagi-erp-domain-bridge']
    expect(resolveErpApiBase(ids)).toBe('/api/mod/taiyangniao-pro')
    expect(resolveErpApiPath('/api/products/list', ids)).toBe(
      '/api/mod/taiyangniao-pro/products/list',
    )
    expect(resolveErpApiPath('/api/orders?limit=200', ids)).toBe(
      '/api/mod/xcagi-erp-domain-bridge/orders?limit=200',
    )
    expect(resolveErpApiPath('/api/shipment/shipment-records/units', ids)).toBe(
      '/api/mod/taiyangniao-pro/shipment/shipment-records/units',
    )
    expect(resolveErpApiPath('/api/purchase_units', ids)).toBe(
      '/api/mod/taiyangniao-pro/purchase_units',
    )
    expect(resolveErpApiPath('/api/shipment/shipment-records/records', ids)).toBe(
      '/api/mod/xcagi-erp-domain-bridge/shipment/shipment-records/records',
    )
  })

  it('falls back to erp bridge when client mod not in installed list', () => {
    localStorage.setItem(ACTIVE_LS, 'taiyangniao-pro')
    const ids = ['xcagi-erp-domain-bridge']
    expect(resolveErpApiPath('/api/customers/list', ids)).toBe(
      '/api/mod/xcagi-erp-domain-bridge/customers/list',
    )
  })

  it('keeps wechat_contacts on host API when active client mod is taiyangniao-pro', () => {
    localStorage.setItem(ACTIVE_LS, 'taiyangniao-pro')
    expect(resolveErpApiPath('/api/wechat_contacts/work_mode_feed?per_contact=1')).toBe(
      '/api/wechat_contacts/work_mode_feed?per_contact=1',
    )
  })
})
