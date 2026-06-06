import { describe, expect, it } from 'vitest'
import { parseDatasetFile } from './kittenDatasetParser'

describe('kittenDatasetParser', () => {
  it('keeps sample rows and profiles csv fields for charts', async () => {
    const text = 'date,channel,sales\n2026-01-01,online,100\n2026-01-02,offline,220\n2026-01-03,online,180'
    const file = {
      name: 'sales.csv',
      size: text.length,
      text: () => Promise.resolve(text)
    } as File

    const parsed = await parseDatasetFile(file)

    expect(parsed.rows).toBe(3)
    expect(parsed.sampleRows).toHaveLength(3)
    expect(parsed.sampleRows[0]).toMatchObject({ channel: 'online', sales: 100 })
    expect(parsed.fieldProfiles.find((field) => field.name === 'sales')?.type).toBe('number')
    expect(parsed.fieldProfiles.find((field) => field.name === 'channel')?.type).toBe('category')
  })
})
