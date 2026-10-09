/**
 * Base local IndexedDB (Dexie) de la PWA (ADR 0006; research R-17).
 *
 * Nunca guarda tokens: el de acceso vive solo en memoria y el de renovación en una cookie
 * HttpOnly. La spec 003 agregará aquí las lecciones y el progreso pendiente de sincronizar.
 */
import Dexie, { type Table } from "dexie";

export interface MetaEntry {
  key: string;
  value: unknown;
}

export class SaberUliDB extends Dexie {
  meta!: Table<MetaEntry, string>;

  constructor() {
    super("saber-uli");
    this.version(1).stores({ meta: "key" });
  }
}

export const db = new SaberUliDB();
