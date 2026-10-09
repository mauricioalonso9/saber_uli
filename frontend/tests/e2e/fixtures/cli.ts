/**
 * Comandos de operación (`saber-uli …`) dentro del contenedor `api` del stack e2e, como los
 * ejecutaría la oficina de TI (quickstart §3). El contenedor se busca por las etiquetas de
 * Compose del proyecto `saber-uli`; `E2E_API_CONTAINER` permite indicarlo a mano.
 */
import { execFileSync } from "node:child_process";

function apiContainer(): string {
  const configured = process.env.E2E_API_CONTAINER;
  if (configured) return configured;
  const ids = execFileSync(
    "docker",
    [
      "ps",
      "-q",
      "--filter",
      "label=com.docker.compose.project=saber-uli",
      "--filter",
      "label=com.docker.compose.service=api",
    ],
    { encoding: "utf8" },
  )
    .split(/\s+/)
    .filter(Boolean);
  if (ids.length !== 1) {
    throw new Error(`se esperaba un contenedor api y hay ${ids.length}; defina E2E_API_CONTAINER`);
  }
  return ids[0] as string;
}

/** `saber-uli identity invite-guest`: el worker envía el correo a Mailpit. */
export function inviteGuest(email: string, days = 30): void {
  execFileSync(
    "docker",
    [
      "exec",
      apiContainer(),
      "saber-uli",
      "identity",
      "invite-guest",
      "--email",
      email,
      "--days",
      String(days),
    ],
    { stdio: ["ignore", "ignore", "inherit"] },
  );
}
