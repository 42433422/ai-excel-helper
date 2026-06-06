import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import AutoImport from 'unplugin-auto-import/vite'
import Components from 'unplugin-vue-components/vite'
import { ElementPlusResolver } from 'unplugin-vue-components/resolvers'
import path from 'path'
import fs from 'fs'

const copyStaticPlugin = () => ({
  name: 'copy-static',
  closeBundle() {
    const srcDir = path.resolve(__dirname, '../AI助手/static')
    const destDir = path.resolve(__dirname, 'public/static')

    if (fs.existsSync(srcDir)) {
      copyDir(srcDir, destDir)
      console.log('Static files copied successfully!')
    }
  }
})

/** FHD/mods 优先；缺失时回退到 FHD/XCAGI/mods（避免 generic build 因 bridge 未同步到 mods/ 失败）。 */
function modViewsDir(modId) {
  const rel = path.join(modId, 'frontend', 'views')
  const candidates = [
    path.resolve(__dirname, '../mods', rel),
    path.resolve(__dirname, '../XCAGI/mods', rel),
  ]
  for (const p of candidates) {
    if (fs.existsSync(p)) return p
  }
  return candidates[0]
}

function copyDir(src, dest) {
  if (!fs.existsSync(dest)) {
    fs.mkdirSync(dest, { recursive: true })
  }

  const entries = fs.readdirSync(src, { withFileTypes: true })

  for (const entry of entries) {
    const srcPath = path.join(src, entry.name)
    const destPath = path.join(dest, entry.name)

    if (entry.isDirectory()) {
      copyDir(srcPath, destPath)
    } else {
      fs.copyFileSync(srcPath, destPath)
    }
  }
}

// 读取环境变量中的后端地址（支持局域网）
// .env.local 里加一行: VITE_API_BASE=http://192.168.x.x:5000
const API_BASE = process.env.VITE_API_BASE || 'http://127.0.0.1:5000'

/** 手机访问局域网 IP 时，HMR WebSocket 不能仍指向 localhost；由 start-lan.ps1 注入本机私网 IP。 */
const devHmrHost = (process.env.VITE_DEV_HMR_HOST || '').trim()

/**
 * 上游返回绝对 ``Location``（指向代理目标）时，浏览器会跟链离开 Vite 同源并触发 CORS。
 * 改为相对路径，使后续请求仍走 ``:5001`` → 代理。
 * 兼容：完整 URL 同源、``//host/path``、以及与 ``upstreamBase`` 字符串前缀一致。
 */
function rewriteUpstreamRedirectToRelative(proxy, upstreamBase) {
  const prefix = String(upstreamBase || '').trim().replace(/\/$/, '')
  let upstreamOrigin = ''
  try {
    if (prefix) upstreamOrigin = new URL(prefix.includes('://') ? prefix : `http://${prefix}`).origin
  } catch {
    upstreamOrigin = ''
  }
  proxy.on('proxyRes', (proxyRes) => {
    const code = Number(proxyRes.statusCode || 0)
    if (code < 300 || code >= 400) return
    let loc = proxyRes.headers.location
    if (!loc || typeof loc !== 'string') return
    loc = loc.trim()
    // 协议相对 URL
    if (loc.startsWith('//')) {
      const scheme = upstreamOrigin.startsWith('https') ? 'https:' : 'http:'
      loc = scheme + loc
    }
    try {
      if (upstreamOrigin) {
        const u = new URL(loc, upstreamOrigin)
        if (u.origin === upstreamOrigin) {
          proxyRes.headers.location = u.pathname + u.search + u.hash
          return
        }
      }
    } catch {
      /* fall through */
    }
    if (prefix && loc.startsWith(prefix)) {
      const rest = loc.slice(prefix.length)
      const path = rest && rest.startsWith('/') ? rest : `/${rest || ''}`
      proxyRes.headers.location = path
    }
  })
}

