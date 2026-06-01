import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'
import frappeui from 'frappe-ui/vite'

export default defineConfig(({ command }) => ({
  base: command === 'build' ? '/assets/buildsuite_core/frontend/' : '/',
  plugins: [
    // lucideIcons resolves ~icons/lucide/* used inside frappe-ui components.
    // frappeProxy / jinjaBootData / buildConfig are disabled — BuildSuite manages them separately.
    ...frappeui({
      lucideIcons: true,
      frappeProxy: false,
      jinjaBootData: false,
      buildConfig: false,
    }),
    vue(),
  ],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  // frappe-ui uses ~icons/lucide/* virtual modules resolved by a custom Rollup
  // plugin. Exclude it from esbuild pre-bundling so Vite's plugin pipeline
  // (which has the lucideIcons Rollup plugin) handles it in dev mode.
  optimizeDeps: {
    exclude: ['frappe-ui'],
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
    proxy: {
      '/api': {
        target: process.env.VITE_FRAPPE_HOST || 'http://localhost:8001',
        changeOrigin: true,
        secure: false,
      },
    },
  },
}))
