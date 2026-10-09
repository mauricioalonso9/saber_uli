import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { type ReactNode, useState } from "react";
import { I18nextProvider } from "react-i18next";

import { ApiProblem } from "@/shared/api/http";
import { initI18n } from "@/shared/i18n";

export function Providers({ children }: { children: ReactNode }) {
  const [i18n] = useState(initI18n);
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          // Los errores ya llegan como ApiProblem con mensaje en español. Solo se reintenta una
          // vez lo que puede ser pasajero (red o 5xx); un 4xx no cambia al repetirlo.
          queries: {
            retry: (failures, error) =>
              failures < 1 &&
              !(error instanceof ApiProblem && error.status >= 400 && error.status < 500),
            refetchOnWindowFocus: false,
          },
        },
      }),
  );

  return (
    <I18nextProvider i18n={i18n}>
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    </I18nextProvider>
  );
}
