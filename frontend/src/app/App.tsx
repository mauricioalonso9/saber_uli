import { RouterProvider } from "@tanstack/react-router";
import { useState } from "react";

import { Providers } from "@/app/providers";
import { type AppRouter, createAppRouter } from "@/app/router";

export function App({ router }: { router?: AppRouter }) {
  const [appRouter] = useState(() => router ?? createAppRouter());
  return (
    <Providers>
      <RouterProvider router={appRouter} />
    </Providers>
  );
}
