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
    port: 5173,
    proxy: {
      // 兼容拆分后端：5000 提供出货/AI助手兼容，5001 提供材料/基础数据。
      // 规则：尽量使用“更具体的前缀 -> 对应端口”，最后用 '/api' 兜底到 5001。

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
      // 否则会落入兜底 '/api' -> 5001，导致前端看到 500
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

      // 兜底：其余所有 /api 都发给材料/基础数据服务（5001）
      '/api': {
        target: 'http://127.0.0.1:5001',
        changeOrigin: true,
        ws: true,
      },
    }
  },
  publicDir: 'public',
  build: {
    outDir: '../templates/vue-dist',
    assetsDir: 'assets',
    emptyOutDir: true,
    rollupOptions: {
      output: {
        manualChunks: {
          'vendor-vue': ['vue'],
          'vendor-stores': [
            './src/stores/proMode.js',
            './src/stores/jarvisChat.js',
            './src/stores/productQuery.js',
            './src/stores/workMode.js'
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
