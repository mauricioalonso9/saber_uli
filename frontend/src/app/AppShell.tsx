import { Link, Outlet, useRouteContext, useRouter } from "@tanstack/react-router";
import { useTranslation } from "react-i18next";

import type { Permission } from "@/api/model";
import { cn } from "@/shared/lib/utils";
import { logout } from "@/features/auth/bootstrap";
import { useOnlineStatus } from "@/shared/lib/use-online-status";
import { Button } from "@/shared/ui/button";
import { InstallHint } from "@/shared/ui/InstallHint";

/** Enlaces de docentes y de administración: se muestran solo con el permiso (FR-030). */
const STAFF_LINKS: ReadonlyArray<{
  to:
    | "/invitaciones"
    | "/grupos"
    | "/admin/usuarios"
    | "/admin/grupos"
    | "/admin/programas"
    | "/admin/parametros"
    | "/admin/auditoria"
    | "/admin/politica";
  label: string;
  permissions: Permission[];
}> = [
  {
    to: "/invitaciones",
    label: "nav.invitations",
    permissions: ["invitations:manage_own", "invitations:manage_all"],
  },
  { to: "/grupos", label: "nav.myGroups", permissions: ["groups:read_own_students"] },
  { to: "/admin/usuarios", label: "nav.users", permissions: ["users:manage"] },
  { to: "/admin/grupos", label: "nav.groups", permissions: ["groups:manage"] },
  { to: "/admin/programas", label: "nav.programs", permissions: ["programs:manage"] },
  { to: "/admin/parametros", label: "nav.settings", permissions: ["settings:manage"] },
  { to: "/admin/auditoria", label: "nav.audit", permissions: ["audit:read"] },
  { to: "/admin/politica", label: "nav.policy", permissions: ["policy:publish"] },
];

/**
 * Estructura común: enlace para saltar al contenido (primer elemento enfocable), cabecera con la
 * marca y el estado de conexión, navegación principal y contenido (WCAG 2.2 AA).
 */
export function AppShell() {
  const { t } = useTranslation();
  const online = useOnlineStatus();
  const router = useRouter();
  const { session, getSession } = useRouteContext({ from: "__root__" });

  async function signOut() {
    await logout();
    getSession.invalidate?.();
    await router.navigate({ to: "/ingresar" });
  }

  return (
    <div className="min-h-dvh bg-background text-foreground">
      <a
        href="#contenido"
        className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded-md focus:bg-primary focus:px-4 focus:py-2 focus:text-primary-foreground"
        onClick={(event) => {
          event.preventDefault();
          document.getElementById("contenido")?.focus();
        }}
      >
        {t("app.skipToContent")}
      </a>
      <header className="flex items-center justify-between border-b px-4 py-3">
        <span className="text-lg font-bold text-primary">{t("app.name")}</span>
        <p
          role="status"
          aria-live="polite"
          aria-label={t("connection.label")}
          className={cn(
            "rounded-full px-3 py-1 text-sm font-medium",
            online ? "bg-green-100 text-green-900" : "bg-amber-100 text-amber-900",
          )}
        >
          {online ? t("connection.online") : t("connection.offline")}
        </p>
        {session?.kind === "authenticated" ? (
          <Button type="button" variant="outline" size="sm" onClick={() => void signOut()}>
            {t("auth.signOut")}
          </Button>
        ) : null}
      </header>
      <InstallHint />
      <nav aria-label={t("app.mainNavigation")} className="border-b px-4 py-2">
        <ul className="flex flex-wrap gap-x-4 gap-y-1">
          <li>
            <Link
              to="/inicio"
              className="rounded-sm underline-offset-4 hover:underline focus-visible:outline-2 focus-visible:outline-offset-2"
            >
              {t("nav.home")}
            </Link>
          </li>
          {session?.kind === "authenticated" && !session.me.onboarding.consent_required
            ? STAFF_LINKS.filter(({ permissions }) =>
                permissions.some((permission) => session.me.permissions.includes(permission)),
              ).map(({ to, label }) => (
                <li key={to}>
                  <Link
                    to={to}
                    className="rounded-sm underline-offset-4 hover:underline focus-visible:outline-2 focus-visible:outline-offset-2"
                  >
                    {t(label)}
                  </Link>
                </li>
              ))
            : null}
          {session?.kind === "authenticated" && !session.me.onboarding.consent_required ? (
            <li>
              <Link
                to="/mi-cuenta"
                className="rounded-sm underline-offset-4 hover:underline focus-visible:outline-2 focus-visible:outline-offset-2"
              >
                {t("nav.account")}
              </Link>
            </li>
          ) : null}
        </ul>
      </nav>
      <main id="contenido" tabIndex={-1} className="mx-auto max-w-3xl px-4 py-6 outline-none">
        <Outlet />
      </main>
    </div>
  );
}
