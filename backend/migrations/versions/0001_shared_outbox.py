"""shared: outbox transaccional (data-model.md §3.1; research R-08; ADR 0004).

Revisión: 0001
Anterior: ninguna
Creada: 2026-10-06
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UPGRADE = [
    # env.py ya crea `shared` (allí vive alembic_version); IF NOT EXISTS lo hace explícito.
    "CREATE SCHEMA IF NOT EXISTS shared",
    """
    CREATE TABLE shared.outbox_events (
        id            uuid        NOT NULL DEFAULT uuidv7(),
        context       text        NOT NULL,
        event_type    text        NOT NULL,
        payload       jsonb       NOT NULL,
        occurred_at   timestamptz NOT NULL,
        available_at  timestamptz NOT NULL DEFAULT now(),
        attempts      integer     NOT NULL DEFAULT 0,
        processed_at  timestamptz,
        last_error    text,
        CONSTRAINT pk_outbox_events PRIMARY KEY (id),
        -- Solo identificadores en un objeto JSON; la ausencia de datos personales la valida
        -- el escritor del outbox (T032).
        CONSTRAINT ck_outbox_events_payload_object CHECK (jsonb_typeof(payload) = 'object'),
        CONSTRAINT ck_outbox_events_attempts_non_negative CHECK (attempts >= 0)
    )
    """,
    """
    CREATE INDEX ix_outbox_events_pending
        ON shared.outbox_events (available_at)
        WHERE processed_at IS NULL
    """,
]


def upgrade() -> None:
    for statement in UPGRADE:
        op.execute(statement)


def downgrade() -> None:
    # El esquema `shared` se conserva: allí vive alembic_version.
    op.execute("DROP TABLE shared.outbox_events")
