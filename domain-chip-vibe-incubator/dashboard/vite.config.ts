import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 4176,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:4177',
        changeOrigin: true,
      },
    },
  },
})
