import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5197,
    strictPort: true,
    proxy: {
      "/api": "http://127.0.0.1:8041",
      "/health": "http://127.0.0.1:8041",
      "/docs": "http://127.0.0.1:8041",
      "/docs-assets": "http://127.0.0.1:8041",
      "/openapi.json": "http://127.0.0.1:8041",
    },
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks: { three: ["three"], react: ["react", "react-dom"] },
      },
    },
  },
});
