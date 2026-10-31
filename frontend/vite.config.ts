import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { fileURLToPath } from 'node:url'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: { alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) } },
  // The browser only talks to this origin; /api is forwarded to FastAPI, so the session cookie is same-origin.
  // Point it at another machine's API with API_TARGET=http://192.168.1.20:8000 npm run dev
  server: { port: 5173, proxy: { '/api': process.env.API_TARGET ?? 'http://localhost:8000' } },
})
