import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { VitePWA } from "vite-plugin-pwa";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
    // PWA instalable (T068; ADR 0006). El registro va en un script externo (`registerSW.js`):
    // la CSP de Nginx no permite scripts en línea. Se carga con `defer` para no bloquear el
    // primer render (T174). La API nunca se precachea ni se usa como
    // fallback de navegación (los tokens y datos personales no se guardan en caché).
    VitePWA({
      registerType: "autoUpdate",
      injectRegister: "script-defer",
      filename: "sw.js",
      manifestFilename: "manifest.webmanifest",
      includeAssets: ["icons/apple-touch-icon-180.png"],
      manifest: {
        name: "Saber Uli",
        short_name: "Saber Uli",
        description:
          "Prepárate para los módulos genéricos de las pruebas Saber Pro con la Universidad Libre.",
        lang: "es-CO",
        dir: "ltr",
        start_url: "/inicio",
        scope: "/",
        display: "standalone",
        orientation: "portrait",
        background_color: "#ffffff",
        theme_color: "#15803d",
        icons: [
          { src: "/icons/icon-192.png", sizes: "192x192", type: "image/png" },
          { src: "/icons/icon-512.png", sizes: "512x512", type: "image/png" },
          {
            src: "/icons/maskable-512.png",
            sizes: "512x512",
            type: "image/png",
            purpose: "maskable",
          },
        ],
      },
      workbox: {
        globPatterns: ["**/*.{js,css,html,svg,png,webmanifest}"],
        navigateFallback: "/index.html",
        navigateFallbackDenylist: [/^\/api\//],
        cleanupOutdatedCaches: true,
      },
    }),
  ],
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
