/**
 * Strip real business values from template preview payloads while keeping shape
 * (headers / grid structure). Used by 模板预览 and 业务对接保存.
 */
export function stripSampleRowsKeepTemplateShape(sampleRows, fallbackFields) {
  const rows = Array.isArray(sampleRows) ? sampleRows : []
  if (!rows.length) {
    const keys = (fallbackFields || []).map((f) => String(f?.label || '').trim()).filter(Boolean)
    return keys.length ? [keys.reduce((acc, k) => { acc[k] = ''; return acc }, {})] : []
  }
  const first = rows[0] || {}
  const keys = Object.keys(first)
  if (!keys.length) return []
  return [keys.reduce((acc, k) => { acc[k] = ''; return acc }, {})]
}

export function stripGridPreviewData(gridPreview, sampleRows) {
  const grid = gridPreview && typeof gridPreview === 'object' ? JSON.parse(JSON.stringify(gridPreview)) : null
  if (!grid || !Array.isArray(grid.rows)) return grid

  const sampleValueSet = new Set()
  ;(Array.isArray(sampleRows) ? sampleRows : []).forEach((row) => {
    Object.values(row || {}).forEach((v) => {
      const text = String(v ?? '').trim()
      if (text) sampleValueSet.add(text)
    })
  })

  const looksLikeDynamicValue = (text, rowIndex) => {
    const t = String(text || '').trim()
    if (!t) return false
    if (sampleValueSet.has(t)) return true
    if (rowIndex <= 1) return false
    if (/^\d+(\.\d+)?$/.test(t)) return true
    if (/^\d{4,}$/.test(t)) return true
    if (/^\d{2,4}[-/年]\d{1,2}([-/月]\d{1,2})?/.test(t)) return true
    return false
  }

  grid.rows = grid.rows.map((row, rowIndex) => {
    if (!Array.isArray(row)) return row
    return row.map((cell) => {
      if (cell && typeof cell === 'object') {
        const cloned = { ...cell }
        if (looksLikeDynamicValue(cloned.text, rowIndex)) {
          cloned.text = ''
        }
        return cloned
      }
      if (looksLikeDynamicValue(cell, rowIndex)) return ''
      return cell
    })
  })
  return grid
}
