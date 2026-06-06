/**
 * 里程碑 K / O：外部/内部客服页 — 物理视图在 Mod 包内。
 */

import { modView } from '@/router/modViews'

const MOD_ID = 'xcagi-customer-service-bridge'
const PREFIX = `/mod/${MOD_ID}`

const modRoutes = [
  {
    path: `${PREFIX}/enterprise-customer-service`,
    name: 'mod-enterprise-customer-service',
    component: modView(MOD_ID, 'EnterpriseCustomerServiceView.vue'),
    meta: { title: '外部客服', mod: MOD_ID, customerServiceSide: 'enterprise' },
  },
  {
    path: `${PREFIX}/internal-customer-service`,
    name: 'mod-internal-customer-service',
    component: modView(MOD_ID, 'InternalCustomerServiceView.vue'),
    meta: { title: '内部客服', mod: MOD_ID, customerServiceSide: 'admin', requiresAdminAccount: true },
  },
]

const modMenu = [
  {
    id: 'mod-enterprise-customer-service',
    label: '外部客服',
    icon: 'fa-headphones',
    path: `${PREFIX}/enterprise-customer-service`,
  },
  {
    id: 'mod-internal-customer-service',
    label: '内部客服',
    icon: 'fa-headphones',
    path: `${PREFIX}/internal-customer-service`,
  },
]

export { modRoutes, modMenu }
