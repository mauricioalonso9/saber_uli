/**
 * Rutas de la interfaz (research R-35). En 001 la base tiene el shell, `/inicio` (marcador hasta
 * la spec 003) y la página de ruta desconocida; cada historia agrega sus rutas aquí.
 */
import {
  Link,
  createMemoryHistory,
  createRootRoute,
  createRoute,
  createRouter,
  redirect,
} from "@tanstack/react-router";
import { useTranslation } from "react-i18next";

import { AppShell } from "@/app/AppShell";

function HomePage() {
  const { t } = useTranslation();
  return (
    <section>
      <h1 className="mb-2 text-2xl font-bold">{t("home.title")}</h1>
      <p>{t("home.placeholder")}</p>
    </section>
  );
}

function NotFoundPage() {
  const { t } = useTranslation();
  return (
    <section>
      <h1 className="mb-2 text-2xl font-bold">{t("notFound.title")}</h1>
      <p className="mb-4">{t("notFound.body")}</p>
      <Link to="/inicio" className="underline">
        {t("notFound.back")}
      </Link>
    </section>
  );
}

const rootRoute = createRootRoute({ component: AppShell, notFoundComponent: NotFoundPage });

const indexRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/",
  beforeLoad: () => {
    throw redirect({ to: "/inicio" });
  },
});

const homeRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/inicio",
  component: HomePage,
});

export const routeTree = rootRoute.addChildren([indexRoute, homeRoute]);

export interface AppRouterOptions {
  /** Ruta inicial en memoria (pruebas); sin ella se usa el historial del navegador. */
  initialPath?: string;
}

export function createAppRouter(options: AppRouterOptions = {}) {
  return createRouter({
    routeTree,
    history: options.initialPath
      ? createMemoryHistory({ initialEntries: [options.initialPath] })
      : undefined,
    defaultPreload: "intent",
  });
}

export type AppRouter = ReturnType<typeof createAppRouter>;

declare module "@tanstack/react-router" {
  interface Register {
    router: AppRouter;
  }
}
