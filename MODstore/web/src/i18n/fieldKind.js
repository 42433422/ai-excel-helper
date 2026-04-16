import { i18n } from './index.js'

/** Maps JSON schema style "string[]" to a safe i18n key segment */
const KIND_TO_MESSAGE_KEY = {
  'string[]': 'stringList',
}

/**
 * Localized label for manifest_contract.fields[].kind
 * @param {string} kind
 */
export function fieldKindZh(kind) {
  const k = String(kind || '')
  const sub = KIND_TO_MESSAGE_KEY[k] || k
  const path = `intro.fieldKindLabel.${sub}`
  if (i18n.global.te(path)) return String(i18n.global.t(path))
  return k
}
