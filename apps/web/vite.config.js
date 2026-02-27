import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    // Proxy API calls to the FastAPI container so the browser never hits CORS
    proxy: {
      '/profiling': 'http://api:8000',
      '/upload':    'http://api:8000',
      '/healthz':   'http://api:8000',
    },
  },
})
