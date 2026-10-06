/**
 * CÓDIGO GENERADO por orval desde specs/001-identidad-acceso/contracts/openapi.yaml.
 * Generado, no editar a mano: ejecute `npm run api:generate` (principio III).
 */
import type { ProblemErrorsItem } from "./problemErrorsItem";

/**
 * RFC 9457 Problem Details. `detail` está en español y nunca contiene datos personales.
 */
export interface Problem {
  type: string;
  title: string;
  /**
   * @minimum 400
   * @maximum 599
   */
  status: number;
  detail?: string;
  instance?: string;
  /** Errores de validación por campo */
  errors?: ProblemErrorsItem[];
}
