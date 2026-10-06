import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

// La configuración de la PWA (vite-plugin-pwa) se agrega en T068.
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      "@": import.meta.dirname + "/src",
    },
  },
  server: {
    // Las pruebas leen el contrato OpenAPI con `?raw` para verificar el catálogo de problemas.
    fs: {
      allow: [".", "../specs/001-identidad-acceso/contracts"],
    },
    // `npm run dev` en el host contra el stack de Docker: el proxy publica la API en el puerto 80.
    proxy: {
      "/api": {
        target: "http://localhost:80",
        changeOrigin: true,
      },
    },
  },
  build: {
    sourcemap: false,
  },
  test: {
    environment: "jsdom",
    include: ["src/**/*.test.{ts,tsx}", "tests/unit/**/*.test.{ts,tsx}"],
    exclude: ["node_modules", "dist", "dev-dist", "tests/e2e"],
    restoreMocks: true,
    setupFiles: ["./tests/setup.ts"],
  },
});
