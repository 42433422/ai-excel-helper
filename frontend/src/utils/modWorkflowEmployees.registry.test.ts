import { describe, expect, it } from 'vitest'
import {
  filterWorkflowRegistrySourceMods,
  isEmployeePackModEntry,
  isNonWorkflowDeskEmployeeId,
} from './modWorkflowEmployees'
import { mergeModManifestEntries as mergeRegistry } from './workflowEmployeeRegistry'

describe('workflow registry mod/employee separation', () => {
  it('treats employee_pack as non-workflow source', () => {
    expect(
      isEmployeePackModEntry({
        id: 'ppt-generate-employee',
        type: 'employee_pack',
        workflow_employees: [{ id: 'ppt-generate-employee', label: 'PPT' }],
      }),
    ).toBe(true)
    expect(
      isEmployeePackModEntry({
        id: 'xcagi-host-foundation-employee',
        type: 'employee_pack',
      }),
    ).toBe(true)
  })

  it('filters office and host ids from desk registry', () => {
    expect(isNonWorkflowDeskEmployeeId('host_foundation')).toBe(true)
    expect(isNonWorkflowDeskEmployeeId('ppt-generate-employee')).toBe(true)
    expect(isNonWorkflowDeskEmployeeId('label_print')).toBe(false)
  })

  it('mergeModManifestEntries ignores employee_pack rows', () => {
    const merged = mergeRegistry(
      { schemaVersion: 1, employees: [] },
      [
        {
          id: 'ppt-generate-employee',
          type: 'employee_pack',
          name: 'PPT 生成员',
          workflow_employees: [{ id: 'ppt-generate-employee', label: 'PPT' }],
        },
        {
          id: 'xcagi-workflow-employee-label-print',
          name: '标签打印',
          workflow_employees: [{ id: 'label_print', label: '标签打印' }],
        },
      ],
    )
    expect(merged.map((e) => e.id)).toEqual(['label_print'])
    expect(filterWorkflowRegistrySourceMods([
      { id: 'ppt-generate-employee', type: 'employee_pack', workflow_employees: [{ id: 'x', label: 'x' }] },
      { id: 'xcagi-workflow-employee-label-print', workflow_employees: [{ id: 'label_print', label: 'L' }] },
    ])).toHaveLength(1)
  })
})
