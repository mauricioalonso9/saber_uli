/**
 * Mensajes en español (es-CO) para cada `type` de problema del contrato (RFC 9457).
 *
 * El `type` es `urn:saber-uli:problem:<slug>`. `network-error` lo produce el cliente cuando no
 * hay respuesta del servidor. Los mensajes nunca incluyen datos personales.
 */
export const PROBLEM_PREFIX = "urn:saber-uli:problem:";

export const GENERIC_MESSAGE = "Algo salió mal. Intenta de nuevo en unos minutos.";

const MESSAGES: Readonly<Record<string, string>> = {
  // Sesión y acceso
  unauthenticated: "Tu sesión terminó. Ingresa de nuevo para continuar.",
  "session-expired": "Tu sesión venció por inactividad. Ingresa de nuevo para continuar.",
  "session-revoked": "Tu sesión se cerró por seguridad. Ingresa de nuevo para continuar.",
  "reauthentication-required":
    "Por seguridad, confirma tu identidad de nuevo para usar las funciones de gestión.",
  "account-disabled": "Tu cuenta está desactivada. Comunícate con la administración de Saber Uli.",
  "account-deleted": "Esta cuenta fue eliminada y ya no puede ingresar.",
  "guest-access-expired":
    "Tu acceso como invitado venció. Pide una nueva invitación a quien te invitó.",
  "guest-access-revoked":
    "Tu acceso como invitado fue retirado. Si crees que es un error, comunícate con quien te invitó.",
  "access-link-invalid":
    "El enlace de ingreso no es válido, ya se usó o venció. Solicita uno nuevo.",
  "guest-erased": "Los datos de este invitado ya fueron eliminados.",
  "rate-limited": "Hiciste demasiadas solicitudes seguidas. Espera un momento e intenta de nuevo.",
  // Autorización de datos y permisos
  "consent-required":
    "Para continuar debes aceptar la política de tratamiento de datos personales vigente.",
  "no-active-consent": "No tienes una autorización de tratamiento de datos vigente para revocar.",
  "policy-version-not-current":
    "La política cambió mientras la leías. Revisa la versión vigente y acéptala de nuevo.",
  "invalid-consent-decision": "Elige «Acepto» o «No acepto».",
  "policy-version-exists": "Esa versión de la política ya fue publicada. Usa un número nuevo.",
  "invalid-policy-version": "Revisa el número de versión, el título y el texto de la política.",
  "effective-from-too-early":
    "La fecha de vigencia debe ser posterior a la de la última versión publicada.",
  forbidden: "No tienes permiso para usar esta función.",
  "not-found": "No encontramos lo que buscas.",
  // Validación y conflictos
  "validation-error": "Revisa los datos marcados e intenta de nuevo.",
  conflict:
    "No se pudo completar porque los datos cambiaron. Actualiza la página e intenta de nuevo.",
  // Perfil
  "invalid-profile": "Revisa los datos de tu perfil e intenta de nuevo.",
  "program-not-available": "El programa elegido no está disponible. Elige otro de la lista.",
  "student-role-required": "Esta opción es solo para estudiantes.",
  "not-institutional-student": "Esta opción es solo para estudiantes con cuenta institucional.",
  // Invitaciones
  "institutional-email-not-invitable":
    "Las personas con correo institucional ingresan con su cuenta Unilibre; no necesitan invitación.",
  "invitation-already-active": "Esa persona ya tiene una invitación vigente.",
  "access-expiry-out-of-range":
    "La fecha de vencimiento del acceso está fuera del rango permitido.",
  "batch-too-large": "El archivo tiene demasiadas filas. Divídelo en lotes más pequeños.",
  "batch-not-pending": "Este lote ya fue procesado o cancelado.",
  "invitation-not-pending": "Solo se pueden reenviar las invitaciones que aún no se aceptaron.",
  "invitation-already-revoked": "Esta invitación ya estaba revocada.",
  "invitation-not-renewable":
    "Ya no se puede renovar este acceso: pasaron más de 90 días. Envía una invitación nueva.",
  // Roles, grupos y supresión
  "not-a-teacher": "La persona seleccionada no tiene el rol Docente.",
  "guest-role-exclusive": "Un invitado no puede tener otros roles.",
  "director-requires-programs": "Asigna al menos un programa al director de programa.",
  "last-admin": "No puedes quitar el rol Administrador al último administrador activo.",
  "deletion-already-requested": "Ya hay una solicitud de supresión de tu cuenta en curso.",
  // Producidos por el cliente o por el estado HTTP
  "service-unavailable": "El servicio no está disponible en este momento. Intenta más tarde.",
  "network-error": "No hay conexión con el servidor. Revisa tu conexión a internet.",
};

/** Extrae el slug de un `type` del contrato; `null` si no es un URN de Saber Uli. */
export function problemSlug(type: string): string | null {
  return type.startsWith(PROBLEM_PREFIX) ? type.slice(PROBLEM_PREFIX.length) : null;
}

/** Slug que corresponde a un estado HTTP cuando el `type` no es reconocible. */
export function slugForStatus(status: number): string | null {
  if (status === 0) return "network-error";
  if (status === 429) return "rate-limited";
  if (status >= 500) return "service-unavailable";
  return null;
}

export function problemMessage(type: string, status: number): string {
  const slug = problemSlug(type);
  if (slug && slug in MESSAGES) return MESSAGES[slug] as string;
  const fallback = slugForStatus(status);
  return (fallback && MESSAGES[fallback]) || GENERIC_MESSAGE;
}
