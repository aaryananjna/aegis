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
    // The family phone reaches this dev server through a Cloudflare quick tunnel
    // (docs/DEMO-RUNBOOK.md). Vite refuses unknown Host headers unless they're listed.
    allowedHosts: ['.trycloudflare.com'],
    proxy: {
      '/events': { target: server, ws: true },
      // Family accounts (#34/#35): same origin, so the httpOnly login cookie stays first-party.
      '/auth/': { target: server },
      '/elders': { target: server },
      '/device/': { target: server },
    },
  },
})