/** 代理无法连上 FastAPI 时在终端给出可操作提示（常见：ETIMEDOUT / ECONNREFUSED）。 */
function logViteProxyConnectFailure(routeLabel, apiBase, err) {
  const msg = err && err.message ? String(err.message) : String(err)
  console.error(`[vite-proxy] ${routeLabel} -> ${apiBase} failed: ${msg}`)
  if (/ETIMEDOUT|ECONNREFUSED|ENOTFOUND|EAI_AGAIN/i.test(msg)) {
    console.error(
      '  → 无法连接代理目标。请检查：① 云主机安全组/系统防火墙是否放行该端口 ② 后端是否监听 0.0.0.0（勿只绑 127.0.0.1）' +
        ' ③ 本机到该 IP 的网络是否可达。本地开发可将 frontend/.env.local 设为 VITE_API_BASE=http://127.0.0.1:5000 后重启 dev。'
    )
  }
}

function proxyUpstreamErrorPayload(apiBase, err) {
  const msg = err && err.message ? String(err.message) : ''
  const head = '无法连接后端 ' + apiBase + '。'
  if (/ETIMEDOUT/i.test(msg)) {
    return (
      head +
      '（连接超时：核对 VITE_API_BASE、安全组与后端监听地址；本机后端常用 http://127.0.0.1:5000）'
    )
  }
  if (/ECONNREFUSED/i.test(msg)) {
    return head + '（连接被拒绝：该端口无服务或仅监听本机回环）'
  }
  if (/ENOTFOUND|EAI_AGAIN/i.test(msg)) {
    return head + '（域名/IP 解析失败或网络不可用）'
  }
  return head + '请先启动后端（仓库根 python run.py，默认端口见控制台）。'
}

/**
 * 开发服务器与 ``vite preview`` 共用：把 ``/api`` 转到 FastAPI（默认 :5000）。
 * preview 默认不带 proxy，局域网用 ``http://<ip>:5001`` 预览构建产物时会整页 404。
 */
