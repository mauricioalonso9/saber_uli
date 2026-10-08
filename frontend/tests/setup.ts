/**
 * Configuración común de Vitest: matchers de Testing Library (`toBeInTheDocument`,
 * `toHaveFocus`, `toHaveTextContent`…), textos en es-CO y limpieza del DOM entre pruebas.
 */
import "@testing-library/jest-dom/vitest";

import { cleanup, configure } from "@testing-library/react";
import { afterEach } from "vitest";

import { initI18n } from "@/shared/i18n";

// Los componentes se prueban con los textos reales en es-CO.
initI18n();

// Las rutas se cargan bajo demanda (T174): con la suite en paralelo, importar una página con
// `react-markdown` puede pasar del segundo que `findBy…` espera por defecto.
configure({ asyncUtilTimeout: 5000 });

afterEach(() => {
  cleanup();
});
