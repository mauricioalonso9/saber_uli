import { defineConfig } from "orval";

/**
 * Generación del cliente y los hooks de TanStack Query desde el contrato OpenAPI (T005).
 *
 * El código generado vive en `src/api/` y NO se edita a mano (principio III); el mutador
 * `src/shared/api/http.ts` centraliza la autenticación y el manejo de errores (stub en T005;
 * lo completan T047/T063).
 */
const header = (feature: string) => () => [
  `CÓDIGO GENERADO por orval desde specs/${feature}/contracts/openapi.yaml.`,
  "Generado, no editar a mano: ejecute `npm run api:generate` (principio III).",
];

/**
 * Opciones comunes de los dos destinos: un contrato por funcionalidad (research 002/R-15).
 */
const override = (feature: string) => ({
  mutator: {
    path: "./src/shared/api/http.ts",
    name: "customInstance",
  },
  header: header(feature),
  fetch: {
    includeHttpResponseReturnType: false,
    forceSuccessResponse: true,
  },
  query: {
    usePrefetch: false,
    useInvalidate: false,
  },
});

export default defineConfig({
  saberUli: {
    input: {
      target: "../specs/001-identidad-acceso/contracts/openapi.yaml",
    },
    output: {
      mode: "tags",
      target: "./src/api",
      schemas: "./src/api/model",
      client: "react-query",
      // Solo lo de 001: `src/api/content/` es del destino de 002.
      clean: ["*.ts", "model/**"],
      formatter: "prettier",
      override: {
        mutator: {
          path: "./src/shared/api/http.ts",
          name: "customInstance",
        },
        header: header("001-identidad-acceso"),
        fetch: {
          // Cliente limpio estilo orval v7: las funciones devuelven los datos (no el envoltorio
          // {data, status, headers}); los errores los lanza el mutador y los captura TanStack Query.
          includeHttpResponseReturnType: false,
          forceSuccessResponse: true,
        },
        query: {
          // Se omiten useQuery/useMutation a propósito: orval genera query para GET y mutation
          // para el resto por defecto. Fijarlos aquí globalmente forzaría el modo equivocado.
          usePrefetch: false,
          useInvalidate: false,
        },
      },
    },
  },
  content: {
    input: {
      target: "../specs/002-banco-items/contracts/openapi.yaml",
    },
    output: {
      mode: "tags",
      target: "./src/api/content",
      schemas: "./src/api/content/model",
      client: "react-query",
      clean: true,
      formatter: "prettier",
      override: override("002-banco-items"),
    },
  },
});
