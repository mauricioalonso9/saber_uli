import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { App } from "@/app/App";
import "@/index.css";

// El arranque real (router, proveedores, i18n) se implementa en T061.
const rootElement = document.getElementById("root");
if (!rootElement) {
  throw new Error("No se encontró el elemento raíz (#root)");
}

createRoot(rootElement).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
