import { describe, expect, it, afterEach } from 'vitest'
import {
  resolveOtherToolsLocation,
  resolveWorkflowVisualizationLocation,
  workflowVisualizationModPath,
} from './workflowNav'

const CORE_LS = 'xcagi_workflow_viz_mod_pages_enabled'
const OFFICE_LS = 'xcagi_office_employee_pack_mod_pages_enabled'

describe('workflowNav', () => {
  afterEach(() => {
    localStorage.removeItem(CORE_LS)
    localStorage.removeItem(OFFICE_LS)
  })

  it('uses host route names when mod facades off', () => {
    expect(resolveWorkflowVisualizationLocation()).toEqual({ name: 'workflow-visualization' })
    expect(resolveOtherToolsLocation()).toEqual({ name: 'other-tools' })
  })

  it('uses mod paths when facades on', () => {
    localStorage.setItem(CORE_LS, '1')
    localStorage.setItem(OFFICE_LS, '1')
    expect(resolveWorkflowVisualizationLocation()).toEqual({
      path: workflowVisualizationModPath(),
    })
    expect(resolveOtherToolsLocation()).toEqual({
      path: '/mod/xcagi-office-employee-pack-bridge/other-tools',
    })
  })
})
