import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    host: "0.0.0.0",
    port: parseInt(process.env.PORT ?? "5173"),
    // Bind-mounted source on Docker/Windows doesn't emit native FS events,
    // so poll for changes to keep HMR working.
    watch: { usePolling: true, interval: 150 },
    proxy: {
      "/api": {
        target: "http://backend:8080",
        changeOrigin: true,
      },
      "/health": {
        target: "http://backend:8080",
        changeOrigin: true,
      },
    },
  },
});
