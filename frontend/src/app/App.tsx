import { RouterProvider } from "@tanstack/react-router";
import { useEffect, useState } from "react";

import { Providers } from "@/app/providers";
import { type AppRouter, createAppRouter } from "@/app/router";
import { clearOfflineSnapshot } from "@/features/auth/offline-access";
import { onSessionEnded } from "@/shared/api/http";

/**
 * Causas por las que la sesión terminó y que la persona debe conocer (FR-010, FR-011, SC-003):
 * `slug` del problema → código de `/ingresar?error=`. Una sesión simplemente vencida no se
 * explica; la guardia ya lleva a `/ingresar`.
 */
const ENDED_SESSION_CODES: Readonly<Record<string, string>> = {
  "guest-access-revoked": "guest_access_revoked",
  "guest-access-expired": "guest_access_expired",
  "account-disabled": "account_disabled",
  "account-deleted": "account_deleted",
};

export function App({ router }: { router?: AppRouter }) {
  const [appRouter] = useState(() => router ?? createAppRouter());

  useEffect(
    () =>
      onSessionEnded((slug) => {
        const code = ENDED_SESSION_CODES[slug];
        if (!code) return;
        appRouter.options.context.getSession.invalidate?.();
        // Sin acceso, tampoco se puede seguir usando sin conexión.
        clearOfflineSnapshot().catch(() => undefined);
        void appRouter.navigate({ to: "/ingresar", search: { error: code } });
      }),
    [appRouter],
  );

  return (
    <Providers>
      <RouterProvider router={appRouter} />
    </Providers>
  );
}
