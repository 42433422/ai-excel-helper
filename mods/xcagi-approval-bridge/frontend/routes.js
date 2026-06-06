/**
 * 里程碑 K / O+：审批中心 — 物理视图在 Mod 包内。
 */

import { modView } from '@/router/modViews'

const MOD_ID = 'xcagi-approval-bridge'
const PREFIX = `/mod/${MOD_ID}`

const modRoutes = [
  {
    path: `${PREFIX}/approval-hub`,
    name: 'mod-approval-hub',
    component: modView(MOD_ID, 'ApprovalHubView.vue'),
    redirect: { name: 'mod-approval-workspace' },
    meta: { title: '审批中心', mod: MOD_ID },
    children: [
      {
        path: 'workspace',
        name: 'mod-approval-workspace',
        component: modView(MOD_ID, 'ApprovalWorkspaceView.vue'),
        meta: { title: '审批工作台', mod: MOD_ID },
      },
      {
        path: 'flow-management',
        name: 'mod-approval-flow-management',
        component: modView(MOD_ID, 'ApprovalFlowManagementView.vue'),
        meta: { title: '审批流程管理', mod: MOD_ID },
      },
      {
        path: 'rules',
        name: 'mod-approval-rules',
        component: modView(MOD_ID, 'ApprovalRulesView.vue'),
        meta: { title: '审批规则配置', mod: MOD_ID },
      },
    ],
  },
]

const modMenu = [
  {
    id: 'mod-approval-hub',
    label: '审批中心',
    icon: 'fa-check-square-o',
    path: `${PREFIX}/approval-hub/workspace`,
  },
]

export { modRoutes, modMenu }
