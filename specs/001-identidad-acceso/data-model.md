# Data Model: Identidad, acceso institucional e invitados

**Feature**: `001-identidad-acceso` | **Fecha**: 2026-10-05 | **Plan**: [plan.md](./plan.md)

Modelo de dominio y su persistencia en PostgreSQL 18. Los nombres de tablas y columnas están en
inglés (código); las descripciones, en español. Todas las claves primarias son `uuid` con
`DEFAULT uuidv7()`. Todas las fechas son `timestamptz` en UTC; los cálculos de "día" usan la zona
America/Bogota.

Esquemas creados en esta funcionalidad: `identity` (contexto de identidad) y `shared` (kernel
compartido: outbox). Ningún otro contexto lee estas tablas directamente (principio II).

---

## 1. Agregados y entidades del dominio

| Agregado (raíz) | Entidades y objetos de valor | Requisitos |
|-----------------|------------------------------|------------|
| `User` | `Profile`, `RoleAssignment`, `DirectorProgram`, `InstitutionalIdentity` (tid, oid) | FR-001…005, 019…026, 029, 034b |
| `Invitation` | `GuestAccess` (vence_en, revocada_en), `AccessLink` | FR-006…013, 034a |
| `InvitationBatch` | `BatchRow` (resultado por fila) | FR-009, SC-005 |
| `PolicyVersion` | — | FR-016, FR-017 |
| `Consent` | registro inmutable de una decisión | FR-014, 015, 018 |
| `Group` | `GroupMember`, `GroupTeacher` | FR-027 |
| `Program` | — | FR-028 |
| `DeletionRequest` | — | FR-032…034 |
| `Session` | `RefreshToken` (familia) | FR-037, 038 |
| `AuditEvent` | — (solo inserción) | FR-035, SC-004 |
| `Setting` | — | FR-006a |

---

## 2. Tablas del esquema `identity`

### 2.1 `users`

| Columna | Tipo | Reglas |
|---------|------|--------|
| `id` | uuid PK | `uuidv7()` |
| `kind` | text | `CHECK (kind IN ('institutional','guest'))` |
| `status` | text | `CHECK (status IN ('active','disabled','deletion_pending','deleted'))`, por defecto `active` |
| `entra_tenant_id` | uuid NULL | solo institucionales |
| `entra_object_id` | uuid NULL | solo institucionales; `NULL` tras la supresión |
| `email` | citext NULL | correo institucional o del invitado; `NULL` tras la supresión |
| `display_name` | text NULL | `NULL` tras la supresión |
| `auth_epoch` | integer | por defecto 0; se incrementa en cada evento que revoca sesiones (R-16) |
| `last_login_at` | timestamptz NULL | base del año de conservación de institucionales (FR-034b) |
| `retention_notice_sent_at` | timestamptz NULL | aviso de 30 días enviado (FR-034c); se limpia al ingresar o renovar |
| `onboarding_completed_at` | timestamptz NULL | perfil completo |
| `created_at`, `updated_at` | timestamptz | |

Restricciones e índices:
- `UNIQUE (entra_tenant_id, entra_object_id)` — una cuenta por persona institucional (FR-005).
- `CHECK (kind <> 'institutional' OR status = 'deleted' OR (entra_tenant_id IS NOT NULL AND entra_object_id IS NOT NULL))`.
- `CHECK (status <> 'deleted' OR (email IS NULL AND display_name IS NULL AND entra_object_id IS NULL))` — una lápida no contiene datos personales (FR-033).
- Índice único parcial `(lower(email)) WHERE kind = 'guest' AND status <> 'deleted'` — un invitado vigente por correo.
- Índice `(kind, last_login_at) WHERE status = 'active'` para la tarea de conservación.
- Requiere la extensión `citext`.

### 2.2 `profiles`

