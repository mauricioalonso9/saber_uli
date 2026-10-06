import { Link, Outlet } from "@tanstack/react-router";
import { useTranslation } from "react-i18next";

import { cn } from "@/shared/lib/utils";
import { useOnlineStatus } from "@/shared/lib/use-online-status";
import { InstallHint } from "@/shared/ui/InstallHint";

/**
 * Estructura común: enlace para saltar al contenido (primer elemento enfocable), cabecera con la
 * marca y el estado de conexión, navegación principal y contenido (WCAG 2.2 AA).
 */
export function AppShell() {
  const { t } = useTranslation();
  const online = useOnlineStatus();

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
      </header>
      <InstallHint />
      <nav aria-label={t("app.mainNavigation")} className="border-b px-4 py-2">
        <ul className="flex gap-4">
          <li>
            <Link
              to="/inicio"
              className="rounded-sm underline-offset-4 hover:underline focus-visible:outline-2 focus-visible:outline-offset-2"
            >
              {t("nav.home")}
            </Link>
          </li>
        </ul>
      </nav>
      <main id="contenido" tabIndex={-1} className="mx-auto max-w-3xl px-4 py-6 outline-none">
        <Outlet />
      </main>
    </div>
  );
}
