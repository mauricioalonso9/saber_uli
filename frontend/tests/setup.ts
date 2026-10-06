/**
 * Configuración común de Vitest: matchers de Testing Library (`toBeInTheDocument`,
 * `toHaveFocus`, `toHaveTextContent`…) y limpieza del DOM entre pruebas.
 */
import "@testing-library/jest-dom/vitest";

import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

afterEach(() => {
  cleanup();
});