| Columna | Tipo | Reglas |
|---------|------|--------|
| `user_id` | uuid PK, FK → `users.id` `ON DELETE CASCADE` | uno a uno |
| `program_id` | uuid NULL, FK → `programs.id` | obligatorio para institucionales al completar el perfil |
| `semester` | smallint NULL | `CHECK (semester BETWEEN 1 AND 12)` |
| `expected_exam_date` | date NULL | obligatoria para institucionales, opcional para invitados |
| `daily_goal` | text | `CHECK (daily_goal IN ('casual','regular','intense'))` |
| `guest_display_name` | text NULL | nombre que indica el invitado (FR-020) |
| `updated_at` | timestamptz | |

Invariante (aplicación): el perfil de un institucional está completo si tiene `program_id`,
`semester`, `expected_exam_date` y `daily_goal`; el de un invitado, si tiene
`guest_display_name` y `daily_goal`.

### 2.3 `role_assignments`

| Columna | Tipo | Reglas |
|---------|------|--------|
| `user_id` | uuid FK → `users.id` `ON DELETE CASCADE` | |
| `role` | text | `CHECK (role IN ('student','guest','teacher','program_director','admin'))` |
| `assigned_by` | uuid NULL | `NULL` = sistema |
| `assigned_at` | timestamptz | |

- PK `(user_id, role)`.
- Invariantes (aplicación y prueba de integración): un `guest` no tiene otros roles (FR-024); un
  institucional siempre conserva `student`; no se puede retirar `admin` al último administrador
  activo (FR-025, se valida con bloqueo `SELECT … FOR UPDATE` sobre los administradores activos).

### 2.4 `director_programs`

| Columna | Tipo | Reglas |
|---------|------|--------|
| `user_id` | uuid FK → `users.id` `ON DELETE CASCADE` | debe tener rol `program_director` |
| `program_id` | uuid FK → `programs.id` | |

PK `(user_id, program_id)` (FR-026).

### 2.5 `programs`

| Columna | Tipo | Reglas |
|---------|------|--------|
| `id` | uuid PK | |
| `code` | text UNIQUE | código institucional, por ejemplo `DER-BOG` |
| `name` | text | |
| `campus` | text | seccional |
| `active` | boolean | los inactivos no aparecen al completar el perfil |

### 2.6 `groups`, `group_members`, `group_teachers`

`groups`: `id`, `name`, `description`, `cohort_label` (por ejemplo `2026-2`), `program_id` NULL,
`created_by`, `created_at`, `archived_at` NULL.

`group_members`: PK `(group_id, user_id)`; el usuario debe ser institucional con rol `student`
(un invitado no puede pertenecer a un grupo institucional, escenario 6.5).

`group_teachers`: PK `(group_id, user_id)`; el usuario debe tener rol `teacher`.

Regla de lectura (FR-027): un docente solo ve el nombre (`display_name`) y el progreso de los
miembros de los grupos donde está en `group_teachers`; nunca su correo.

### 2.7 `invitations`

| Columna | Tipo | Reglas |
|---------|------|--------|
| `id` | uuid PK | |
| `email` | citext NULL | correo destino; `NULL` tras la supresión del invitado o la purga de FR-034e |
| `invitee_name` | text NULL | nombre opcional que indica quien invita |
| `invited_by` | uuid NULL FK → `users.id` | docente o administrador; `NULL` = sistema (comando `invite-guest`, T118) |
| `batch_id` | uuid NULL FK → `invitation_batches.id` | |
| `guest_user_id` | uuid NULL FK → `users.id` | se llena al aceptar |
| `status` | text | `CHECK (status IN ('sent','accepted','expired','revoked'))` |
| `access_expires_at` | timestamptz | vencimiento del acceso del invitado |
| `link_expires_at` | timestamptz NULL | vencimiento del enlace de invitación vigente |
| `sent_at`, `accepted_at`, `revoked_at` | timestamptz NULL | |
| `last_delivery_status` | text NULL | `queued`, `sent`, `failed` (caso límite de rebote) |
| `created_at`, `updated_at` | timestamptz | |

- Índice único parcial `(lower(email)) WHERE status IN ('sent','accepted')` — no hay dos
  invitaciones vigentes al mismo correo (caso límite de duplicados).
- `CHECK (access_expires_at > created_at)`.
- Regla FR-006a (aplicación): si quien invita no es administrador,
  `access_expires_at ≤ now() + setting(teacher_max_access_days)`.
