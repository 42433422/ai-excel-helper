const base = ''

async function req(path, opts = {}) {
  const r = await fetch(`${base}${path}`, {
    headers: { 'Content-Type': 'application/json', ...opts.headers },
    ...opts,
  })
  const text = await r.text()
  let data = null
  try {
    data = text ? JSON.parse(text) : null
  } catch {
    data = { detail: text || r.statusText }
  }
  if (!r.ok) {
    const d = data?.detail
    let msg
    if (Array.isArray(d)) {
      msg = d.map((x) => x.msg || JSON.stringify(x)).join('; ')
    } else if (typeof d === 'string') {
      msg = d
    } else if (d && typeof d === 'object') {
      msg = JSON.stringify(d)
    } else {
      msg = r.statusText
    }
    throw new Error(msg)
  }
  return data
}

export const api = {
  health: () => req('/api/health'),
  getConfig: () => req('/api/config'),
  putConfig: (body) =>
    req('/api/config', { method: 'PUT', body: JSON.stringify(body) }),
  listMods: () => req('/api/mods'),
  getMod: (id) => req(`/api/mods/${encodeURIComponent(id)}`),
  putManifest: (id, manifest) =>
    req(`/api/mods/${encodeURIComponent(id)}/manifest`, {
      method: 'PUT',
      body: JSON.stringify({ manifest }),
    }),
  createMod: (mod_id, display_name) =>
    req('/api/mods/create', {
      method: 'POST',
      body: JSON.stringify({ mod_id, display_name }),
    }),
  deleteMod: (id) =>
    req(`/api/mods/${encodeURIComponent(id)}`, { method: 'DELETE' }),
  importZip: async (file, replace = true) => {
    const fd = new FormData()
    fd.append('file', file)
    const r = await fetch(`${base}/api/mods/import?replace=${replace}`, {
      method: 'POST',
      body: fd,
    })
    const data = await r.json().catch(() => ({}))
    if (!r.ok) throw new Error(data.detail || r.statusText)
    return data
  },
  push: (mod_ids) =>
    req('/api/sync/push', {
      method: 'POST',
      body: JSON.stringify({ mod_ids: mod_ids || null }),
    }),
  pull: (mod_ids) =>
    req('/api/sync/pull', {
      method: 'POST',
      body: JSON.stringify({ mod_ids: mod_ids || null }),
    }),
  exportUrl: (id) => `${base}/api/mods/${encodeURIComponent(id)}/export`,
}
