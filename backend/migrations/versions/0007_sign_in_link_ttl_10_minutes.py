"""identity: el enlace de ingreso de invitados vence a los 10 minutos como máximo (T178a).

Revisión: 0007
Anterior: 0006
Creada: 2026-10-08

ASVS 4.0.3 V2.7.2 pide que un código o enlace fuera de banda venza a los 10 minutos. El valor
por defecto pasa de 15 a 10, y el rango admitido de 5 a 60 pasa a 5 a 10
(`identity.domain.settings`). Un valor guardado por encima de 10 se recorta a 10, porque fuera
del rango los parámetros no cargan; uno de 10 o menos que haya elegido un administrador se
conserva.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0007"
down_revision: str | Sequence[str] | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "UPDATE identity.settings SET value = '10'::jsonb, updated_at = now() "
        "WHERE key = 'sign_in_link_ttl_minutes' AND (value #>> '{}')::int > 10"
    )


def downgrade() -> None:
    # No se restaura el valor anterior: 10 minutos también es válido con el rango de 0006.
    pass
