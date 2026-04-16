const base = ''

async function req(path, opts = {}) {
  const method = String(opts.method || 'GET').toUpperCase()
  const headers = { ...(opts.headers || {}) }
  const body = opts.body
  if (!(body instanceof FormData) && method !== 'GET' && method !== 'HEAD' && body !== undefined) {
    if (!headers['Content-Type'] && !headers['content-type']) {
      headers['Content-Type'] = 'application/json'
    }
  }
  const r = await fetch(`${base}${path}`, {
    ...opts,
    method,
    headers,
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
  getModFile: (id, filePath) =>
    req(`/api/mods/${encodeURIComponent(id)}/file?path=${encodeURIComponent(filePath)}`),
  putModFile: (id, filePath, content) =>
    req(`/api/mods/${encodeURIComponent(id)}/file`, {
      method: 'PUT',
      body: JSON.stringify({ path: filePath, content }),
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
  debugSandbox: (mod_id, mode = 'copy') =>
    req('/api/debug/sandbox', {
      method: 'POST',
      body: JSON.stringify({ mod_id, mode }),
    }),
  debugFocusPrimary: (mod_id) =>
    req('/api/debug/focus-primary', {
      method: 'POST',
      body: JSON.stringify({ mod_id }),
    }),
  xcagiLoadingStatus: () => req('/api/xcagi/loading-status'),
  /** 扫描 XCAGI/mods 目录（与 push 目标一致） */
  xcagiInstalledMods: () => req('/api/xcagi/installed-mods'),
  /** 代理 FHD：宿主是否已配置 FHD_DB_READ_TOKEN / FHD_DB_WRITE_TOKEN（无明文） */
  fhdDbTokensStatus: () => req('/api/fhd/db-tokens/status'),
  exportFhdShellMods: (outputPath = '') =>
    req('/api/export/fhd-shell-mods', {
      method: 'POST',
      body: JSON.stringify({ output_path: outputPath }),
    }),
  extensionSurface: (mergeHost = false) =>
    req(`/api/authoring/extension-surface?merge_host=${mergeHost ? '1' : '0'}`),
  modBlueprintRoutes: (id) => req(`/api/mods/${encodeURIComponent(id)}/blueprint-routes`),
  modAuthoringSummary: (id) => req(`/api/mods/${encodeURIComponent(id)}/authoring-summary`),
}
