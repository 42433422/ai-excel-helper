import fs from 'node:fs'

const p = new URL('../frontend/src/tutorial/tracks/basic.ts', import.meta.url)
let s = fs.readFileSync(p, 'utf8')

function trimText(t) {
  const one = t.replace(/\s+/g, ' ').trim()
  const first = one.split(/[。；]/)[0] || one
  return first.length > 38 ? `${first.slice(0, 38)}…` : first
}

s = s.replace(/description:\s*`([^`]+)`/g, (_, body) => `description: \`${trimText(body)}\``)
s = s.replace(/description:\s*\n\s*'([^']+)'/g, (_, body) => `description: '${trimText(body)}'`)
s = s.replace(/description:\s*\n\s*"([^"]+)"/g, (_, body) => `description: "${trimText(body)}"`)

fs.writeFileSync(p, s)
console.log('trimmed basic.ts')
