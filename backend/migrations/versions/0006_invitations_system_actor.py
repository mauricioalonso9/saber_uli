"""identity: invitaciones creadas por el sistema (data-model §2.7; T118).

Revisión: 0006
Anterior: 0005
Creada: 2026-10-07

`invitations.invited_by` admite `NULL` = sistema (comando `saber-uli identity invite-guest`),
igual que `role_assignments.assigned_by`.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0006"
down_revision: str | Sequence[str] | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TABLE identity.invitations ALTER COLUMN invited_by DROP NOT NULL")


def downgrade() -> None:
    # Solo es posible si no quedan invitaciones del sistema.
    op.execute("ALTER TABLE identity.invitations ALTER COLUMN invited_by SET NOT NULL")
