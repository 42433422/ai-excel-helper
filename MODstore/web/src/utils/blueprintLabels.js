import { i18n } from '../i18n/index.js'

/** 英文：snake_case → 可读标题（非 i18n，无逐词翻译表） */
function humanizeSnakeCaseEn(s) {
  if (!s || typeof s !== 'string') return ''
  return s
    .split('_')
    .filter(Boolean)
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase())
    .join(' ')
}

/**
 * 蓝图路由表「函数」列展示名。
 * - en-US：算法格式化（英文 UI 惯例）
 * - zh-CN：走 vue-i18n 键 `intro.modDetail.bpSegments.<片段>`（文案在 copy/zhIntro.js → locales/zh-CN）
 *
 * @param {string} fn
 * @param {string} locale vue-i18n locale
 */
export function blueprintFunctionLabel(fn, locale) {
  const f = String(fn || '')
  if (!f) return ''
  if (locale === 'en-US') return humanizeSnakeCaseEn(f)
  if (locale === 'zh-CN') {
    const g = i18n.global
    const parts = f.split('_').filter(Boolean)
    const mapped = parts.map((p) => {
      const key = `intro.modDetail.bpSegments.${p.toLowerCase()}`
      return g.te(key) ? String(g.t(key)) : null
    })
    if (mapped.length && mapped.every(Boolean)) return mapped.join('')
  }
  return f
}
