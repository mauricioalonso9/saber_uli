"""content: permisos del rol saber_app (data-model §2.14; FR-047; research R-14).

- DML sin `DELETE` sobre lo que se versiona o se audita: módulos, taxonomía, rúbricas,
  contextos, ítems y versiones (las versiones publicadas son inmutables por el código y las
  pruebas; ninguna fila se borra).
- Solo inserción y lectura: historia de los ítems, versiones de contexto, imágenes,
  exportaciones, cambios de taxonomía y cargas del banco inicial.
- `DELETE` solo sobre `taxonomy_nodes` (una categoría sin uso, FR-045) e `item_version_stats`
  (se reemplazan cada noche, R-13).
- De `imports` solo cambian su estado y su resultado; las vencidas no se borran (R-05).
- `saber_bi` no recibe nada en `content`.

Revisión: 0009
Anterior: 0008
Creada: 2026-10-09
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0009"
down_revision: str | Sequence[str] | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

VERSIONED = (
    "content.modules, content.taxonomy_nodes, content.rubrics, content.contexts, content.items,"
    " content.item_versions, content.item_version_stats"
)
APPEND_ONLY = (
    "content.item_events, content.context_versions, content.media, content.exports,"
    " content.taxonomy_changes, content.seed_loads"
)
IMPORT_MUTABLE = "status, payload, target_state, originality_declared, confirmed_at, result"

UPGRADE = [
    "GRANT USAGE ON SCHEMA content TO saber_app",
    f"GRANT SELECT, INSERT, UPDATE ON {VERSIONED} TO saber_app",
    "GRANT DELETE ON content.taxonomy_nodes, content.item_version_stats TO saber_app",
    f"GRANT SELECT, INSERT ON {APPEND_ONLY} TO saber_app",
    "GRANT SELECT, INSERT ON content.imports TO saber_app",
    f"GRANT UPDATE ({IMPORT_MUTABLE}) ON content.imports TO saber_app",
]

DOWNGRADE = [
    "REVOKE ALL ON ALL TABLES IN SCHEMA content FROM saber_app",
    "REVOKE USAGE ON SCHEMA content FROM saber_app",
]


def upgrade() -> None:
    for statement in UPGRADE:
        op.execute(statement)


def downgrade() -> None:
    for statement in DOWNGRADE:
        op.execute(statement)
