/**
 * v-html 统一消毒入口（DOMPurify）。禁止在模板中写 v-html="原始字符串"。
 */
import DOMPurify, { type Config, type UponSanitizeAttributeHookEvent } from 'dompurify'
import { renderMarkdown, stripInternalMarkers } from '@/utils/lightMarkdown'

const CHAT_BUBBLE_CONFIG: Config = {
  ALLOWED_TAGS: [
    'a',
    'abbr',
    'b',
    'br',
    'blockquote',
    'caption',
    'code',
    'col',
    'colgroup',
    'div',
    'em',
    'h1',
    'h2',
    'h3',
    'h4',
    'h5',
    'h6',
    'hr',
    'i',
    'li',
    'ol',
    'p',
    'pre',
    'span',
    'strong',
    'sub',
    'sup',
    'table',
    'tbody',
    'td',
    'tfoot',
    'th',
    'thead',
    'tr',
    'ul',
    'del',
    'ins',
    'kbd',
    'mark',
    'small',
    'time'
  ],
  ALLOWED_ATTR: [
    'href',
    'title',
    'target',
    'rel',
    'class',
    'id',
    'name',
    'colspan',
    'rowspan',
    'headers',
    'scope',
    'align',
    'width',
    'height',
    'lang',
    'dir',
    'style'
  ],
  ALLOWED_URI_REGEXP: /^(?:(?:https?|mailto):|[^a-z]|[a-z+.-]+(?:[^a-z+.\-:]|$))/i
}

/** AI 气泡：Markdown → HTML 后再消毒；允许代码块复制按钮与图片等 Markdown 产物 */
const CHAT_MARKDOWN_CONFIG: Config = {
  ...CHAT_BUBBLE_CONFIG,
  ALLOWED_TAGS: [...(CHAT_BUBBLE_CONFIG.ALLOWED_TAGS as string[]), 'img', 'button'],
  ALLOWED_ATTR: [
    ...(CHAT_BUBBLE_CONFIG.ALLOWED_ATTR as string[]),
    'src',
    'alt',
    'type',
    'data-copy',
    'data-lang',
    'data-source',
    'data-tex',
    'aria-label',
    'role'
  ]
}

const SALES_CONTRACT_SANITIZE_CONFIG: Config = {
  ...CHAT_BUBBLE_CONFIG,
  ALLOWED_TAGS: [...(CHAT_BUBBLE_CONFIG.ALLOWED_TAGS as string[]), 'input', 'button'],
  ALLOWED_ATTR: [
    ...(CHAT_BUBBLE_CONFIG.ALLOWED_ATTR as string[]),
    'type',
    'value',
    'min',
    'max',
    'step',
    'disabled',
    'aria-hidden',
    'role',
    'data-row-id',
    'data-field',
    'data-index',
    'data-task-id'
  ]
}

function salesContractInteractiveAttrHook(
  currentNode: Element,
  hookEvent: UponSanitizeAttributeHookEvent,
  _config: Config
) {
  const name = String(hookEvent.attrName || '')
  if (!name.startsWith('on')) return
  const tag = currentNode.tagName
  const inPreview = currentNode.closest?.('.sales-contract-excel-preview')
  if (!inPreview) return
  const el = currentNode as HTMLElement
  if (tag === 'BUTTON' && name === 'onclick' && el.classList.contains('sales-contract-row-action-btn')) {
    hookEvent.forceKeepAttr = true
    return
  }
  if (tag === 'INPUT' && name === 'onchange') {
    if (
      el.classList.contains('sales-contract-excel-preview__model-input') ||
      el.classList.contains('sales-contract-excel-preview__qty-input')
    ) {
      hookEvent.forceKeepAttr = true
    }
  }
}

export function sanitizeChatBubbleHtml(raw: string | undefined | null): string {
  const dirty = String(raw ?? '')
  if (!dirty) return ''
  return DOMPurify.sanitize(dirty, CHAT_BUBBLE_CONFIG)
}

/** 助手回复：按 Markdown 渲染后再消毒（表格、列表、粗体等）。 */
export function sanitizeChatBubbleMarkdown(raw: string | undefined | null): string {
  const stripped = stripInternalMarkers(String(raw ?? ''))
  if (!stripped) return ''
  const html = renderMarkdown(stripped)
  return DOMPurify.sanitize(html, CHAT_MARKDOWN_CONFIG)
}

export type TaskSummarySanitizeInput = {
  type?: string
  summary?: string
}

export function sanitizeTaskSummaryHtml(task: TaskSummarySanitizeInput): string {
  const dirty = String(task.summary ?? '')
  if (!dirty) return ''
  const t = String(task.type || '')
  if (t === 'sales_contract' && dirty.includes('sales-contract-excel-preview')) {
    DOMPurify.addHook('uponSanitizeAttribute', salesContractInteractiveAttrHook)
    try {
      return DOMPurify.sanitize(dirty, SALES_CONTRACT_SANITIZE_CONFIG)
    } finally {
      DOMPurify.removeHook('uponSanitizeAttribute', salesContractInteractiveAttrHook)
    }
  }
  return DOMPurify.sanitize(dirty, CHAT_BUBBLE_CONFIG)
}
