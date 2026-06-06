import type { RouteLocationRaw } from 'vue-router'
import { CORE_WORKFLOW_MOD_ID, readCoreWorkflowModPagesEnabled } from '@/constants/coreWorkflowMod'
import {
  OFFICE_EMPLOYEE_PACK_BRIDGE_MOD_ID,
  readOfficeEmployeePackModPagesEnabled,
} from '@/constants/officeEmployeePackMod'

const WORKFLOW_VIZ_MOD_PATH = `/mod/${CORE_WORKFLOW_MOD_ID}/workflow-visualization`
const OTHER_TOOLS_MOD_PATH = `/mod/${OFFICE_EMPLOYEE_PACK_BRIDGE_MOD_ID}/other-tools`

/** 流程全景 / 工作流可视化页路由（Mod 门面开启时走物理视图路径） */
export function resolveWorkflowVisualizationLocation(): RouteLocationRaw {
  if (readCoreWorkflowModPagesEnabled()) {
    return { path: WORKFLOW_VIZ_MOD_PATH }
  }
  return { name: 'workflow-visualization' }
}

/** 员工工作流管理页（office pack 门面开启时走 Mod 路径） */
export function resolveOtherToolsLocation(): RouteLocationRaw {
  if (readOfficeEmployeePackModPagesEnabled()) {
    return { path: OTHER_TOOLS_MOD_PATH }
  }
  return { name: 'other-tools' }
}

export function workflowVisualizationModPath(): string {
  return WORKFLOW_VIZ_MOD_PATH
}
