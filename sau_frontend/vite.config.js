import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

const LOOPBACK_HOSTS = new Set(['127.0.0.1', 'localhost', '[::1]'])

export function resolveWebRuntimeConfig(environment) {
  const frontendPort = Number(environment.VITE_PORT || 5173)
  if (!Number.isInteger(frontendPort) || frontendPort < 1 || frontendPort > 65535) {
    throw new Error('VITE_PORT must be an integer port between 1 and 65535')
  }

  const proxyUrl = new URL(
    environment.VITE_API_PROXY_TARGET || 'http://127.0.0.1:5409',
  )
  if (
    proxyUrl.protocol !== 'http:'
    || !LOOPBACK_HOSTS.has(proxyUrl.hostname.toLowerCase())
    || proxyUrl.username
    || proxyUrl.password
    || proxyUrl.pathname !== '/'
    || proxyUrl.search
    || proxyUrl.hash
  ) {
    throw new Error('VITE_API_PROXY_TARGET must be an origin-only HTTP loopback URL')
  }

  return {
    frontendPort,
    openBrowser: environment.VITE_OPEN_BROWSER === 'true',
    proxyTarget: proxyUrl.origin,
  }
}

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const environment = {
    ...loadEnv(mode, process.cwd(), ''),
    ...process.env,
  }
  const runtime = resolveWebRuntimeConfig(environment)

  return {
    plugins: [vue()],
    resolve: {
      alias: {
        '@': resolve(__dirname, 'src'),
      },
    },
    css: {
      preprocessorOptions: {
        scss: {
          // 移除自动导入，改用@use语法
        }
      }
    },
    server: {
      host: '127.0.0.1',
      port: runtime.frontendPort,
      open: runtime.openBrowser,
      proxy: {
        '/api': {
          target: runtime.proxyTarget,
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/api/, '')
        }
      }
    },
    build: {
      outDir: 'dist',
      sourcemap: false,
      chunkSizeWarningLimit: 1600,
      rollupOptions: {
        output: {
          manualChunks: {
            vue: ['vue', 'vue-router', 'pinia'],
            elementPlus: ['element-plus'],
            utils: ['axios']
          }
        }
      }
    }
  }
})
