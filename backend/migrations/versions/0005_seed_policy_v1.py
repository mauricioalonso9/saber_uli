"""identity: semilla de la versión 1.0 de la política de tratamiento de datos (data-model §2.10).

Revisión: 0005
Anterior: 0004
Creada: 2026-10-07

El texto sale de `seeds/politica_tratamiento_datos_v1.md` (en la imagen Docker, `/app/seeds`,
junto a `/app/migrations`). La carga es idempotente: si la versión 1.0 ya existe, no se toca,
porque las versiones publicadas son inmutables.
"""

from collections.abc import Sequence
from pathlib import Path

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: str | Sequence[str] | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

VERSION = "1.0"
TITLE = "Política de tratamiento de datos personales de Saber Uli"
POLICY_FILE = Path(__file__).resolve().parents[2] / "seeds" / "politica_tratamiento_datos_v1.md"


def upgrade() -> None:
    body = POLICY_FILE.read_text(encoding="utf-8")
    op.get_bind().execute(
        sa.text(
            """INSERT INTO identity.policy_versions (version, title, body_markdown, effective_from)
               VALUES (:version, :title, :body, now())
               ON CONFLICT (version) DO NOTHING"""
        ),
        {"version": VERSION, "title": TITLE, "body": body},
    )


def downgrade() -> None:
    # Si alguien ya decidió sobre la 1.0, sus registros son prueba de la autorización: se conserva.
    op.get_bind().execute(
        sa.text(
            """DELETE FROM identity.policy_versions p
               WHERE p.version = :version
                 AND NOT EXISTS (SELECT 1 FROM identity.consents c
                                 WHERE c.policy_version_id = p.id)"""
        ),
        {"version": VERSION},
    )
