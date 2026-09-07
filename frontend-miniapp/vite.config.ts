import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const target = env.VITE_BACKEND_PROXY || 'http://127.0.0.1:8000'
  return {
    plugins: [react()],
    resolve: { dedupe: ['react', 'react-dom'] },
    server: {
      port: 5173,
      host: '127.0.0.1',
      strictPort: true,
      proxy: {
        '/__preview': { target, changeOrigin: true },
        '/api': { target, changeOrigin: true },
        '/admin': { target, changeOrigin: true },
      },
    },
    build: { outDir: 'dist', sourcemap: false },
  }
})
