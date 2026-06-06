/**
 * 里程碑 K / O：局域网授权页 — 物理视图在 Mod 包内。
 */

import { modView } from '@/router/modViews'

const MOD_ID = 'xcagi-lan-license-bridge'
const PREFIX = `/mod/${MOD_ID}`

const modRoutes = [
  {
    path: `${PREFIX}/lan-gate`,
    name: 'mod-lan-gate',
    component: modView(MOD_ID, 'LanGateView.vue'),
    meta: { title: '局域网授权', mod: MOD_ID, publicAccess: true, hideChrome: true },
  },
]

/** 侧栏入口改由商店安装的 lan-gate-ai-employee 提供；bridge 仅保留路由与 API 门面 */
const modMenu = []

export { modRoutes, modMenu }
