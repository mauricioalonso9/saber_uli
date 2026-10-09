"""identity: semilla de parámetros por defecto (data-model §2.15; research R-29).

Revisión: 0004
Anterior: 0003
Creada: 2026-10-06
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0004"
down_revision: str | Sequence[str] | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Mismos valores por defecto que `identity.domain.settings.IdentitySettings`; una prueba (T056)
# verifica la semilla.
DEFAULTS = {
    "teacher_max_access_days": 180,
    "default_guest_access_days": 90,
    "invitation_link_ttl_days": 7,
    "sign_in_link_ttl_minutes": 15,
}


def upgrade() -> None:
    for key, value in DEFAULTS.items():
        # Si un administrador ya cambió un valor, no se pisa.
        op.execute(
            f"INSERT INTO identity.settings (key, value) VALUES ('{key}', '{value}') "  # noqa: S608
            "ON CONFLICT (key) DO NOTHING"
        )


def downgrade() -> None:
    keys = ", ".join(f"'{key}'" for key in DEFAULTS)
    op.execute(f"DELETE FROM identity.settings WHERE key IN ({keys})")  # noqa: S608
