import js from "@eslint/js";
import jsxA11y from "eslint-plugin-jsx-a11y";
import globals from "globals";
import tseslint from "typescript-eslint";

export default tseslint.config(
  {
    // Código generado (orval) y artefactos: no se revisan a mano.
    ignores: [
      "dist/**",
      "dev-dist/**",
      "coverage/**",
      "node_modules/**",
      "src/api/**",
      "tests/e2e/report/**",
      "test-results/**",
      "playwright-report/**",
    ],
  },
  js.configs.recommended,
  ...tseslint.configs.recommended,
  jsxA11y.flatConfigs.recommended,
  {
    files: ["**/*.{ts,tsx}"],
    languageOptions: {
      globals: { ...globals.browser },
    },
  },
  {
    files: ["**/*.test.{ts,tsx}", "tests/**/*.{ts,tsx}", "src/test/**"],
    languageOptions: {
      globals: { ...globals.node },
    },
    rules: {
      // Las pruebas simulan errores y estados límite.
      "@typescript-eslint/no-explicit-any": "off",
    },
  },
  {
    files: ["vite.config.ts", "orval.config.ts", "playwright.config.ts", "eslint.config.js"],
    languageOptions: {
      globals: { ...globals.node },
    },
  },
);