- Regla FR-034e (tarea `expire_invitations`): si la invitación nunca se aceptó
  (`accepted_at IS NULL`) y pasaron 90 días desde `revoked_at` (si fue revocada) o, si no, desde
  `link_expires_at`,
  se ponen en `NULL` `email` e `invitee_name` y se borran sus `access_links`. Por eso `email`
  admite `NULL` también en invitaciones no aceptadas.

### 2.8 `access_links`

| Columna | Tipo | Reglas |
|---------|------|--------|
| `id` | uuid PK | |
| `invitation_id` | uuid FK → `invitations.id` `ON DELETE CASCADE` | |
| `purpose` | text | `CHECK (purpose IN ('invitation','sign_in'))` |
| `token_hash` | bytea UNIQUE | SHA-256 del token; el token en claro nunca se guarda (R-19) |
| `expires_at` | timestamptz | 7 días (`invitation`) o 15 minutos (`sign_in`) |
| `used_at` | timestamptz NULL | un solo uso |
| `created_at` | timestamptz | |

Al emitir un enlace nuevo se invalidan (`used_at = now()`) los anteriores sin usar de la misma
invitación y propósito.

### 2.9 `invitation_batches`

| Columna | Tipo | Reglas |
|---------|------|--------|
| `id` | uuid PK | |
| `created_by` | uuid FK → `users.id` | |
| `status` | text | `CHECK (status IN ('pending_confirmation','confirmed','expired'))` |
| `rows` | jsonb | lista de filas con `line`, `email`, `name`, `access_expires_at`, `result` (`valid`, `invalid_email`, `duplicate_in_file`, `already_invited`, `institutional_email`, `expiry_out_of_range`) |
| `valid_count`, `invalid_count` | integer | |
| `expires_at` | timestamptz | 24 horas para confirmar |
| `created_at`, `confirmed_at` | timestamptz | |

Los lotes se purgan 30 días después de confirmados o vencidos (contienen correos).

### 2.10 `policy_versions`

| Columna | Tipo | Reglas |
|---------|------|--------|
| `id` | uuid PK | |
| `version` | text UNIQUE | por ejemplo `1.0` |
| `title` | text | |
| `body_markdown` | text | finalidad, datos recogidos, derechos y canales (FR-016) |
| `effective_from` | timestamptz | la versión vigente es la de mayor `effective_from ≤ now()` |
| `published_by` | uuid NULL | |
| `created_at` | timestamptz | |

Las versiones publicadas son inmutables (sin `UPDATE`; solo `INSERT` para `saber_app`).

### 2.11 `consents` (solo inserción)

| Columna | Tipo | Reglas |
|---------|------|--------|
| `id` | uuid PK | |
| `user_id` | uuid FK → `users.id` | |
| `policy_version_id` | uuid FK → `policy_versions.id` | |
| `decision` | text | `CHECK (decision IN ('accepted','rejected','revoked'))` |
| `channel` | text | medio de aceptación, por ejemplo `web_pwa` (escenario 2.2) |
| `decided_at` | timestamptz | |

- Índice `(user_id, decided_at DESC)`.
- **Autorización vigente** de un usuario = su último registro tiene `decision = 'accepted'` y
  `policy_version_id` = versión vigente. Cualquier otro caso → `consent_required`.
- `saber_app` solo tiene `INSERT` y `SELECT`. Al suprimir a un usuario, sus filas se conservan
  como prueba de la autorización, enlazadas solo al UUID de la lápida.

### 2.12 `deletion_requests`

| Columna | Tipo | Reglas |
|---------|------|--------|
| `id` | uuid PK | |
| `user_id` | uuid FK → `users.id` | |
| `origin` | text | `CHECK (origin IN ('user_request','guest_retention','institutional_retention'))` |
| `status` | text | `CHECK (status IN ('received','in_progress','completed'))` |
| `requested_at` | timestamptz | |
| `due_date` | date | `requested_at` + 15 días hábiles en Colombia (R-25) |
| `completed_at` | timestamptz NULL | |

