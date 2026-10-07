/**
 * Preparación de datos directamente en PostgreSQL del stack e2e: asignar el primer
 * administrador (`grant-admin` llega con US6, T147), dar por completado el perfil cuando la
 * prueba no trata de él y asegurar un programa en el catálogo. Ejecuta `psql` dentro del
 * contenedor `db` como `postgres`; los
 * valores viajan como variables de psql (`:'email'`), nunca concatenados en el SQL.
 *
 * El contenedor se busca por las etiquetas de Compose del proyecto `saber-uli` (`name:` de
 * `compose.yaml`) y el servicio `db`; `E2E_DB_CONTAINER` permite indicarlo a mano.
 */
import { execFileSync } from "node:child_process";

function dbContainer(): string {
  const configured = process.env.E2E_DB_CONTAINER;
  if (configured) return configured;
  const ids = execFileSync(
    "docker",
    [
      "ps",
      "-q",
      "--filter",
      "label=com.docker.compose.project=saber-uli",
      "--filter",
      "label=com.docker.compose.service=db",
    ],
    { encoding: "utf8" },
  )
    .split(/\s+/)
    .filter(Boolean);
  if (ids.length !== 1) {
    throw new Error(
      `se esperaba un contenedor db del stack e2e y hay ${ids.length}; defina E2E_DB_CONTAINER`,
    );
  }
  return ids[0] as string;
}

function psql(statement: string, variables: Record<string, string>): void {
  const args = ["exec", "-i", dbContainer(), "psql", "-U", "postgres", "-v", "ON_ERROR_STOP=1"];
  for (const [name, value] of Object.entries(variables)) {
    args.push("-v", `${name}=${value}`);
  }
  // La base es la de POSTGRES_DB del contenedor (saber_uli por defecto).
  args.push("-d", process.env.E2E_POSTGRES_DB ?? "saber_uli", "-q");
  execFileSync("docker", args, { input: statement, stdio: ["pipe", "ignore", "inherit"] });
}

/** Asigna el rol Administrador a un usuario que ya ingresó una vez. */
export function grantAdmin(email: string): void {
  psql(
    `INSERT INTO identity.role_assignments (user_id, role)
     SELECT id, 'admin' FROM identity.users WHERE lower(email) = lower(:'email')
     ON CONFLICT DO NOTHING;`,
    { email },
  );
}

/** Da por completado el primer ingreso (perfil, US3) de un usuario. */
export function completeOnboarding(email: string): void {
  psql(
    `UPDATE identity.users SET onboarding_completed_at = now()
     WHERE lower(email) = lower(:'email');`,
    { email },
  );
}

/** Crea un programa activo si no existe (el catálogo se carga con `import-programs`). */
export function ensureProgram(code: string, name: string, campus: string): void {
  psql(
    `INSERT INTO identity.programs (code, name, campus, active)
     VALUES (:'code', :'name', :'campus', true)
     ON CONFLICT (code) DO UPDATE SET active = true;`,
    { code, name, campus },
  );
}
