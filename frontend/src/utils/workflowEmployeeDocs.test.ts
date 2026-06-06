import { describe, expect, it } from 'vitest'
import bundledDocs from '@/data/workflow-employee-docs.json'
import {
  applyWorkflowEmployeeDocsRuntime,
  mergeManifestWorkflowEmployeesIntoDocs,
  normalizeWorkflowEmployeeDocs,
} from './workflowEmployeeDocs'
import type { WorkflowDocsRuntimeContext } from './workflowEmployeeDocs'
import { WORKFLOW_EMPLOYEE_MOD_IDS } from '@/constants/workflowEmployeeMods'

const baseDocs = () =>
  normalizeWorkflowEmployeeDocs(bundledDocs as import('@/types/workflowEmployeeDocs').WorkflowEmployeeDocsV1)

const sixModsCtx: WorkflowDocsRuntimeContext = {
  clientModsUiOff: false,
  modsDisabledByServer: false,
  isModsListLoaded: true,
  modsForUi: WORKFLOW_EMPLOYEE_MOD_IDS.map((id, i) => ({
    id,
    name: `员工 Mod ${i + 1}`,
    workflow_employees: [
      {
        id: ['label_print', 'shipment_mgmt', 'receipt_confirm', 'wechat_msg', 'wechat_phone', 'real_phone'][i],
        label: `员工 ${i + 1}`,
        panel_summary: '测试摘要',
      },
    ],
  })),
}

const activeCtx: WorkflowDocsRuntimeContext = {
  clientModsUiOff: false,
  modsDisabledByServer: false,
  isModsListLoaded: true,
  modsForUi: [
    {
      id: 'wechat-contacts-ai-employee',
      name: '微信触点 AI 员工',
      workflow_employees: [
        {
          id: 'wechat_contacts_hub',
          label: '微信触点管家',
          panel_summary: '侧栏微信联系人与副窗配合。',
          workflow_placeholder: true,
        },
      ],
    },
  ],
}

const inactiveCtx: WorkflowDocsRuntimeContext = {
  clientModsUiOff: false,
  modsDisabledByServer: false,
  isModsListLoaded: true,
  modsForUi: [{ id: 'empty-pack', name: '无员工包' }],
}

describe('workflowEmployeeDocs', () => {
  it('bundled docs have no static employee branches', () => {
    const d = baseDocs()
    expect(d.branches).toHaveLength(0)
    expect(d.flows).toHaveLength(0)
  })

  it('merges manifest employees into branches and flows when mod active', () => {
    const merged = mergeManifestWorkflowEmployeesIntoDocs(baseDocs(), activeCtx)
    expect(merged.branches.some((b) => b.id === 'wechat_contacts_hub')).toBe(true)
    expect(merged.flows.some((f) => f.id === 'wechat_contacts_hub')).toBe(true)
    const branch = merged.branches.find((b) => b.id === 'wechat_contacts_hub')
    expect(branch?.kind).toBe('mod_extension')
  })

  it('does not merge when no manifest workflow_employees', () => {
    const merged = mergeManifestWorkflowEmployeesIntoDocs(baseDocs(), inactiveCtx)
    expect(merged.branches).toHaveLength(0)
    expect(merged.flows).toHaveLength(0)
  })

  it('applyWorkflowEmployeeDocsRuntime shows installed count for six mods', () => {
    const out = applyWorkflowEmployeeDocsRuntime(baseDocs(), sixModsCtx)
    expect(out.pipelineBranchLabel).toContain('6')
    expect(out.branches).toHaveLength(6)
    expect(out.flows).toHaveLength(6)
  })

  it('applyWorkflowEmployeeDocsRuntime includes extension copy', () => {
    const out = applyWorkflowEmployeeDocsRuntime(baseDocs(), activeCtx)
    expect(out.pipelineBranchLabel).toContain('1')
    expect(out.branches.some((b) => b.id === 'wechat_contacts_hub')).toBe(true)
  })
})
