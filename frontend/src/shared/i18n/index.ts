/**
 * Textos de la interfaz en español de Colombia (constitución VII). Todos los textos visibles
 * salen de `es-CO.json`; el documento declara `lang="es-CO"`.
 */
import i18n from "i18next";
import { initReactI18next } from "react-i18next";

import esCO from "./es-CO.json";

export const LANGUAGE = "es-CO";

export function initI18n(): typeof i18n {
  if (!i18n.isInitialized) {
    void i18n.use(initReactI18next).init({
      lng: LANGUAGE,
      fallbackLng: LANGUAGE,
      resources: { [LANGUAGE]: { translation: esCO } },
      interpolation: { escapeValue: false }, // React ya escapa
      initAsync: false,
    });
  }
  document.documentElement.lang = LANGUAGE;
  return i18n;
}
