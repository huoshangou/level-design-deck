import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// dev: Vite :5173 走 proxy 调 backend :8766；prod: backend 挂 dist/
const BACKEND = "http://127.0.0.1:8766";

export default defineConfig({
  plugins: [react()],
  server: {
    host: "127.0.0.1",
    port: 5173,
    strictPort: true,
    proxy: {
      "/api": BACKEND,
      "/legacy": BACKEND,
      "/outputs": BACKEND,
      "/lib": BACKEND,
      "/tools/levelcraft": BACKEND,
      "/templates/html": BACKEND,
      "/docs": BACKEND,
      "/ws": { target: BACKEND.replace("http", "ws"), ws: true },
    },
  },
  build: {
    outDir: "dist",
    emptyOutDir: true,
  },
});
