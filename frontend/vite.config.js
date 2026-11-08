import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Single URL in development: the app and the API are both served from http://localhost:5173.
// Vite forwards every /api/* request to the backend (BACKEND_URL, default http://localhost:4000),
// so the browser never talks to port 4000 directly.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: process.env.BACKEND_URL || "http://localhost:4000",
        changeOrigin: true,
      },
    },
  },
});
