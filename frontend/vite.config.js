import { fileURLToPath } from 'node:url'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  css: {
    preprocessorOptions: {
      // Lets every .scss file do `@use "tokens" as *;` without relative paths.
      scss: { loadPaths: [fileURLToPath(new URL('./src/styles', import.meta.url))] },
    },
  },
  server: {
    // Forward API calls to the FastAPI backend in dev (no CORS needed).
    proxy: { '/api': 'http://localhost:8000' },
  },
})
