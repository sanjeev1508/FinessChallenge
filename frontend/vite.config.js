import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// `npm run dev` proxies /api to the FastAPI server on :8000.
// `npm run build` writes straight into the backend so FastAPI serves the UI.
export default defineConfig({
  plugins: [react()],
  base: "./",
  server: { port: 5173, proxy: { "/api": "http://127.0.0.1:8000" } },
  build: { outDir: "../backend/app/static", emptyOutDir: true },
});
