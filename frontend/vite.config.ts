import { defineConfig } from "vite"
import vue from "@vitejs/plugin-vue"

export default defineConfig(({ mode }) => ({
    plugins: [vue()],
    server: {
        host: true,
        port: 80,
        watch: {
            usePolling: true,
        },
        proxy:
            mode === "development"
                ? {
                      "/api": {
                          target:
                              process.env.VITE_BACKEND_URL ||
                              "http://localhost:1314",
                          changeOrigin: true,
                          rewrite: (path) => path.replace(/^\/api/, "/api"),
                      },
                  }
                : undefined,
    },
}))