Índice único parcial `(user_id) WHERE status <> 'completed'`.

### 2.13 `sessions` y `refresh_tokens`

`sessions`: `id` (= `sid` del token de acceso), `user_id`, `auth_method`
(`entra_id`, `guest_link`), `auth_time`, `last_seen_at`, `last_privileged_activity_at` NULL,
`absolute_expires_at` (30 días), `revoked_at` NULL, `revoked_reason` NULL, `created_at`.

`refresh_tokens`: `id`, `session_id` FK `ON DELETE CASCADE`, `token_hash` bytea UNIQUE,
`issued_at`, `idle_expires_at` (7 días tras emisión), `rotated_at` NULL.

Reglas:
- Al crear la sesión o al reautenticarse, `last_privileged_activity_at = auth_time` (R-15).
- Al renovar: si el token ya tiene `rotated_at`, se revoca la sesión completa (reutilización
  detectada) y se audita.
- Al incrementar `users.auth_epoch` se revocan todas las sesiones del usuario.
- La tarea diaria purga sesiones vencidas o revocadas hace más de 30 días.

### 2.14 `audit_events` (solo inserción)

| Columna | Tipo | Reglas |
|---------|------|--------|
| `id` | uuid PK | |
| `occurred_at` | timestamptz | |
| `actor_id` | uuid NULL | `NULL` = sistema (tareas programadas, CLI) |
| `action` | text | catálogo cerrado, ver §5 |
| `target_type` | text | `user`, `invitation`, `group`, `program`, `policy`, `setting`, `deletion_request`, `session` |
| `target_id` | uuid NULL | |
| `subject_user_id` | uuid NULL | usuario afectado |
| `details` | jsonb | sin datos personales (por ejemplo roles antes/después, vencimientos) |

Índices: `(occurred_at DESC)`, `(subject_user_id, occurred_at DESC)`, `(actor_id, occurred_at DESC)`.
`saber_app` solo tiene `INSERT` y `SELECT` (FR-035).

### 2.15 `settings`

| Clave | Tipo de valor | Por defecto |
|-------|---------------|-------------|
| `teacher_max_access_days` | integer | 180 |
| `default_guest_access_days` | integer | 90 |
| `invitation_link_ttl_days` | integer | 7 |
| `sign_in_link_ttl_minutes` | integer | 15 |

Columnas: `key` PK, `value` jsonb, `updated_by`, `updated_at`. Cada cambio se audita.

---

## 3. Esquema `shared`

### 3.1 `outbox_events`

| Columna | Tipo | Reglas |
|---------|------|--------|
| `id` | uuid PK | también es la clave de idempotencia de los manejadores |
| `context` | text | contexto emisor, por ejemplo `identity` |
| `event_type` | text | por ejemplo `identity.InvitationCreated` |
| `payload` | jsonb | solo identificadores; **sin datos personales ni tokens** |
| `occurred_at` | timestamptz | |
| `available_at` | timestamptz | para reintentos con espera |
| `attempts` | integer | |
| `processed_at` | timestamptz NULL | |
| `last_error` | text NULL | sin datos personales |

Índice parcial `(available_at) WHERE processed_at IS NULL`. Purga a los 7 días de procesado.

---

## 4. Máquinas de estado

### 4.1 Usuario (`users.status`)

```text
            desactivar (admin)
  active ───────────────────────► disabled
    ▲  ◄─────────────────────────    │
    │        reactivar (admin)       │
    │                                │
    └─ solicitud de supresión / retención ─► deletion_pending ──► deleted (lápida)
```

- `deleted` es final. Toda transición sale de `active` o `disabled` a `deletion_pending`
  incrementa `auth_epoch`.
- El acceso de un invitado no es un estado del usuario: se **deriva** de su invitación
  (§4.2). El estado que muestra la interfaz (activo, desactivado, vencido, revocado, en
  supresión) combina ambos.

### 4.2 Invitación (`invitations.status`)

