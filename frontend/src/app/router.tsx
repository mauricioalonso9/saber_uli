/**
 * Rutas de la interfaz (research R-35). La ruta raíz aplica las guardias (T067) antes de cargar
 * cualquier página. Cada historia agrega aquí sus rutas.
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
import { GuestAccessPage } from "@/features/auth/GuestAccessPage";
import { GuestLinkRequestPage } from "@/features/auth/GuestLinkRequestPage";
import { LoginPage } from "@/features/auth/LoginPage";
import { createSessionLoader } from "@/features/auth/session-loader";
import { AccountPage } from "@/features/account/AccountPage";
import { ConsentSettingsPage } from "@/features/account/ConsentSettingsPage";
import { PolicyPage } from "@/features/admin/PolicyPage";
import { ConsentPage } from "@/features/onboarding/ConsentPage";
import { ProfilePage } from "@/features/onboarding/ProfilePage";

export interface SessionGetter {
  (): Promise<SessionState>;
  /** Olvida la sesión en caché (tras ingresar o cerrar sesión). */
  invalidate?: () => void;
}

export interface RouterContext {
  getSession: SessionGetter;
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
    const session = await context.getSession();
    const target = decideNavigation(session, location.pathname);
    if (target) {
      throw redirect({ href: target });
    }
    return { session };
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

interface LoginSearch {
  error?: string;
  return_to?: string;
}

const loginRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/ingresar",
  validateSearch: (search: Record<string, unknown>): LoginSearch => ({
    error: typeof search.error === "string" ? search.error : undefined,
    return_to: typeof search.return_to === "string" ? search.return_to : undefined,
  }),
  component: LoginPage,
});

const consentRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/bienvenida/datos",
  component: ConsentPage,
});

const profileRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/bienvenida/perfil",
  component: ProfilePage,
});

const accountRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/mi-cuenta",
  component: AccountPage,
});

const consentSettingsRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/mi-cuenta/autorizacion",
  component: ConsentSettingsPage,
});

const adminPolicyRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/admin/politica",
  component: PolicyPage,
});

const guestAccessRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/acceso",
  component: GuestAccessPage,
});

const guestLinkRequestRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/ingresar/invitado",
  component: GuestLinkRequestPage,
});

const offlineRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/sin-conexion",
  component: OfflineExpiredPage,
});

export const routeTree = rootRoute.addChildren([
  indexRoute,
  page("/inicio", "home.title", "home.placeholder"),
  loginRoute,
  guestAccessRoute,
  guestLinkRequestRoute,
  consentRoute,
  consentSettingsRoute,
  adminPolicyRoute,
  // Marcador: la supresión (US7) y la consulta y descarga de datos (US8, T169) la completan.
  page("/mi-cuenta/datos", "accountData.title", "accountData.placeholder"),
  profileRoute,
  accountRoute,
  offlineRoute,
]);

export interface AppRouterOptions {
  /** Ruta inicial en memoria (pruebas); sin ella se usa el historial del navegador. */
  initialPath?: string;
  /** Estado de la sesión para las guardias; por defecto renovación + `/me` con caché. */
  getSession?: SessionGetter;
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
