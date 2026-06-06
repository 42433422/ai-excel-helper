/**
 * 里程碑 K / O+：模型付费业务页 — 物理视图在 Mod 包内。
 */

import { modView } from '@/router/modViews'

const MOD_ID = 'xcagi-model-payment-bridge'
const PREFIX = `/mod/${MOD_ID}`

const modRoutes = [
  {
    path: `${PREFIX}/model-payment`,
    name: 'mod-model-payment',
    component: modView(MOD_ID, 'ModelPaymentRedirectView.vue'),
    meta: { title: '模型服务', mod: MOD_ID },
  },
  {
    path: `${PREFIX}/kitten-finance`,
    name: 'mod-kitten-finance',
    component: modView(MOD_ID, 'KittenFinanceView.vue'),
    meta: { title: '财务分析', mod: MOD_ID },
  },
]

const modMenu = [
  {
    id: 'mod-kitten-finance',
    label: '财务分析',
    icon: 'fa-line-chart',
    path: `${PREFIX}/kitten-finance`,
  },
]

export { modRoutes, modMenu }
