# ADR 0005: Autenticación con Microsoft Entra ID, invitados por enlace y sesión propia

- **Estado**: Aceptado
- **Fecha**: 2026-10-05
- **Origen**: `specs/001-identidad-acceso/plan.md`, research R-10 a R-19

## Contexto

La comunidad Unilibre ingresa con su cuenta Microsoft 365 y las personas externas lo hacen por
invitación, sin contraseñas (spec 001). La constitución pide OWASP ASVS nivel 2 y la
especificación exige uso sin conexión durante 7 días (FR-038) y revocación inmediata con
conexión.

## Decisión

1. **Institucionales**: OpenID Connect con Authlib, cliente confidencial, *authorization code* +
   PKCE resuelto en el backend. Registro *single tenant*, autoridad específica del inquilino y
   validación explícita de `tid` e `iss`. Identidad estable = (`tid`, `oid`). Solo alcances
   `openid profile email`; sin Microsoft Graph. El frontend nunca ve tokens de Microsoft.
2. **Invitados**: tokens de 256 bits de un solo uso guardados como hash; enlace de invitación de
   7 días y de ingreso de 10 minutos (15 hasta el 2026-10-08; ASVS 2.7.2, T178a). El enlace apunta al frontend con el token en el fragmento
   (`/acceso#t=…`) y se consume con un POST explícito, para que los escáneres de correo no lo
   gasten. Sin contraseñas.
3. **Sesión propia** para ambos: token de acceso JWT de 10 minutos en memoria del frontend y
   token de renovación opaco, rotativo y con detección de reutilización, en cookie `HttpOnly`,
   `Secure`, `SameSite=Strict`, `Path=/api/auth`. Duración de aprendizaje: 7 días de
   inactividad y 30 días absolutos.
4. **Funciones privilegiadas** (docente, director, administrador): exigen `auth_time` menor a
   12 horas y actividad privilegiada en los últimos 30 minutos (ASVS 4.0.3 V3.3.2 nivel 2).
5. **Revocación inmediata**: `auth_epoch` por usuario, verificada en cada petición contra Redis.

## Consecuencias

- Sin contraseñas que custodiar; la seguridad de la cuenta institucional queda en Entra ID
  (incluido el MFA que TI tenga configurado).
- La desviación de ASVS V3.3.2 para sesiones de aprendizaje queda acotada a funciones sin datos
  de terceros y justificada por FR-038.
- Depende de que TI registre la aplicación y renueve el secreto de cliente a tiempo.

## Alternativas descartadas

- **MSAL para Python**: API síncrona; su caché de tokens no aporta porque no se llama a APIs de
  Microsoft.
- **Cookie de sesión en todas las peticiones**: exige protección CSRF en toda la API.
- **Contraseñas para invitados**: más superficie de ataque y soporte de recuperación.