function buildDevProxy(apiBase) {
  return {
        // 开发时统一把业务 API 代理到完整后端 run.py（5000）。材料拆分进程见 run_warehouse.py（默认 5002），勿占用 5001（Vite）。
        // 规则：尽量使用"更具体的前缀 -> 5000"，最后用 '/api' 兜底到 5000。

        // compat：/orders/*（不带 /api 前缀）。注意 Vue 路由也有页面 /orders，浏览器刷新须走 SPA。
        '/orders': {
          target: apiBase,
          changeOrigin: true,
          bypass(req) {
            const accept = req.headers.accept || ''
            if (req.method === 'GET' && accept.includes('text/html')) {
              return '/index.html'
            }
          },
        },

        // compat：/health
        '/health': {
          target: apiBase,
          changeOrigin: true,
        },

        // 出货/打印/AI/chat/以及 compat 中的相关接口都走 5000
        '/api/shipment': {
          target: apiBase,
          changeOrigin: true,
        },
        // Planner SSE：默认代理超时过短可能中断长连接
        '/api/ai': {
          target: apiBase,
          changeOrigin: true,
          timeout: 0,
          proxyTimeout: 0,
        },
        '/api/print': {
          target: apiBase,
          changeOrigin: true,
        },
        '/api/generate': {
          target: apiBase,
          changeOrigin: true,
        },
        '/api/orders': {
          target: apiBase,
          changeOrigin: true,
        },
        '/api/shipment-records': {
          target: apiBase,
          changeOrigin: true,
        },
        '/api/purchase_units': {
          target: apiBase,
          changeOrigin: true,
        },
        '/api/product_names': {
          target: apiBase,
          changeOrigin: true,
        },
        '/api/printers': {
          target: apiBase,
          changeOrigin: true,
        },
        '/api/sales-contract': {
          target: apiBase,
          changeOrigin: true,
        },
        '/api/price-list': {
          target: apiBase,
          changeOrigin: true,
        },
        '/api/tts': {
          target: apiBase,
          changeOrigin: true,
        },
        // FHD 风格上传（对话 @ Excel 等）：须由 FastAPI 5000 提供
        '/api/upload': {
          target: apiBase,
          changeOrigin: true,
          timeout: 120000,
          proxyTimeout: 120000,
        },

        // 兼容：基础数据/聊天/联系人等也应转发到 5000
        // 否则会落入兜底 '/api'，若 5000 未启动则代理失败（终端见 [vite-proxy] 日志）
        '/api/conversations': {
          target: apiBase,
          changeOrigin: true,
        },
        '/api/wechat_contacts': {
          target: apiBase,
          changeOrigin: true,
          timeout: 0,
          proxyTimeout: 0,
        },
        '/api/products': {
          target: apiBase,
          changeOrigin: true,
        },
        '/api/materials': {
          target: apiBase,
          changeOrigin: true,
        },
        '/api/system': {
          target: apiBase,
          changeOrigin: true,
        },
        '/api/state': {
          target: apiBase,
          changeOrigin: true,
        },
        '/api/market': {
          target: apiBase,
          changeOrigin: true,
        },
        '/api/intent-packages': {
          target: apiBase,
          changeOrigin: true,
        },
        '/api/tools': {
          target: apiBase,
          changeOrigin: true,
        },
        '/api/wechat': {
          target: apiBase,
          changeOrigin: true,
        },
        '/api/db-tools': {
          target: apiBase,
          changeOrigin: true,
        },
        '/api/templates': {
          target: apiBase,
          changeOrigin: true,
          timeout: 0,
          proxyTimeout: 0,
        },
        // 传统模式 watch 为长连接流式响应；默认超时过短易出现 504
        '/api/traditional-mode': {
          target: apiBase,
          changeOrigin: true,
          timeout: 0,
          proxyTimeout: 0,
        },
        // XCmax 同步 SSE 流（/api/xcmax/sync/stream）；长连接须禁用代理超时
        '/api/xcmax': {
          target: apiBase,
          changeOrigin: true,
          timeout: 0,
          proxyTimeout: 0,
          configure: (proxy) => {
            proxy.on('proxyRes', (proxyRes, _req, res) => {
              if (proxyRes.headers['content-type']?.includes('text/event-stream')) {
                proxyRes.headers['cache-control'] = 'no-cache'
                proxyRes.headers['connection'] = 'keep-alive'
                if (!res.headersSent) res.flushHeaders()
              }
            })
            proxy.on('error', (err, _req, res) => {
              logViteProxyConnectFailure('/api/xcmax', apiBase, err)
              if (res && !res.headersSent && typeof res.writeHead === 'function') {
                res.writeHead(502, { 'Content-Type': 'application/json; charset=utf-8' })
                res.end(
                  JSON.stringify({
                    success: false,
                    error: proxyUpstreamErrorPayload(apiBase, err),
                  })
                )
              }
            })
          },
        },
        // 奇士美 PRO Mod（含 /api/mod/sz-qsm-pro/phone-agent/*）；代理层失败时返回 JSON 502，避免与后端 500 混淆
        '/api/mod': {
          target: apiBase,
          changeOrigin: true,
          configure: (proxy) => {
            rewriteUpstreamRedirectToRelative(proxy, apiBase)
            proxy.on('error', (err, _req, res) => {
              logViteProxyConnectFailure('/api/mod', apiBase, err)
              if (res && !res.headersSent && typeof res.writeHead === 'function') {
                res.writeHead(502, { 'Content-Type': 'application/json; charset=utf-8' })
                res.end(
                  JSON.stringify({
                    success: false,
                    error: proxyUpstreamErrorPayload(apiBase, err),
                  })
                )
              }
            })
          },
        },

        // Mod 系统（显式规则，避免个别环境下 /api 兜底未命中或错误码不直观）
        '/api/mods': {
          target: apiBase,
          changeOrigin: true,
          timeout: 0,
          proxyTimeout: 0,
          configure: (proxy) => {
            rewriteUpstreamRedirectToRelative(proxy, apiBase)
            proxy.on('error', (err, _req, res) => {
              logViteProxyConnectFailure('/api/mods', apiBase, err)
              if (res && !res.headersSent && typeof res.writeHead === 'function') {
                res.writeHead(502, { 'Content-Type': 'application/json; charset=utf-8' })
                res.end(
                  JSON.stringify({
                    success: false,
                    error: proxyUpstreamErrorPayload(apiBase, err),
                  })
                )
              }
            })
          },
        },

        // 兜底：其余所有 /api 都发给后端服务（5000）。若浏览器大量 500/502，先确认已执行：python run.py
        '/api': {
          target: apiBase,
          changeOrigin: true,
          ws: true,
          configure: (proxy) => {
            rewriteUpstreamRedirectToRelative(proxy, apiBase)
            // 把真实客户端 IP 透传给后端，让 LAN Guard 能拿到正确的来源地址
            proxy.on('proxyReq', (proxyReq, req) => {
              const clientIp = req.socket?.remoteAddress || req.headers['x-forwarded-for'] || ''
              const normalizedIp = clientIp.replace(/^::ffff:/, '')
              if (normalizedIp) {
              proxyReq.setHeader('X-Forwarded-For', normalizedIp)
              proxyReq.setHeader('X-Real-IP', normalizedIp)
              }
            })
            proxy.on('error', (err, _req, res) => {
              logViteProxyConnectFailure('/api', apiBase, err)
              if (res && !res.headersSent && typeof res.writeHead === 'function') {
                res.writeHead(502, { 'Content-Type': 'application/json; charset=utf-8' })
                res.end(
                  JSON.stringify({
                    success: false,
                    error: proxyUpstreamErrorPayload(apiBase, err),
                  })
                )
              }
            })
          }
        },
  }
}

