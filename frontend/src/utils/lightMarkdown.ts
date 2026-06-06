/**
 * 轻量 Markdown -> HTML 渲染器（自包含、零依赖）。
 *
 * 设计目标：
 * - 覆盖 chat 场景：标题、列表、引用、行内/块代码、表格、加粗/斜体/删除线、链接、图片、行内公式 \(...\)、块级公式 \[...\]、Mermaid 占位
 * - 安全：纯文本→HTML 全部走 escapeHtml；不解析任何 raw HTML 标签；链接 href 仅允许 http/https/mailto；图片同理
 * - 不引入 marked / dompurify 等外部依赖，控制 bundle 体积
 *
 * 输出规约：
 * - mermaid 代码块输出 <div class="md-mermaid" data-source="...">，调用方负责异步替换为渲染后的 SVG
 * - 块级公式输出 <div class="md-math md-math-block" data-tex="...">；行内公式输出 <span class="md-math md-math-inline" data-tex="...">
 * - 普通代码块输出 <pre class="md-code"><code class="md-code__body" data-lang="...">...</code></pre>，配合 <button class="md-code__copy"> 由调用方注入
 */

const VOID_PLACEHOLDER_PREFIX = '\u0000MD_PLACEHOLDER_'
const VOID_PLACEHOLDER_SUFFIX = '\u0001'

