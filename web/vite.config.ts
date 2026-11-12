import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// In dev, Vite serves the app and forwards /api (HTTP + WebSockets) to `hoss serve`.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": { target: "http://127.0.0.1:8000", ws: true },
    },
  },
});
