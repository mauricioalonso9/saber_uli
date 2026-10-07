# Quickstart: Identidad, acceso institucional e invitados

**Feature**: `001-identidad-acceso` | **Fecha**: 2026-10-05 | **Plan**: [plan.md](./plan.md)

Guía para levantar el entorno y comprobar de punta a punta que la funcionalidad cumple la
especificación. No contiene código de implementación: los detalles están en
[data-model.md](./data-model.md) y en [contracts/openapi.yaml](./contracts/openapi.yaml).

---

## 1. Requisitos previos

| Entorno | Requisito |
|---------|-----------|
| Windows 11 (desarrollo) | Docker Desktop con backend WSL2, Git, `uv`, Node.js 24 LTS |
| Servidor (producción) | Linux con Docker Engine y Compose v2, dominio con DNS y certificado TLS |
| Ambos | Credenciales de Microsoft Entra ID entregadas por la oficina de TI (sección 2) |

Para desarrollar **sin** credenciales reales de Entra ID se usa el perfil `e2e`, que levanta un
proveedor OIDC de prueba (sección 4).

---

## 2. Registro de la aplicación en Microsoft Entra ID (oficina de TI de Unilibre)

Pedir a TI que registre la aplicación con estos datos:

1. **Tipo de cuenta admitida**: *Solo cuentas de este directorio organizativo (inquilino único)*.
2. **URI de redirección (plataforma Web)**:
   - Desarrollo: `http://localhost/api/auth/microsoft/callback`
   - Producción: `https://<dominio-de-produccion>/api/auth/microsoft/callback`
3. **Secreto de cliente** con vencimiento documentado (se debe renovar antes de que expire).
4. **Permisos delegados**: `openid`, `profile`, `email`. No se requieren permisos de Microsoft
   Graph ni consentimiento de administrador adicional.
5. **Claims opcionales** del ID token: `email`.

TI entrega: *Tenant ID*, *Client ID* y *Client Secret*. Se cargan solo en `.env`, nunca en el
repositorio.

---

## 3. Levantar el entorno (desarrollo)

```powershell
# En la raíz del repositorio
copy .env.example .env
# Editar .env: ENTRA_TENANT_ID, ENTRA_CLIENT_ID, ENTRA_CLIENT_SECRET,
# INSTITUTIONAL_EMAIL_DOMAINS=unilibre.edu.co, JWT_SIGNING_KEY, SESSION_COOKIE_SECRET
docker compose up --build
```

Resultado esperado:

- Los servicios `proxy`, `api`, `worker`, `beat`, `db`, `redis` y `mailpit` quedan `healthy`;
  `migrate` termina con código 0 (migraciones aplicadas y versión 1 de la política cargada).
- `http://localhost` muestra la pantalla de ingreso de Saber Uli.
- `http://localhost/api/health` → `{"status":"ok"}`; `http://localhost/api/ready` → `{"status":"ok"}`.
- `http://localhost:8025` abre Mailpit (correos de invitación en desarrollo).

Primer administrador (después de haber ingresado una vez con la cuenta institucional):

```powershell
docker compose run --rm api saber-uli identity grant-admin --email <correo-institucional>
```

Cargar programas académicos (CSV UTF-8 con columnas `codigo,nombre,seccional`; repetir la carga
actualiza por `codigo` sin duplicar):

```powershell
docker compose run --rm -v ${PWD}\programas.csv:/tmp/programas.csv api `
  saber-uli identity import-programs --csv /tmp/programas.csv
```

Ejemplo de archivo (sirve el «CSV UTF-8» de Excel; el código va en mayúsculas, números o
guiones, de 2 a 20 caracteres):

```text
codigo,nombre,seccional
DER-BOG,Derecho,Bogotá
CON-CAL,Contaduría Pública,Cali
```

El comando informa cuántos programas creó, actualizó y dejó sin cambios, y lista las filas
rechazadas con su número y el motivo. Código de salida: `0` todo cargado; `1` hubo filas
rechazadas (las válidas sí se cargaron) o falló la base de datos; `2` el archivo no existe, no
está en UTF-8 o el encabezado no es `codigo,nombre,seccional` (no se cargó nada). Los programas
existentes conservan su estado activo o inactivo.

Después también se pueden gestionar desde `/admin/programas`.

---

## 4. Pruebas automatizadas

```powershell
# Infraestructura (Compose válido, servicios healthy, cabeceras de Nginx, sin procesos root)
cd backend
uv run pytest tests/infra
cd ..

# Backend (unitarias + integración con Testcontainers; requiere Docker)
cd backend
uv run pytest --cov=saber_uli --cov-report=term-missing
uv run ruff check . ; uv run mypy --strict src ; uv run lint-imports

# Contrato (con el stack arriba)
uv run schemathesis run ../specs/001-identidad-acceso/contracts/openapi.yaml --url http://localhost

# Frontend
cd ../frontend
npm ci ; npm run lint ; npm run typecheck ; npm test

