import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'

export default defineConfig(({ command }) => ({
  base: command === 'build' ? '/assets/buildsuite_core/frontend/' : '/',
  plugins: [vue()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  build: {
    outDir: path.resolve(__dirname, '../buildsuite_core/public/frontend'),
    emptyOutDir: true,
    manifest: 'manifest.json',
    sourcemap: true,
  },
  server: {
    port: 5173,
    open: true,
  },
}))
