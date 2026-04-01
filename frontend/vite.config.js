import { defineConfig } from 'vite'
import { svelte } from '@sveltejs/vite-plugin-svelte'

export default defineConfig({
  plugins: [svelte()],
  server: {
    host: true,  // bind to 0.0.0.0 — required for Docker port forwarding
    proxy: {
      '/api': process.env.API_TARGET ?? 'http://localhost:8000',
    },
  },
  build: {
    outDir: 'dist',
  },
})
