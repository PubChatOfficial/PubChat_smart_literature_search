import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'
import { fileURLToPath } from 'url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: '::', // 这行是关键！它告诉 Vite 监听所有的 IPv4 和 IPv6 地址
    port: 5173, // 
    strictPort: true, // 如果端口被占用就直接报错，而不是悄悄换个端口
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
      '@/components': path.resolve(__dirname, './src/components'),
      '@/api': path.resolve(__dirname, './src/api'),
      '@/interface': path.resolve(__dirname, './src/interface'),
      '@/icons': path.resolve(__dirname, './src/icons'),
      '@/styles': path.resolve(__dirname, './src/styles'),
      '@/utils': path.resolve(__dirname, './src/utils'),
    },
  },
})