# Extremo a extremo, accesibilidad y modo sin conexión (stack con proveedor OIDC de prueba)
cd ..
docker compose --profile e2e up -d --build
cd frontend ; npx playwright test
```

Criterios: todas las suites en verde; cobertura ≥ 80 % en `domain` y `application`;
Schemathesis sin fallos; axe sin infracciones de nivel AA.

---

## 5. Escenarios de validación manual

Cada escenario indica la historia o requisito que comprueba. Con el perfil `e2e`, el proveedor
de prueba permite elegir un usuario del inquilino Unilibre o uno externo.

| # | Escenario | Pasos | Resultado esperado |
|---|-----------|-------|--------------------|
| V1 | Primer ingreso institucional (HU1, HU2, HU3, SC-001) | Ingresar con una cuenta del inquilino → aceptar la política → completar programa, semestre, fecha y meta | Llega a `/inicio` en menos de 1 minuto; la cuenta tiene rol Estudiante; en `/mi-cuenta/autorizacion` se ve la versión aceptada y la fecha |
| V2 | Cuenta Microsoft externa (FR-002, SC-003) | Ingresar con un usuario de otro inquilino | Mensaje claro con la alternativa de invitación; `GET /api/v1/admin/users` no muestra cuenta nueva; el log registra `tenant_not_allowed` sin correo |
| V3 | Rechazo y revocación de la autorización (HU2) | Usuario nuevo elige "No acepto"; luego acepta; luego revoca | Sin acceso a ninguna función salvo política, cierre de sesión y supresión; tras revocar, la sesión se cierra en la siguiente acción |
| V4 | Nueva versión de la política (FR-017) | Administrador publica la versión 1.1 | Todo usuario debe aceptar la 1.1 en su siguiente navegación |
| V5 | Invitación individual (HU4, HU5, SC-007) | Docente invita a un correo externo → abrir el correo en Mailpit → pulsar "Ingresar" | Ingreso sin contraseña; rol Invitado; perfil pide solo nombre, meta y fecha opcional |
| V6 | Enlace usado o vencido (escenario 4.3) | Abrir otra vez el mismo enlace | "Solicita un enlace nuevo"; no se abre sesión |
| V7 | Correo institucional invitado (FR-008) | Invitar a `alguien@unilibre.edu.co` | Rechazo `institutional-email-not-invitable` |
| V8 | Plazo máximo del docente (FR-006a) | Docente invita con vencimiento a 200 días | Rechazo indicando el máximo (180 días); un administrador sí puede |
| V9 | Lote de invitaciones (FR-009, SC-005) | Cargar un CSV de 200 filas con correos inválidos, duplicados e institucionales → confirmar | Reporte por fila; solo las válidas se envían; todo el proceso toma menos de 5 minutos |
| V10 | Alcance del docente (escenario 5.7) | Docente A abre `/invitaciones` | Solo ve sus invitaciones; abrir una de otro docente responde "no encontrado" |
| V11 | Revocación inmediata (escenario 5.4, SC-003) | Con el invitado navegando, el administrador revoca su acceso | La siguiente acción del invitado muestra "acceso revocado"; no puede volver a ingresar |
| V12 | Renovación dentro de 90 días (escenario 5.5) | Renovar el acceso de un invitado vencido | El invitado vuelve a ingresar y conserva su progreso |
| V13 | Roles múltiples y último administrador (HU6) | Asignar Docente + Director a un usuario; intentar quitar el rol al único administrador | Unión de permisos; el retiro se rechaza con `last-admin` |
| V14 | Vista del docente y del director (FR-026, FR-027) | Docente abre su grupo; director consulta su programa | El docente ve nombres sin correos solo de sus grupos; el director no ve ningún dato identificable |
| V15 | Sesión privilegiada (R-15) | Administrador inactivo 31 minutos intenta una acción administrativa | Se le pide autenticarse de nuevo; la práctica personal no se interrumpe |
| V16 | Uso sin conexión (FR-038, FR-039) | Abrir la app instalada, activar modo avión; avanzar el reloj del dispositivo 8 días | Hasta el día 7 la app funciona sin red; después pide reconectarse; al reconectar con el acceso revocado, la actividad pendiente no se sincroniza y se muestra la causa |
| V17 | Consulta y descarga de datos (HU8) | `/mi-cuenta/datos` → Descargar | JSON con identidad, perfil, roles, grupos y autorizaciones |
| V18 | Supresión voluntaria (HU7, SC-006) | Solicitar supresión escribiendo ELIMINAR | Sesión cerrada al instante; el administrador ve la solicitud con fecha límite a 15 días hábiles; tras procesarse, la cuenta no aparece y reingresar crea una cuenta nueva |
| V19 | Conservación automática (FR-034a/b/c) | Ejecutar `process_retention` con fecha simulada (prueba de integración) | Aviso a los 30 días antes; supresión en la fecha; ingresar o renovar antes la cancela |
| V20 | Auditoría inmodificable (FR-035, SC-004) | Revisar `/admin/auditoria` tras V5–V18; intentar `UPDATE` sobre `identity.audit_events` con el rol `saber_app` | Cada acción administrativa tiene su evento; el `UPDATE` falla por permisos |
| V21 | Registros sin datos personales (principio V) | `docker compose logs api worker` tras V1–V18 | Ningún correo, nombre ni token en los registros |

---

## 6. Producción (resumen)

```bash
cp .env.example .env    # valores de producción; secretos desde el gestor de secretos
docker compose -f compose.yaml -f compose.prod.yaml up -d --build
```

- `compose.prod.yaml` activa HTTPS en Nginx (certificados montados), cabeceras HSTS y desactiva
  Mailpit; el correo sale por el SMTP configurado (`SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`,
  `SMTP_PASSWORD`, `SMTP_FROM`).
- Verificar V1, V2, V5 y V20 tras cada despliegue.
- Renovar el secreto de Entra ID antes de su vencimiento y rotar `JWT_SIGNING_KEY` con un `kid`
  nuevo (los tokens anteriores siguen válidos hasta 10 minutos).
