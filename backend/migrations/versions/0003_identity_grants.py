"""identity y shared: permisos del rol saber_app (research R-07; FR-035; data-model §2).

- `saber_app` (api, worker, beat) tiene DML en `identity` y en `shared.outbox_events`, nunca DDL
  ni `TRUNCATE`, y no toca `shared.alembic_version`.
- Solo inserción y lectura (garantizado por la base de datos, no solo por el código):
  `identity.audit_events` y `identity.consents` (FR-035, §2.11, §2.14) y
  `identity.policy_versions` (versiones publicadas inmutables, §2.10).
- `identity.users` sin `DELETE`: la supresión deja una lápida (FR-033).
- `saber_bi` no recibe nada en `identity` ni `shared`.
- Privilegios por defecto: las tablas que `saber_migrator` cree después en `identity` o
  `shared` dan DML a `saber_app`. Una tabla nueva de solo inserción debe revocar `UPDATE` y
  `DELETE` en su propia migración.

Revisión: 0003
Anterior: 0002
Creada: 2026-10-06
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0003"
down_revision: str | Sequence[str] | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DML = "SELECT, INSERT, UPDATE, DELETE"
APPEND_ONLY = "identity.audit_events, identity.consents, identity.policy_versions"

UPGRADE = [
    "GRANT USAGE ON SCHEMA identity, shared TO saber_app",
    f"GRANT {DML} ON ALL TABLES IN SCHEMA identity TO saber_app",
    f"GRANT {DML} ON shared.outbox_events TO saber_app",
    f"REVOKE UPDATE, DELETE ON {APPEND_ONLY} FROM saber_app",
    "REVOKE DELETE ON identity.users FROM saber_app",
    f"""ALTER DEFAULT PRIVILEGES FOR ROLE saber_migrator IN SCHEMA identity
        GRANT {DML} ON TABLES TO saber_app""",
    f"""ALTER DEFAULT PRIVILEGES FOR ROLE saber_migrator IN SCHEMA shared
        GRANT {DML} ON TABLES TO saber_app""",
]

DOWNGRADE = [
    f"""ALTER DEFAULT PRIVILEGES FOR ROLE saber_migrator IN SCHEMA shared
        REVOKE {DML} ON TABLES FROM saber_app""",
    f"""ALTER DEFAULT PRIVILEGES FOR ROLE saber_migrator IN SCHEMA identity
        REVOKE {DML} ON TABLES FROM saber_app""",
    "REVOKE ALL ON shared.outbox_events FROM saber_app",
    "REVOKE ALL ON ALL TABLES IN SCHEMA identity FROM saber_app",
    "REVOKE USAGE ON SCHEMA identity, shared FROM saber_app",
]


def upgrade() -> None:
    for statement in UPGRADE:
        op.execute(statement)


def downgrade() -> None:
    for statement in DOWNGRADE:
        op.execute(statement)
