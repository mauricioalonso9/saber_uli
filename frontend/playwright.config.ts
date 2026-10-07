/**
 * Pruebas e2e contra el stack de Compose con el perfil `e2e` (T069; research R-36).
 *
 *   docker compose --profile e2e up -d --wait
 *   npm run test:e2e
 *
 * El navegador entra por `http://localhost` (el proxy) y el proveedor OIDC simulado se alcanza en
 * `http://oidc:8080`, el mismo nombre que usa la API dentro de Compose: el host necesita la
 * entrada `127.0.0.1 oidc` en su archivo hosts (CI la agrega; ver quickstart).
 */
import { defineConfig, devices } from "@playwright/test";

const baseURL = process.env.E2E_BASE_URL ?? "http://localhost";

export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: true,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 2 : 0,
  reporter: process.env.CI ? [["list"], ["html", { open: "never" }]] : "list",
  use: {
    baseURL,
    locale: "es-CO",
    timezoneId: "America/Bogota",
    trace: "retain-on-failure",
  },
  projects: [
    {
      name: "pixel-7",
      use: {
        ...devices["Pixel 7"],
        locale: "es-CO",
        // Resuelve `oidc` (proveedor simulado) sin tocar el archivo hosts del equipo.
        launchOptions: { args: ["--host-resolver-rules=MAP oidc 127.0.0.1"] },
      },
    },
    { name: "iphone-14", use: { ...devices["iPhone 14"], locale: "es-CO" } },
  ],
});