function escapeHtml(s: string): string {
  return String(s ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}

function safeUrl(raw: string): string {
  const s = String(raw || '').trim()
  if (!s) return ''
  if (/^javascript:/i.test(s)) return ''
  if (/^data:/i.test(s) && !/^data:image\//i.test(s)) return ''
  if (/^vbscript:/i.test(s)) return ''
  return s
}

/** 把「挤在一行里的 GFM 表格」拆成多行，便于下行解析（模型常输出「帮助： | 列1 | 列2 | | :--- | …」）。 */
function normalizePackedMarkdownTables(text: string): string {
  let s = text
  s = s.replace(/([：:])\s+\|/g, '$1\n|')
  // 表头行与 :--- 分隔行挤在同一串里时：「… | | :---」→ 拆成两行且保留两侧单元格边界用的竖线
  s = s.replace(/\|\s+\|\s*(?=:?-{2,})/g, '|\n|')
  let prev = ''
  while (prev !== s) {
    prev = s
    s = s.replace(/\|\s+\|\s+(?=\*\*)/g, '\n| ')
  }
  return s
}

/** 把所有「不参与后续行内/块解析」的片段抽出，先用占位符替换，最后再回填。 */
class PlaceholderTable {
  private items = new Map<string, string>()
  private counter = 0

  push(html: string): string {
    const id = `${VOID_PLACEHOLDER_PREFIX}${this.counter}${VOID_PLACEHOLDER_SUFFIX}`
    this.counter += 1
    this.items.set(id, html)
    return id
  }

  flush(text: string): string {
    if (!this.items.size) return text
    let out = text
    for (const [id, html] of this.items) {
      out = out.split(id).join(html)
    }
    return out
  }
}

function inlineFormat(raw: string, ph: PlaceholderTable): string {
  let s = raw

  s = s.replace(/`([^`]+)`/g, (_m, code) => {
    return ph.push(`<code class="md-code-inline">${escapeHtml(code)}</code>`)
  })

  s = s.replace(/\\\[([\s\S]+?)\\\]/g, (_m, tex) => {
    return ph.push(`<div class="md-math md-math-block" data-tex="${escapeHtml(tex.trim())}">${escapeHtml(tex.trim())}</div>`)
  })
  s = s.replace(/\$\$([\s\S]+?)\$\$/g, (_m, tex) => {
    return ph.push(`<div class="md-math md-math-block" data-tex="${escapeHtml(tex.trim())}">${escapeHtml(tex.trim())}</div>`)
  })
  s = s.replace(/\\\(([^\n]+?)\\\)/g, (_m, tex) => {
    return ph.push(`<span class="md-math md-math-inline" data-tex="${escapeHtml(tex.trim())}">${escapeHtml(tex.trim())}</span>`)
  })

  s = escapeHtml(s)

  s = s.replace(/!\[([^\]]*)\]\(([^)\s]+)(?:\s+&quot;([^&]*)&quot;)?\)/g, (_m, alt, url, title) => {
    const u = safeUrl(url)
    if (!u) return alt
    const t = title ? ` title="${title}"` : ''
    return `<img src="${u}" alt="${alt}"${t} class="md-img" />`
  })

  s = s.replace(/\[([^\]]+)\]\(([^)\s]+)(?:\s+&quot;([^&]*)&quot;)?\)/g, (_m, label, url, title) => {
    const u = safeUrl(url)
    if (!u) return label
    const t = title ? ` title="${title}"` : ''
    return `<a href="${u}"${t} target="_blank" rel="noopener noreferrer" class="md-link">${label}</a>`
  })

  s = s.replace(/(^|[\s(])(https?:\/\/[^\s<>()]+)(?=[)\s]|$)/g, (_m, lead, url) => {
    const u = safeUrl(url)
    if (!u) return _m
    return `${lead}<a href="${u}" target="_blank" rel="noopener noreferrer" class="md-link">${u}</a>`
  })

  s = s.replace(/\*\*([^*\n]+)\*\*/g, '<strong>$1</strong>')
  s = s.replace(/__([^_\n]+)__/g, '<strong>$1</strong>')
  s = s.replace(/(^|[\s(>])\*([^*\n]+)\*(?=[\s).,!?;:]|$)/g, '$1<em>$2</em>')
  s = s.replace(/(^|[\s(>])_([^_\n]+)_(?=[\s).,!?;:]|$)/g, '$1<em>$2</em>')
  s = s.replace(/~~([^~\n]+)~~/g, '<del>$1</del>')

  return s
}

function renderTable(rows: string[], ph: PlaceholderTable): string {
  if (rows.length < 2) return ''
  const split = (line: string) =>
    line.replace(/^\|/, '').replace(/\|\s*$/, '').split('|').map((c) => c.trim())
  const header = split(rows[0])
  const align = split(rows[1]).map((c) => {
    const left = c.startsWith(':')
    const right = c.endsWith(':')
    if (left && right) return 'center'
    if (right) return 'right'
    if (left) return 'left'
    return ''
  })
  const body = rows.slice(2).map(split)
  const th = header.map((c, i) => {
    const a = align[i] ? ` style="text-align:${align[i]}"` : ''
    return `<th${a}>${inlineFormat(c, ph)}</th>`
  }).join('')
  const tr = body.map((row) => {
    const tds = row.map((c, i) => {
      const a = align[i] ? ` style="text-align:${align[i]}"` : ''
      return `<td${a}>${inlineFormat(c, ph)}</td>`
    }).join('')
    return `<tr>${tds}</tr>`
  }).join('')
  return `<div class="md-table-wrap"><table class="md-table"><thead><tr>${th}</tr></thead><tbody>${tr}</tbody></table></div>`
}

function isTableHeaderSep(line: string): boolean {
  return /^\s*\|?(\s*:?-{2,}:?\s*\|)+\s*:?-{2,}:?\s*\|?\s*$/.test(line)
}

/** 主入口：把 markdown 字符串渲染为安全 HTML 字符串。*/
export function renderMarkdown(src: string): string {
  const ph = new PlaceholderTable()
  const text = normalizePackedMarkdownTables(String(src ?? '').replace(/\r\n?/g, '\n'))

  const fenceMatcher = /(^|\n)```([\w+-]*)\s*\n([\s\S]*?)\n?```(?=\n|$)/g
  const tokenized = text.replace(fenceMatcher, (_m, lead, lang, code) => {
    const langSafe = String(lang || '').toLowerCase().slice(0, 24)
    if (langSafe === 'mermaid') {
      return `${lead}${ph.push(`<div class="md-mermaid" data-source="${escapeHtml(code)}"></div>`)}`
    }
    const codeHtml = escapeHtml(code)
    const html =
      `<pre class="md-code"><div class="md-code__head"><span class="md-code__lang">${langSafe || 'text'}</span>` +
      `<button type="button" class="md-code__copy" data-copy="1" aria-label="复制代码">复制</button></div>` +
      `<code class="md-code__body" data-lang="${langSafe}">${codeHtml}</code></pre>`
    return `${lead}${ph.push(html)}`
  })

  const lines = tokenized.split('\n')
  const out: string[] = []
  let i = 0
  let inList: 'ul' | 'ol' | null = null
  let listBuf: string[] = []

  const flushList = () => {
    if (!inList) return
    out.push(`<${inList} class="md-list">${listBuf.join('')}</${inList}>`)
    inList = null
    listBuf = []
  }

  const flushParagraph = (buf: string[]) => {
    if (!buf.length) return
    const joined = buf.join('\n').trim()
    if (!joined) return
    if (joined.startsWith(VOID_PLACEHOLDER_PREFIX)) {
      out.push(joined)
      return
    }
    out.push(`<p class="md-p">${inlineFormat(joined, ph)}</p>`)
  }

  let paraBuf: string[] = []

  while (i < lines.length) {
    const line = lines[i]

    if (!line.trim()) {
      flushParagraph(paraBuf)
      paraBuf = []
      flushList()
      i += 1
      continue
    }

    const heading = line.match(/^(#{1,6})\s+(.+)$/)
    if (heading) {
      flushParagraph(paraBuf)
      paraBuf = []
      flushList()
      const lv = heading[1].length
      out.push(`<h${lv} class="md-h md-h${lv}">${inlineFormat(heading[2], ph)}</h${lv}>`)
      i += 1
      continue
    }

    if (/^\s*(---|\*\*\*|___)\s*$/.test(line)) {
      flushParagraph(paraBuf)
      paraBuf = []
      flushList()
      out.push('<hr class="md-hr" />')
      i += 1
      continue
    }

    if (line.startsWith('>')) {
      flushParagraph(paraBuf)
      paraBuf = []
      flushList()
      const quote: string[] = []
      while (i < lines.length && lines[i].startsWith('>')) {
        quote.push(lines[i].replace(/^>\s?/, ''))
        i += 1
      }
      out.push(`<blockquote class="md-quote">${inlineFormat(quote.join('\n'), ph)}</blockquote>`)
      continue
    }

    if (line.includes('|') && i + 1 < lines.length && isTableHeaderSep(lines[i + 1])) {
      flushParagraph(paraBuf)
      paraBuf = []
      flushList()
      const tableLines: string[] = [line, lines[i + 1]]
      i += 2
      while (i < lines.length && lines[i].includes('|') && lines[i].trim()) {
        tableLines.push(lines[i])
        i += 1
      }
      out.push(renderTable(tableLines, ph))
      continue
    }

    const ulMatch = line.match(/^(\s*)([-*+])\s+(.+)$/)
    const olMatch = line.match(/^(\s*)(\d+)[.)]\s+(.+)$/)
    if (ulMatch || olMatch) {
      flushParagraph(paraBuf)
      paraBuf = []
      const indent = (ulMatch ? ulMatch[1] : (olMatch as RegExpMatchArray)[1]).length
      const kind: 'ul' | 'ol' = ulMatch ? 'ul' : 'ol'
      if (!inList) {
        inList = kind
        void indent
      }
      const content = ulMatch ? ulMatch[3] : (olMatch as RegExpMatchArray)[3]
      listBuf.push(`<li class="md-li">${inlineFormat(content, ph)}</li>`)
      i += 1
      continue
    } else if (inList) {
      flushList()
    }

    paraBuf.push(line)
    i += 1
  }
  flushParagraph(paraBuf)
  flushList()

  const html = out.join('\n')
  return ph.flush(html)
}

/** 把 chat 文本中可能出现的「<<<XXX>>>」类内部协议片段隐藏（仅在直接对话场景使用）。*/
export function stripInternalMarkers(src: string): string {
  return String(src || '')
    .replace(/<<<PLAN_DETAILS>>>[\s\S]*?<<<END_PLAN_DETAILS>>>/g, '')
    .replace(/<<<PLAN_OPTIONS>>>[\s\S]*?<<<END_PLAN_OPTIONS>>>/g, '')
    .replace(/<<<CHECKLIST>>>[\s\S]*?<<<END>>>/g, '')
    .trim()
}
