import { describe, it, expect } from 'vitest'
import {
  resolvePhoneAgentApiBase,
  countManifestWorkflowEmployeeRows,
  findWorkflowEmployeeEntry,
  getPhoneAgentApiBaseForEmployeeId,
  isPhoneAgentStatusEmployee,
  isWorkflowPlaceholderEmployee,
  getActivePhoneAgentPollTarget,
  buildModWorkflowPanelMeta,
} from './modWorkflowEmployees'

describe('resolvePhoneAgentApiBase', () => {
  it('returns trimmed full api base without trailing slashes', () => {
    expect(
      resolvePhoneAgentApiBase(
        { id: 'x', label: 'L', phone_agent_api_base: '/api/mod/m1/agent//' },
        'm1'
      )
    ).toBe('/api/mod/m1/agent')
  })

  it('builds path from phone_agent_base_path and modId', () => {
    expect(
      resolvePhoneAgentApiBase(
        { id: 'p', label: 'P', phone_agent_base_path: '/phone-agent/' },
        'mod-a'
      )
    ).toBe('/api/mod/mod-a/phone-agent')
  })

  it('prefers phone_agent_api_base over relative path', () => {
    expect(
      resolvePhoneAgentApiBase(
        {
          id: 'p',
          label: 'P',
          phone_agent_api_base: '/api/mod/x/root',
          phone_agent_base_path: 'ignored',
        },
        'mod-a'
      )
    ).toBe('/api/mod/x/root')
  })

  it('returns null when no phone config', () => {
    expect(resolvePhoneAgentApiBase({ id: 'p', label: 'P' }, 'm')).toBe(null)
    expect(resolvePhoneAgentApiBase(undefined, 'm')).toBe(null)
  })
})

describe('countManifestWorkflowEmployeeRows', () => {
  it('dedupes same id across mods', () => {
    expect(
      countManifestWorkflowEmployeeRows([
        {
          id: 'a',
          workflow_employees: [
            { id: 'dup', label: '1' },
            { id: 'other', label: '2' },
          ],
        },
        { id: 'b', workflow_employees: [{ id: 'dup', label: 'shadow' }] },
      ])
    ).toBe(2)
  })

  it('handles empty and trims ids', () => {
    expect(countManifestWorkflowEmployeeRows(undefined)).toBe(0)
    expect(
      countManifestWorkflowEmployeeRows([
        { id: 'm', workflow_employees: [{ id: '  ', label: 'x' }, { id: 'ok', label: 'y' }] },
      ])
    ).toBe(1)
  })
})

describe('findWorkflowEmployeeEntry', () => {
  const mods = [
    {
      id: 'm1',
      name: 'Mod One',
      workflow_employees: [{ id: 'e1', label: 'E1', panel_summary: 'S' }],
    },
  ]

  it('returns merged entry with modId and modName', () => {
    const e = findWorkflowEmployeeEntry(mods, 'e1')
    expect(e).not.toBe(null)
    expect(e!.modId).toBe('m1')
    expect(e!.modName).toBe('Mod One')
    expect(e!.label).toBe('E1')
  })

  it('returns null when missing', () => {
    expect(findWorkflowEmployeeEntry(mods, 'none')).toBe(null)
    expect(findWorkflowEmployeeEntry(undefined, 'e1')).toBe(null)
  })
})

describe('getPhoneAgentApiBaseForEmployeeId', () => {
  it('delegates to manifest resolution', () => {
    const mods = [
      {
        id: 'mid',
        workflow_employees: [
          { id: 'call', label: 'C', phone_agent_base_path: 'phone-agent' },
        ],
      },
    ]
    expect(getPhoneAgentApiBaseForEmployeeId(mods, 'call')).toBe('/api/mod/mid/phone-agent')
    expect(getPhoneAgentApiBaseForEmployeeId(mods, 'nope')).toBe(null)
  })
})

describe('isPhoneAgentStatusEmployee', () => {
  it('is false when poll explicitly disabled', () => {
    const mods = [
      {
        id: 'm',
        workflow_employees: [
          {
            id: 'x',
            label: 'X',
            phone_agent_base_path: 'p',
            phone_agent_status_poll: false,
          },
        ],
      },
    ]
    expect(isPhoneAgentStatusEmployee(mods, 'x')).toBe(false)
  })

  it('is true when base exists and poll not false', () => {
    const mods = [
      {
        id: 'm',
        workflow_employees: [
          { id: 'x', label: 'X', phone_agent_api_base: '/api/mod/m/p', phone_agent_status_poll: true },
        ],
      },
    ]
    expect(isPhoneAgentStatusEmployee(mods, 'x')).toBe(true)
  })
})

describe('isWorkflowPlaceholderEmployee', () => {
  it('detects workflow_placeholder and workflow_ui_kind', () => {
    const mods = [
      {
        id: 'm',
        workflow_employees: [
          { id: 'a', label: 'A', workflow_placeholder: true },
          { id: 'b', label: 'B', workflow_ui_kind: 'placeholder' as const },
        ],
      },
    ]
    expect(isWorkflowPlaceholderEmployee(mods, 'a')).toBe(true)
    expect(isWorkflowPlaceholderEmployee(mods, 'b')).toBe(true)
    expect(isWorkflowPlaceholderEmployee(mods, 'c')).toBe(false)
  })
})

describe('getActivePhoneAgentPollTarget', () => {
  it('returns first enabled employee with poll base', () => {
    const mods = [
      {
        id: 'm1',
        workflow_employees: [
          { id: 'off', label: 'O', phone_agent_api_base: '/api/x', phone_agent_status_poll: true },
          { id: 'on', label: 'N', phone_agent_api_base: '/api/y', phone_agent_status_poll: true },
        ],
      },
    ]
    const enabled = { off: false, on: true }
    expect(getActivePhoneAgentPollTarget(mods, enabled)).toEqual({
      empId: 'on',
      apiBase: '/api/y',
    })
  })

  it('skips when poll disabled', () => {
    const mods = [
      {
        id: 'm',
        workflow_employees: [
          {
            id: 'x',
            label: 'X',
            phone_agent_api_base: '/api/x',
            phone_agent_status_poll: false,
          },
        ],
      },
    ]
    expect(getActivePhoneAgentPollTarget(mods, { x: true })).toBe(null)
  })
})

describe('buildModWorkflowPanelMeta', () => {
  it('builds title and summary with dedupe by id', () => {
    const meta = buildModWorkflowPanelMeta([
      {
        id: 'm',
        name: 'MyMod',
        workflow_employees: [
          {
            id: 'w1',
            label: 'Worker',
            panel_title: '自定义标题',
            panel_summary: '自定义摘要',
          },
          { id: 'w1', label: 'Dup', panel_title: 'ignored' },
        ],
      },
    ])
    expect(meta.w1).toEqual({ title: '自定义标题', summary: '自定义摘要' })
  })

  it('uses defaults when panel fields missing', () => {
    const meta = buildModWorkflowPanelMeta([
      { id: 'm', name: 'NM', workflow_employees: [{ id: 'only', label: 'L' }] },
    ])
    expect(meta.only.title).toBe('工作流 · L')
    expect(meta.only.summary).toContain('NM')
    expect(meta.only.summary).toContain('L')
  })
})
