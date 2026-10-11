# ADR 0009: Cuenta local de administración con contraseña

- **Estado**: Aceptado
- **Fecha**: 2026-10-11
- **Origen**: enmienda de `specs/001-identidad-acceso/spec.md` (US9, FR-040 a FR-047), research
  R-41
- **Modifica**: [ADR 0005](0005-autenticacion-entra-id-e-invitados.md), que no preveía contraseñas
  propias

## Contexto

La plataforma solo admitía el ingreso institucional (Entra ID) y el de invitados por enlace. Sin
las credenciales de Entra ID, o si el ingreso institucional falla, nadie puede administrarla. La
persona responsable pidió (2026-10-11) una cuenta `adminsaber` con usuario y contraseña, también
en producción, con la contraseña inicial `adminsaber` y cambio obligatorio en el primer ingreso.
La constitución exige OWASP ASVS nivel 2.

## Decisión

1. **Una sola cuenta local**, de tipo `local`, con el usuario `adminsaber` y el rol
   Administrador. La crea una migración con la contraseña inicial `adminsaber` marcada para
   cambio obligatorio. No tiene identidad de Entra ID ni datos personales (sin correo; nombre
   "Administración Saber Uli"), así que no pide autorización de datos ni perfil y no se suprime
   por inactividad.
2. **Hash Argon2id** con `argon2-cffi` y sus parámetros por defecto (RFC 9106, perfil de baja
   memoria: 3 pasadas, 64 MiB, 4 hilos). Se vuelve a calcular si cambian los parámetros.
3. **Cambio obligatorio**: mientras esté pendiente, la sesión se emite sin roles y con
   `pwd_change`: ninguna función responde salvo cambiar la contraseña, cerrar sesión y `/me`.
   El cambio exige la contraseña actual, sube `auth_epoch` (cierra todas las sesiones) y abre una
   sesión nueva completa.
4. **Política** (ASVS V2.1): de 12 a 128 caracteres, sin recortar ni componer reglas de
   mayúsculas o símbolos, distinta del usuario y de la actual, y fuera de una lista de
   contraseñas comunes incluida en el código.
5. **Fuerza bruta** (ASVS V2.2.1): 10 intentos por minuto por IP en Redis y bloqueo de la cuenta
   15 minutos tras 10 fallos seguidos (contador en la base). Usuario inexistente y contraseña
   incorrecta dan el mismo 401 genérico, y se verifica contra un hash ficticio para igualar
   el tiempo.
6. **Recuperación**: `saber-uli identity reset-local-password` vuelve a la contraseña inicial con
   cambio obligatorio, desbloquea y cierra las sesiones. Requiere acceso al servidor.

## Consecuencias

- Mientras no se cambie, la contraseña inicial es pública: la mitigan el cambio obligatorio
  antes de cualquier función, el bloqueo y el límite por IP, y el registro en la auditoría.
- La cuenta local no tiene segundo factor (ASVS 4.0.3 V4.3.1 lo pide para las interfaces de
  administración): desviación aceptada por la persona responsable para operar sin Entra ID; queda
  en la revisión ASVS de 001.
- Una dependencia nueva: `argon2-cffi`.

## Alternativas descartadas

- **Ingreso de administración solo en desarrollo**: no cubría la operación en producción, que es
  lo pedido.
- **Contraseña fijada solo por comando (sin inicial)**: más segura, pero la persona responsable
  eligió la contraseña inicial con cambio obligatorio.
- **bcrypt o PBKDF2**: Argon2id es la primera opción de OWASP para hashes de contraseñas.
