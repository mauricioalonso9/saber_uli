/**
 * Rutas de la interfaz (research R-35). La ruta raíz aplica las guardias (T067) antes de cargar
 * cualquier página. Las páginas de ingreso, autorización y perfil son mínimas y las completan
 * T080, T085 y T097; cada historia agrega aquí sus rutas.
 */
import {
  Link,
  createMemoryHistory,
  createRootRouteWithContext,
  createRoute,
  createRouter,
  redirect,
} from "@tanstack/react-router";
import { useTranslation } from "react-i18next";

import { AppShell } from "@/app/AppShell";
import { type SessionState, decideNavigation } from "@/app/guards";
import { OFFLINE_EXPIRED_MESSAGE } from "@/features/auth/offline-access";
import { createSessionLoader } from "@/features/auth/session-loader";

export interface RouterContext {
  getSession: () => Promise<SessionState>;
}

function Page({ titleKey, bodyKey }: { titleKey: string; bodyKey?: string }) {
  const { t } = useTranslation();
  return (
    <section>
      <h1 className="mb-2 text-2xl font-bold">{t(titleKey)}</h1>
      {bodyKey ? <p>{t(bodyKey)}</p> : null}
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

function OfflineExpiredPage() {
  const { t } = useTranslation();
  return (
    <section>
      <h1 className="mb-2 text-2xl font-bold">{t("offline.title")}</h1>
      <p>{OFFLINE_EXPIRED_MESSAGE}</p>
    </section>
  );
}

const rootRoute = createRootRouteWithContext<RouterContext>()({
  component: AppShell,
  notFoundComponent: NotFoundPage,
  beforeLoad: async ({ context, location }) => {
    const target = decideNavigation(await context.getSession(), location.pathname);
    if (target) {
      throw redirect({ href: target });
    }
  },
});

const indexRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/",
  beforeLoad: () => {
    throw redirect({ to: "/inicio" });
  },
});

const page = <TPath extends string>(path: TPath, titleKey: string, bodyKey?: string) =>
  createRoute({
    getParentRoute: () => rootRoute,
    path,
    component: () => <Page titleKey={titleKey} bodyKey={bodyKey} />,
  });

const offlineRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/sin-conexion",
  component: OfflineExpiredPage,
});

export const routeTree = rootRoute.addChildren([
  indexRoute,
  page("/inicio", "home.title", "home.placeholder"),
  page("/ingresar", "login.title"),
  page("/acceso", "guestAccess.title"),
  page("/bienvenida/datos", "consent.title"),
  page("/bienvenida/perfil", "profile.title"),
  offlineRoute,
]);

export interface AppRouterOptions {
  /** Ruta inicial en memoria (pruebas); sin ella se usa el historial del navegador. */
  initialPath?: string;
  /** Estado de la sesión para las guardias; por defecto renovación + `/me` con caché. */
  getSession?: () => Promise<SessionState>;
}

export function createAppRouter(options: AppRouterOptions = {}) {
  return createRouter({
    routeTree,
    context: { getSession: options.getSession ?? createSessionLoader() },
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
