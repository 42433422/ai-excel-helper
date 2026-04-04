import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
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

export default defineConfig({
  plugins: [vue(), copyStaticPlugin()],
  base: '/',
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src')
    }
  },
  server: {
    // 与 run.py（5000）配合：/api 走下方代理。勿与 run_warehouse.py（默认 5002）混用同一端口。
    port: 5001,
    proxy: {
      // 开发时统一把业务 API 代理到完整后端 run.py（5000）。材料拆分进程见 run_warehouse.py（默认 5002），勿占用 5001（Vite）。
      // 规则：尽量使用“更具体的前缀 -> 5000”，最后用 '/api' 兜底到 5000。

      // compat：/orders/*（不带 /api 前缀）
      '/orders': {
        target: 'http://127.0.0.1:5000',
        changeOrigin: true,
      },

      // compat：/health
      '/health': {
        target: 'http://127.0.0.1:5000',
        changeOrigin: true,
      },

      // 出货/打印/AI/chat/以及 compat 中的相关接口都走 5000
      '/api/shipment': {
        target: 'http://127.0.0.1:5000',
        changeOrigin: true,
      },
      '/api/ai': {
        target: 'http://127.0.0.1:5000',
        changeOrigin: true,
      },
      '/api/print': {
        target: 'http://127.0.0.1:5000',
        changeOrigin: true,
      },
      '/api/generate': {
        target: 'http://127.0.0.1:5000',
        changeOrigin: true,
      },
      '/api/orders': {
        target: 'http://127.0.0.1:5000',
        changeOrigin: true,
      },
      '/api/shipment-records': {
        target: 'http://127.0.0.1:5000',
        changeOrigin: true,
      },
      '/api/purchase_units': {
        target: 'http://127.0.0.1:5000',
        changeOrigin: true,
      },
      '/api/product_names': {
        target: 'http://127.0.0.1:5000',
        changeOrigin: true,
      },
      '/api/printers': {
        target: 'http://127.0.0.1:5000',
        changeOrigin: true,
      },
      '/api/tts': {
        target: 'http://127.0.0.1:5000',
        changeOrigin: true,
      },

      // 兼容：基础数据/聊天/联系人等也应转发到 5000
      // 否则会落入兜底 '/api'，若 5000 未启动则代理失败（终端见 [vite-proxy] 日志）
      '/api/conversations': {
        target: 'http://127.0.0.1:5000',
        changeOrigin: true,
      },
      '/api/wechat_contacts': {
        target: 'http://127.0.0.1:5000',
        changeOrigin: true,
      },
      '/api/products': {
        target: 'http://127.0.0.1:5000',
        changeOrigin: true,
      },
      '/api/materials': {
        target: 'http://127.0.0.1:5000',
        changeOrigin: true,
      },
      '/api/system': {
        target: 'http://127.0.0.1:5000',
        changeOrigin: true,
      },
      '/api/intent-packages': {
        target: 'http://127.0.0.1:5000',
        changeOrigin: true,
      },
      '/api/tools': {
        target: 'http://127.0.0.1:5000',
        changeOrigin: true,
      },
      '/api/wechat': {
        target: 'http://127.0.0.1:5000',
        changeOrigin: true,
      },
      '/api/db-tools': {
        target: 'http://127.0.0.1:5000',
        changeOrigin: true,
      },
      // 奇士美 PRO Mod（含 /api/mod/sz-qsm-pro/phone-agent/*）；代理层失败时返回 JSON 502，避免与后端 500 混淆
      '/api/mod': {
        target: 'http://127.0.0.1:5000',
        changeOrigin: true,
        configure: (proxy) => {
          proxy.on('error', (err, _req, res) => {
            console.error(
              '[vite-proxy] /api/mod -> http://127.0.0.1:5000 failed:',
              err && err.message ? err.message : err
            )
            if (res && !res.headersSent && typeof res.writeHead === 'function') {
              res.writeHead(502, { 'Content-Type': 'application/json; charset=utf-8' })
              res.end(
                JSON.stringify({
                  success: false,
                  error:
                    '无法连接后端 127.0.0.1:5000。请先在本机启动：python run.py（工作目录 XCAGI）。',
                })
              )
            }
          })
        },
      },

      // Mod 系统（显式规则，避免个别环境下 /api 兜底未命中或错误码不直观）
      '/api/mods': {
        target: 'http://127.0.0.1:5000',
        changeOrigin: true,
        configure: (proxy) => {
          proxy.on('error', (err, _req, res) => {
            console.error(
              '[vite-proxy] /api/mods -> http://127.0.0.1:5000 failed:',
              err && err.message ? err.message : err
            )
            if (res && !res.headersSent && typeof res.writeHead === 'function') {
              res.writeHead(502, { 'Content-Type': 'application/json; charset=utf-8' })
              res.end(
                JSON.stringify({
                  success: false,
                  error:
                    '无法连接后端 127.0.0.1:5000。请先在本机启动：python run.py（工作目录 XCAGI）。',
                })
              )
            }
          })
        },
      },

      // 兜底：其余所有 /api 都发给后端服务（5000）。若浏览器大量 500/502，先确认已执行：python run.py
      '/api': {
        target: 'http://127.0.0.1:5000',
        changeOrigin: true,
        ws: true,
        configure: (proxy) => {
          proxy.on('error', (err, _req, res) => {
            console.error(
              '[vite-proxy] /api -> http://127.0.0.1:5000 failed:',
              err && err.message ? err.message : err
            )
            if (res && !res.headersSent && typeof res.writeHead === 'function') {
              res.writeHead(502, { 'Content-Type': 'application/json; charset=utf-8' })
              res.end(
                JSON.stringify({
                  success: false,
                  error:
                    '无法连接后端 127.0.0.1:5000。请先在本机启动：python run.py（或确保 Flask 监听 5000）。'
                })
              )
            }
          })
        }
      },
    }
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
        manualChunks: {
          'vendor-vue': ['vue'],
          'vendor-stores': [
            './src/stores/proMode.ts',
            './src/stores/jarvisChat.ts',
            './src/stores/productQuery.ts',
            './src/stores/workMode.ts'
          ]
        },
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
      }
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
})
