import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// In development `npm run dev` serves the UI on :5173 and proxies API calls
// to the Python backend on :8000, so both hot-reload independently.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': 'http://localhost:8000',
      '/uploads': 'http://localhost:8000',
    },
  },
})
