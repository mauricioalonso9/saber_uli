"""identity: cuenta local de administración (enmienda de 001, US9; FR-040 a FR-047; R-41;
ADR 0009).

- `users.kind` admite `local`; columna `username` (citext, única) solo para las cuentas locales,
  que no tienen identidad de Entra ID ni correo.
- `sessions.auth_method` admite `local_password`.
- Tabla `local_credentials` (data-model §2.16): `saber_app` lee, inserta y actualiza; nunca borra.
- La cuenta `adminsaber` (rol Administrador, sin autorización ni perfil pendientes) con la
  contraseña inicial `adminsaber` y el cambio obligatorio. El hash es Argon2id con su propia sal;
  la contraseña es pública a propósito: el primer ingreso obliga a cambiarla (FR-041).

Revisión: 0010
Anterior: 0009
Creada: 2026-10-11
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0010"
down_revision: str | Sequence[str] | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

INITIAL_HASH = (
    "$argon2id$v=19$m=65536,t=3,p=4$2oHXKWcz+WxYxgdceOnKFA$"
    "zSWfTSYUGuax+EbQBXK/8lCSRHICdZAvAkAg9LO9sJ0"
)

UPGRADE = [
    "ALTER TABLE identity.users DROP CONSTRAINT ck_users_kind",
    """ALTER TABLE identity.users ADD CONSTRAINT ck_users_kind
           CHECK (kind IN ('institutional', 'guest', 'local'))""",
    "ALTER TABLE identity.users ADD COLUMN username citext",
    "ALTER TABLE identity.users ADD CONSTRAINT uq_users_username UNIQUE (username)",
    # Solo las cuentas locales tienen usuario, y no tienen identidad de Entra ID ni correo.
    """ALTER TABLE identity.users ADD CONSTRAINT ck_users_local_identity CHECK (
           (kind = 'local') = (username IS NOT NULL)
           AND (kind <> 'local'
                OR (entra_tenant_id IS NULL AND entra_object_id IS NULL AND email IS NULL))
       )""",
    "ALTER TABLE identity.sessions DROP CONSTRAINT ck_sessions_auth_method",
    """ALTER TABLE identity.sessions ADD CONSTRAINT ck_sessions_auth_method
           CHECK (auth_method IN ('entra_id', 'guest_link', 'local_password'))""",
    """CREATE TABLE identity.local_credentials (
           user_id          uuid        NOT NULL,
           password_hash    text        NOT NULL,
           must_change      boolean     NOT NULL DEFAULT true,
           failed_attempts  integer     NOT NULL DEFAULT 0,
           locked_until     timestamptz,
           changed_at       timestamptz NOT NULL DEFAULT now(),
           CONSTRAINT pk_local_credentials PRIMARY KEY (user_id),
           CONSTRAINT fk_local_credentials_user_id_users
               FOREIGN KEY (user_id) REFERENCES identity.users (id) ON DELETE CASCADE,
           CONSTRAINT ck_local_credentials_failed_attempts CHECK (failed_attempts >= 0),
           CONSTRAINT ck_local_credentials_argon2id
               CHECK (password_hash LIKE '$argon2id$%')
       )""",
    "GRANT SELECT, INSERT, UPDATE ON identity.local_credentials TO saber_app",
    """WITH admin AS (
           INSERT INTO identity.users (kind, username, display_name, onboarding_completed_at)
           VALUES ('local', 'adminsaber', 'Administración Saber Uli', now())
           RETURNING id
       ), role AS (
           INSERT INTO identity.role_assignments (user_id, role)
           SELECT id, 'admin' FROM admin
       )
       INSERT INTO identity.local_credentials (user_id, password_hash, must_change)
       SELECT id, :hash, true FROM admin""",
]

DOWNGRADE = [
    "DELETE FROM identity.users WHERE kind = 'local'",
    "DROP TABLE identity.local_credentials",
    "ALTER TABLE identity.sessions DROP CONSTRAINT ck_sessions_auth_method",
    """ALTER TABLE identity.sessions ADD CONSTRAINT ck_sessions_auth_method
           CHECK (auth_method IN ('entra_id', 'guest_link'))""",
    "ALTER TABLE identity.users DROP CONSTRAINT ck_users_local_identity",
    "ALTER TABLE identity.users DROP CONSTRAINT uq_users_username",
    "ALTER TABLE identity.users DROP COLUMN username",
    "ALTER TABLE identity.users DROP CONSTRAINT ck_users_kind",
    """ALTER TABLE identity.users ADD CONSTRAINT ck_users_kind
           CHECK (kind IN ('institutional', 'guest'))""",
]


def upgrade() -> None:
    import sqlalchemy as sa

    for statement in UPGRADE:
        if ":hash" in statement:
            op.execute(sa.text(statement).bindparams(hash=INITIAL_HASH))
        else:
            op.execute(statement)


def downgrade() -> None:
    for statement in DOWNGRADE:
        op.execute(statement)
