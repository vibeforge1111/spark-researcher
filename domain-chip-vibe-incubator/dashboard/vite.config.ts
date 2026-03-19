import path from 'path'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [tailwindcss(), react()],
  resolve: {
    alias: { '@': path.resolve(__dirname, 'src') },
  },
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
