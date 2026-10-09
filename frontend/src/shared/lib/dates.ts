/**
 * Fechas para mostrar en es-CO con la hora de Colombia, sin importar la zona del dispositivo.
 */
const DATE_TIME = new Intl.DateTimeFormat("es-CO", {
  dateStyle: "long",
  timeStyle: "short",
  timeZone: "America/Bogota",
});

const DATE = new Intl.DateTimeFormat("es-CO", { dateStyle: "long", timeZone: "America/Bogota" });

export function formatDateTime(iso: string): string {
  return DATE_TIME.format(new Date(iso));
}

export function formatDate(iso: string): string {
  return DATE.format(new Date(iso));
}

/** Fecha sin hora del contrato (`2026-10-28`): es un día de Colombia, no medianoche en UTC. */
export function formatDay(isoDate: string): string {
  return DATE.format(new Date(`${isoDate}T12:00:00-05:00`));
}
