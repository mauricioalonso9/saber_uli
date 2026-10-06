import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { type ReactNode, useState } from "react";
import { I18nextProvider } from "react-i18next";

import { initI18n } from "@/shared/i18n";

export function Providers({ children }: { children: ReactNode }) {
  const [i18n] = useState(initI18n);
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          // Los errores ya llegan como ApiProblem con mensaje en español; un solo reintento.
          queries: { retry: 1, refetchOnWindowFocus: false },
        },
      }),
  );

  return (
    <I18nextProvider i18n={i18n}>
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    </I18nextProvider>
  );
}
