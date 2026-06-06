/**
 * 里程碑 R：工具 / 员工工作流页 — 物理视图在 Mod 包内。
 */

import { modView } from '@/router/modViews'

const MOD_ID = 'xcagi-office-employee-pack-bridge'
const PREFIX = `/mod/${MOD_ID}`

const modRoutes = [
  {
    path: `${PREFIX}/tools`,
    name: 'mod-office-tools',
    component: modView(MOD_ID, 'ToolsView.vue'),
    meta: { title: '工具', mod: MOD_ID },
  },
  {
    path: `${PREFIX}/other-tools`,
    name: 'mod-office-other-tools',
    component: modView(MOD_ID, 'OtherToolsView.vue'),
    meta: { title: '员工工作流', mod: MOD_ID },
  },
]

const modMenu = [
  { id: 'mod-office-tools', label: '工具', icon: 'fa-wrench', path: `${PREFIX}/tools` },
  { id: 'mod-office-other-tools', label: '员工工作流', icon: 'fa-users', path: `${PREFIX}/other-tools` },
]

export { modRoutes, modMenu }
