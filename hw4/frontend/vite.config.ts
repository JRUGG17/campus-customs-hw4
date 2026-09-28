import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// Forward API and image requests to the FastAPI backend on :8000,
// so the browser only ever talks to the Vite dev server (no CORS needed).
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://127.0.0.1:8000',
      '/media': 'http://127.0.0.1:8000',
    },
  },
})
