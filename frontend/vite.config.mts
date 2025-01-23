/// <reference types="vite/client" />
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tsconfigPaths from 'vite-tsconfig-paths'
import { resolve } from 'path'

export default defineConfig({
    plugins: [react(), tsconfigPaths()],
    server: {
      port: 3000,
      host: '0.0.0.0',
      strictPort: true
    },
    publicDir: 'public',
    cacheDir: '/tmp/vite',
    base: '/',
    build: {
      rollupOptions: {
        input: {
          main: resolve(__dirname, 'index.html')
        }
      }
    }
  })