export default defineConfig(({ mode }) => {
  // 加载环境变量
  const env = loadEnv(mode, process.cwd(), 'VITE_')
  const apiBase = env.VITE_API_BASE || API_BASE
  const publicBase = env.VITE_PUBLIC_BASE || '/'
  const isDev = mode === 'development'
  const xcmaxPublicApiPrefix = String(env.VITE_XCMAX_PUBLIC_API_PREFIX || '').trim()

  let devPort = 5001
  const rawDevPort = String(env.VITE_DEV_PORT || '').trim()
  if (rawDevPort) {
    const p = Number.parseInt(rawDevPort, 10)
    if (Number.isFinite(p) && p > 0) devPort = p
  }

  const hmr =
    isDev && devHmrHost && devHmrHost !== '127.0.0.1'
      ? {
          overlay: false,
          host: devHmrHost,
          port: devPort,
          clientPort: devPort,
        }
      : { overlay: false }

  const editionSuffix =
    mode === 'minimal' ? 'minimal' : mode === 'generic' ? 'generic' : 'full'
  const constantsDir = path.resolve(__dirname, './src/constants')

  return {
    plugins: [
      vue(),
      AutoImport({
        resolvers: [ElementPlusResolver()],
        dts: false,
      }),
      Components({
        resolvers: [ElementPlusResolver({ importStyle: 'css' })],
        dts: false,
      }),
      copyStaticPlugin(),
      {
        name: 'inject-xcmax-api-base',
        transformIndexHtml(html) {
          if (!xcmaxPublicApiPrefix) return html
          const escaped = JSON.stringify(xcmaxPublicApiPrefix)
          const tag = `<script>window.__XCMAX_API_BASE__=${escaped}</script>`
          if (html.includes('__XCMAX_API_BASE__')) return html
          return html.replace('<head>', `<head>\n    ${tag}`)
        },
      },
    ],
    base: publicBase,
    resolve: {
      alias: [
        {
          find: '@/constants/hostViewGlob',
          replacement: path.join(constantsDir, `hostViewGlob.${editionSuffix}.ts`),
        },
        {
          find: '@/constants/modPhysicalViewGlob',
          replacement: path.join(constantsDir, `modPhysicalViewGlob.${editionSuffix}.ts`),
        },
        {
          find: '@/constants/modRouteGlob',
          replacement: path.join(constantsDir, `modRouteGlob.${editionSuffix}.ts`),
        },
        { find: '@', replacement: path.resolve(__dirname, './src') },
        {
          find: '@mod-views/xcagi-lan-license-bridge',
          replacement: modViewsDir('xcagi-lan-license-bridge'),
        },
        {
          find: '@mod-views/xcagi-customer-service-bridge',
          replacement: modViewsDir('xcagi-customer-service-bridge'),
        },
        {
          find: '@mod-views/xcagi-approval-bridge',
          replacement: modViewsDir('xcagi-approval-bridge'),
        },
        {
          find: '@mod-views/xcagi-planner-bridge',
          replacement: modViewsDir('xcagi-planner-bridge'),
        },
        {
          find: '@mod-views/xcagi-model-payment-bridge',
          replacement: modViewsDir('xcagi-model-payment-bridge'),
        },
        {
          find: '@mod-views/xcagi-erp-domain-bridge',
          replacement: modViewsDir('xcagi-erp-domain-bridge'),
        },
        {
          find: '@mod-views/xcagi-office-employee-pack-bridge',
          replacement: modViewsDir('xcagi-office-employee-pack-bridge'),
        },
        {
          find: '@mod-views/xcagi-workflow-visualization-bridge',
          replacement: modViewsDir('xcagi-workflow-visualization-bridge'),
        },
        {
          find: '@mod-views/xcagi-core-workflow-employees',
          replacement: modViewsDir('xcagi-workflow-visualization-bridge'),
        },
        { find: 'vue-router', replacement: path.resolve(__dirname, 'node_modules/vue-router') },
        { find: 'pinia', replacement: path.resolve(__dirname, 'node_modules/pinia') },
        { find: 'element-plus', replacement: path.resolve(__dirname, 'node_modules/element-plus') },
        { find: 'xlsx', replacement: path.resolve(__dirname, 'node_modules/xlsx') },
      ],
      dedupe: ['vue', 'vue-router', 'pinia', 'element-plus', 'xlsx'],
    },
    server: {
      // 0.0.0.0：明确监听 IPv4 全接口，避免个别环境下 host:true 局域网设备连不上 :5001
      host: isDev ? '0.0.0.0' : true,
      // 与 XCAGI/run.py（默认 5000）配合：/api 走下方代理。第二套本地实例见仓库根 .env.example「个人实例」。
      port: devPort,
      // 避免部分环境下以「主机名 / IP」访问时被 Vite 拒绝（局域网联调）
      ...(isDev ? { allowedHosts: true } : {}),
      hmr,
      proxy: buildDevProxy(apiBase),
      fs: {
        allow: ['..'],
      },
    },

    preview: {
      host: '0.0.0.0',
      port: devPort,
      strictPort: false,
      proxy: buildDevProxy(apiBase),
    },
    publicDir: 'public',
    worker: {
      format: 'es'
    },
    build: {
      outDir: '../templates/vue-dist',
      assetsDir: 'assets',
      emptyOutDir: true,
      rollupOptions: {
        output: {
          // 生产包勿 manualChunks：与业务 store/router 循环依赖会导致桌面白屏（Ed/gr before initialization）
          chunkFileNames: 'assets/js/[name]-[hash].js',
          entryFileNames: 'assets/js/[name]-[hash].js',
          assetFileNames: (assetInfo) => {
            const info = assetInfo.name.split('.')
            const ext = info[info.length - 1]
            if (/\.(css)$/.test(assetInfo.name)) {
              return 'assets/css/[name]-[hash][extname]'
            }
            if (/\.(woff2?|eot|ttf|otf)$/.test(assetInfo.name)) {
              return 'assets/fonts/[name]-[hash][extname]'
            }
            return 'assets/[name]-[hash][extname]'
          }
        },
        onwarn(warning, warn) {
          if (warning.message && warning.message.includes('dynamic import will not move module into another chunk')) {
            return
          }
          warn(warning)
        },
      },
      // 使用 Vite 默认的 esbuild 压缩，避免对 terser 额外依赖
      minify: 'esbuild',
      sourcemap: false,
      cssCodeSplit: true,
      target: 'es2015',
      reportCompressedSize: true
    },
    optimizeDeps: {
      include: ['vue'],
      exclude: []
    },
    css: {
      devSourcemap: true
    }
  }
})
