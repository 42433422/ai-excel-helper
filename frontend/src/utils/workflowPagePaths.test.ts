import { describe, expect, it, afterEach } from 'vitest'
import {
  resolveWorkflowPageRedirectForRouteName,
  useWorkflowModPages,
} from './workflowPagePaths'

const LS = 'xcagi_workflow_viz_mod_pages_enabled'

describe('workflowPagePaths', () => {
  afterEach(() => {
    localStorage.removeItem(LS)
  })

  it('keeps host route when facade off', () => {
    expect(useWorkflowModPages()).toBe(false)
    expect(resolveWorkflowPageRedirectForRouteName('workflow-visualization')).toBeNull()
  })

  it('maps workflow-visualization to mod path when facade on', () => {
    localStorage.setItem(LS, '1')
    expect(useWorkflowModPages()).toBe(true)
    expect(resolveWorkflowPageRedirectForRouteName('workflow-visualization')).toBe(
      '/mod/xcagi-workflow-visualization-bridge/workflow-visualization',
    )
  })
})
