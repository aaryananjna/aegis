import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// The screens always connect to their own origin (/events/...), and Vite forwards the
// WebSocket to A's server. That way the same URL works on the laptop and through the tunnel.
const server = process.env.AEGIS_SERVER ?? 'http://localhost:8000'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    proxy: {
      '/events': { target: server, ws: true },
    },
  },
})
