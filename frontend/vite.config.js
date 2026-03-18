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
      '/api': {
        target: 'http://127.0.0.1:5000',
        changeOrigin: true,
        ws: true
      }
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
          'vendor-pro-mode': [
            './src/composables/useProMode.js',
            './src/composables/useJarvisChat.js',
            './src/composables/useProductQuery.js',
            './src/composables/useWorkMode.js',
            './src/composables/useAnimations.js',
            './src/composables/useDigitalRain.js'
          ],
          'vendor-utils': [
            './src/utils/animation-helpers.js',
            './src/utils/geometry.js',
            './src/utils/particle-system.js'
          ],
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
    minify: 'terser',
    terserOptions: {
      compress: {
        drop_console: true,
        drop_debugger: true
      }
    },
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
