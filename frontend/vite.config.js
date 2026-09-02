import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [
    react(),
    tailwindcss()
  ],
  server: {
    port: 5173,
    proxy: {
      '/calls': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        ws: true
      },
      '/analytics': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true
      },
      '/settings': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true
      },
      '/localization': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true
      },
      '/logs': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true
      },
      '/health': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true
      }
    }
  }
})
