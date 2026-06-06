/**
 * 流程可视化 — 物理视图（无 workflow_employees）
 */
import { modView } from '@/router/modViews'

const MOD_ID = 'xcagi-workflow-visualization-bridge'
const PREFIX = `/mod/${MOD_ID}`

const modRoutes = [
  {
    path: `${PREFIX}/workflow-visualization`,
    name: 'mod-workflow-visualization',
    component: modView(MOD_ID, 'WorkflowVisualizationView.vue'),
    meta: { title: '流程可视化', mod: MOD_ID },
  },
]

const modMenu = [
  {
    id: 'mod-workflow-visualization',
    label: '流程可视化',
    icon: 'fa-project-diagram',
    path: `${PREFIX}/workflow-visualization`,
  },
]

export { modRoutes, modMenu }
