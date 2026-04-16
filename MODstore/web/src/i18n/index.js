import { createI18n } from 'vue-i18n'
import zhCN from '../locales/zh-CN.js'
import enUS from '../locales/en-US.js'

export const LOCALE_STORAGE_KEY = 'modstore-locale'

function readSavedLocale() {
  try {
    const s = localStorage.getItem(LOCALE_STORAGE_KEY)
    if (s === 'en-US' || s === 'zh-CN') return s
  } catch {
    /* ignore */
  }
  return 'zh-CN'
}

export const i18n = createI18n({
  legacy: false,
  globalInjection: true,
  locale: readSavedLocale(),
  fallbackLocale: 'zh-CN',
  messages: {
    'zh-CN': zhCN,
    'en-US': enUS,
  },
  missingWarn: false,
  fallbackWarn: false,
})

export function persistLocale(code) {
  try {
    localStorage.setItem(LOCALE_STORAGE_KEY, code)
  } catch {
    /* ignore */
  }
}
