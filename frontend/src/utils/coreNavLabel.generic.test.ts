import { describe, expect, it } from 'vitest'
import { resolveCoreNavLabel } from '@/utils/coreNavLabel'

describe('resolveCoreNavLabel generic host defaults', () => {
  it('uses generic labels by default', () => {
    expect(resolveCoreNavLabel('products', '通用', [])).toBe('业务对象')
    expect(resolveCoreNavLabel('orders', '通用', [])).toBe('业务单据')
    expect(resolveCoreNavLabel('materials', '通用', [])).toBe('资源库')
  })

  it('keeps attendance labels scoped to the attendance industry', () => {
    expect(resolveCoreNavLabel('products', '考勤', [])).toBe('人员管理')
    expect(resolveCoreNavLabel('orders', '考勤', [])).toBe('考勤单管理')
    expect(resolveCoreNavLabel('materials', '考勤', [])).toBe('排班资源')
  })
})
