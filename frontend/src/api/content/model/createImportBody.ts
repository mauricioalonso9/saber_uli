/**
 * CÓDIGO GENERADO por orval desde specs/002-banco-items/contracts/openapi.yaml.
 * Generado, no editar a mano: ejecute `npm run api:generate` (principio III).
 */

export type CreateImportBody = {
  /** `.json` (formato del banco inicial) o `.xlsx` (plantilla); máximo 10 MB y 1 000 ítems */
  file: Blob | File;
};