```text
  sent ──(consumo del enlace)──► accepted ──(access_expires_at < now)──► expired
   │                                │                                       │
   │ (link_expires_at < now)        │ revocar                               │ renovar (< 90 días
   ▼                                ▼                                       │  desde el fin del acceso)
 expired ◄──── reenviar ───► sent  revoked ──── renovar (< 90 días) ────────┴──► accepted
```

- **Reenviar** (solo sin aceptar): emite un enlace nuevo y vuelve a `sent`.
- **Renovar** (aceptada que venció o fue revocada, dentro de los 90 días): fija un nuevo
  `access_expires_at` futuro, limpia `revoked_at` y `retention_notice_sent_at`, y vuelve a
  `accepted`; el invitado conserva su progreso (escenario 5.5).
- Después de la supresión del invitado no hay renovación: una nueva invitación crea otro usuario
  (caso límite).

### 4.3 Solicitud de supresión

`received → in_progress → completed`. El procesamiento es idempotente: si el worker falla a la
mitad, la reanudación completa los pasos faltantes.

---

## 5. Catálogo de acciones auditadas

`user.created`, `user.role_granted`, `user.role_revoked`, `user.director_programs_changed`,
`user.disabled`, `user.reactivated`, `user.erased`, `invitation.created`, `invitation.resent`,
`invitation.expiry_changed`, `invitation.revoked`, `invitation.accepted`,
`invitation_batch.confirmed`, `group.created`, `group.updated`, `group.archived`,
`group.member_added`, `group.member_removed`, `group.teacher_added`, `group.teacher_removed`,
`program.created`, `program.updated`, `policy.published`, `consent.accepted`,
`consent.rejected`, `consent.revoked`, `deletion.requested`, `deletion.completed`,
`retention.notice_sent`, `retention.skipped_last_admin`, `invitation.contact_purged`,
`setting.changed`, `session.reuse_detected`, `auth.login_rejected`.

---

## 6. Eventos de dominio

| Evento | Emisor | Reacción (worker) |
|--------|--------|-------------------|
| `identity.InvitationCreated` | crear invitación o confirmar lote | emitir enlace `invitation`, enviar correo |
| `identity.InvitationResent` | reenviar | emitir enlace nuevo, enviar correo |
| `identity.SignInLinkRequested` | `POST /api/auth/guest/link-requests` con correo de invitado vigente | emitir enlace `sign_in`, enviar correo |
| `identity.RetentionNoticeDue` | tarea `process_retention` | enviar aviso de supresión en 30 días |
| `identity.DeletionRequested` | solicitud o retención | procesar la supresión |
| `identity.UserErased` | fin de la supresión | los contextos futuros anonimizan sus datos (consumidores en 002+) |
| `identity.UserAccessChanged` | desactivación, revocación, retiro de roles, supresión | invalidar la caché de `auth_epoch` en Redis |

Los payloads llevan solo identificadores. El correo destino se lee desde `identity` en el
manejador, dentro del worker, justo antes de enviar.

---

## 7. Validaciones derivadas de los requisitos

| Regla | Dónde se valida |
|-------|-----------------|
| Solo `tid` de Unilibre (FR-002) | aplicación (`AuthenticateInstitutionalUser`) |
| Correo institucional no invitable (FR-008) | dominio (`Invitation.create`) |
| Plazo máximo de docentes (FR-006a) | dominio con `Setting` |
| Alcance de invitaciones del docente (FR-006) | aplicación + consulta filtrada por `invited_by` |
| Invitado sin otros roles; último admin (FR-024, FR-025) | dominio + bloqueo en transacción |
| Autorización vigente para usar la plataforma (FR-014) | dependencia de FastAPI en todas las rutas salvo la lista permitida |
| Perfil completo según tipo (FR-019, FR-020) | dominio (`Profile.is_complete`) |
| Auditoría inmodificable (FR-035) | permisos de base de datos |
| El último administrador activo no se suprime (FR-034d) | aplicación (`RequestDeletion`, `process_retention`) con el mismo bloqueo de FR-025 |
| Purga del contacto de invitaciones no aceptadas (FR-034e) | tarea `expire_invitations` |
| Lápida sin datos personales (FR-033) | `CHECK` en `users` |
