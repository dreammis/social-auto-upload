import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
// import vueDevTools from 'vite-plugin-vue-devtools'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    vue(),
    // vueDevTools(),
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
      '@assets': fileURLToPath(new URL('./src/assets', import.meta.url)),
    },
  },
  optimizeDeps: {
    exclude: ['fsevents'],
  },
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:5409',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
        // configure: (proxy, options) => {
        //   proxy.on('proxyReq', (proxyReq, req, res) => {
        //     // 支持SSE连接
        //     if (req.url && req.url.includes('/login')) {
        //       proxyReq.setHeader('Accept', 'text/event-stream');
        //       proxyReq.setHeader('Cache-Control', 'no-cache');
        //       proxyReq.setHeader('Connection', 'keep-alive');
        //     }
        //   });
        //   proxy.on('proxyRes', (proxyRes, req, res) => {
        //     // 确保SSE响应头正确设置
        //     if (req.url && req.url.includes('/login')) {
        //       proxyRes.headers['content-type'] = 'text/event-stream';
        //       proxyRes.headers['cache-control'] = 'no-cache';
        //       proxyRes.headers['connection'] = 'keep-alive';
        //       proxyRes.headers['access-control-allow-origin'] = '*';
        //     }
        //   });
        // }
      }
    }
  }
})