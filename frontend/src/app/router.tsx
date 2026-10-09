/**
 * Rutas de la interfaz (research R-35). La ruta raíz aplica las guardias (T067) antes de cargar
 * cualquier página. Cada historia agrega aquí sus rutas. Las páginas distintas de `/ingresar` se
 * cargan bajo demanda para que el ingreso descargue solo lo necesario (T174); el service worker
 * las precachea igual, así que siguen disponibles sin conexión.
 */
import {
  Link,
  createMemoryHistory,
  createRootRouteWithContext,
  createRoute,
  createRouter,
  lazyRouteComponent,
  redirect,
} from "@tanstack/react-router";
import { useTranslation } from "react-i18next";

import { AppShell } from "@/app/AppShell";
import { type SessionState, decideNavigation } from "@/app/guards";
import { OFFLINE_EXPIRED_MESSAGE } from "@/features/auth/offline-access";
import { LoginPage } from "@/features/auth/LoginPage";
import { createSessionLoader } from "@/features/auth/session-loader";

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
  component: lazyRouteComponent(() => import("@/features/onboarding/ConsentPage"), "ConsentPage"),
});

const profileRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/bienvenida/perfil",
  component: lazyRouteComponent(() => import("@/features/onboarding/ProfilePage"), "ProfilePage"),
});

const accountRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/mi-cuenta",
  component: lazyRouteComponent(() => import("@/features/account/AccountPage"), "AccountPage"),
});

const consentSettingsRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/mi-cuenta/autorizacion",
  component: lazyRouteComponent(
    () => import("@/features/account/ConsentSettingsPage"),
    "ConsentSettingsPage",
  ),
});

const myDataRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/mi-cuenta/datos",
  component: lazyRouteComponent(() => import("@/features/account/MyDataPage"), "MyDataPage"),
});

const adminPolicyRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/admin/politica",
  component: lazyRouteComponent(() => import("@/features/admin/PolicyPage"), "PolicyPage"),
});

const guestAccessRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/acceso",
  component: lazyRouteComponent(() => import("@/features/auth/GuestAccessPage"), "GuestAccessPage"),
});

const guestLinkRequestRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/ingresar/invitado",
  component: lazyRouteComponent(
    () => import("@/features/auth/GuestLinkRequestPage"),
    "GuestLinkRequestPage",
  ),
});

const invitationsRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/invitaciones",
  component: lazyRouteComponent(
    () => import("@/features/invitations/InvitationsPage"),
    "InvitationsPage",
  ),
});

const adminUsersRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/admin/usuarios",
  component: lazyRouteComponent(() => import("@/features/admin/UsersPage"), "UsersPage"),
});

const adminGroupsRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/admin/grupos",
  component: lazyRouteComponent(() => import("@/features/admin/GroupsPage"), "GroupsPage"),
});

const adminGroupRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/admin/grupos/$groupId",
  component: lazyRouteComponent(() => import("@/features/admin/GroupDetail"), "GroupDetail"),
});

const adminProgramsRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/admin/programas",
  component: lazyRouteComponent(() => import("@/features/admin/ProgramsPage"), "ProgramsPage"),
});

const adminSettingsRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/admin/parametros",
  component: lazyRouteComponent(() => import("@/features/admin/SettingsPage"), "SettingsPage"),
});

const adminAuditRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/admin/auditoria",
  component: lazyRouteComponent(() => import("@/features/admin/AuditPage"), "AuditPage"),
});

const adminDeletionsRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/admin/supresiones",
  component: lazyRouteComponent(
    () => import("@/features/admin/DeletionRequestsPage"),
    "DeletionRequestsPage",
  ),
});

const teacherGroupsRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/grupos",
  component: lazyRouteComponent(
    () => import("@/features/teacher/TeacherGroupsPage"),
    "TeacherGroupsPage",
  ),
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
  invitationsRoute,
  adminUsersRoute,
  adminGroupsRoute,
  adminGroupRoute,
  adminProgramsRoute,
  adminSettingsRoute,
  adminAuditRoute,
  adminDeletionsRoute,
  teacherGroupsRoute,
  myDataRoute,
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
