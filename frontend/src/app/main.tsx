import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { App } from "@/app/App";
import { initI18n } from "@/shared/i18n";
import "@/index.css";

initI18n();

const rootElement = document.getElementById("root");
if (!rootElement) {
  throw new Error("No se encontró el elemento raíz (#root)");
}

createRoot(rootElement).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
