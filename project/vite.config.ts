import { defineConfig } from "vite";
import react from "@vitejs/plugin-react-swc";

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api/dashboard": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
      "/api/industry": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
      "/api/meta": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
      "/api/scoring": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
      "/api/system": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
      "/api/tags": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
      "/api/weights": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
      "/api/auth": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
      "/api/users": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
      "/api/invite-codes": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
      "/api": {
        target: "http://localhost:3001",
        changeOrigin: true,
      },
    },
  },
});
