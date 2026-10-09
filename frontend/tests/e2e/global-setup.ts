/**
 * Antes de cada corrida e2e se borran los contadores de límites de peticiones (R-31) del Redis
 * del stack: varias corridas en la misma hora agotarían, por ejemplo, las 20 solicitudes de
 * enlace por hora y por IP, y todas las pruebas salen de la misma IP. En CI el stack es nuevo en
 * cada corrida y esto no cambia nada.
 */
import { execFileSync } from "node:child_process";

export default function globalSetup(): void {
  const ids = execFileSync(
    "docker",
    [
      "ps",
      "-q",
      "--filter",
      "label=com.docker.compose.project=saber-uli",
      "--filter",
      "label=com.docker.compose.service=redis",
    ],
    { encoding: "utf8" },
  )
    .split(/\s+/)
    .filter(Boolean);
  const container = process.env.E2E_REDIS_CONTAINER ?? ids[0];
  if (!container) return; // sin el stack, las pruebas fallarán con un mensaje más claro
  execFileSync(
    "docker",
    [
      "exec",
      container,
      "sh",
      "-c",
      "redis-cli --scan --pattern 'saber-uli:rl:*' | xargs -r redis-cli del > /dev/null",
    ],
    { stdio: ["ignore", "ignore", "inherit"] },
  );
}
