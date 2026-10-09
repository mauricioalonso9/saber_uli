"""T141: `saber-uli identity grant-admin --email <correo>` (research R-28).

El primer administrador se asigna por terminal sobre un institucional que ya ingresó una vez;
queda auditado con actor `system` (sin `actor_id`).
"""

import os
import subprocess
import sys

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from saber_uli.identity.domain.roles import Role
from tests.integration.conftest import CommittedLogin


def grant(url: str, email: str) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if k != "DATABASE_URL"}
    env["DATABASE_URL"] = url
    return subprocess.run(  # noqa: S603 - los argumentos los fija la propia prueba
        [sys.executable, "-m", "saber_uli.cli", "identity", "grant-admin", "--email", email],
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
        timeout=120,
    )


async def test_asigna_el_rol_administrador_y_lo_audita_con_actor_sistema(
    migrated_database: dict[str, str], committed_login: CommittedLogin, app_engine: AsyncEngine
) -> None:
    user, _ = await committed_login()

    result = grant(migrated_database["app"], user.email.upper())  # type: ignore[union-attr]

    assert result.returncode == 0, result.stderr
    async with app_engine.connect() as conn:
        roles = set(
            (
                await conn.execute(
                    text("SELECT role FROM identity.role_assignments WHERE user_id = :u"),
                    {"u": user.id},
                )
            ).scalars()
        )
        audit = (
            await conn.execute(
                text(
                    "SELECT action, actor_id, details FROM identity.audit_events"
                    " WHERE subject_user_id = :u"
                ),
                {"u": user.id},
            )
        ).all()
    assert roles == {Role.STUDENT.value, Role.ADMIN.value}
    assert [(a.action, a.actor_id) for a in audit] == [("user.role_granted", None)]
    assert audit[0].details["roles"] == ["admin"]

    again = grant(migrated_database["app"], user.email)  # type: ignore[arg-type]
    assert again.returncode == 0
    assert "ya" in again.stdout.lower()


def test_un_correo_que_no_ingreso_nunca_da_un_mensaje_claro(
    migrated_database: dict[str, str],
) -> None:
    result = grant(migrated_database["app"], "nadie@unilibre.edu.co")

    assert result.returncode == 1
    assert "ingresar" in result.stderr.lower()


async def test_un_invitado_no_puede_ser_administrador(
    migrated_database: dict[str, str], committed_login: CommittedLogin
) -> None:
    guest, _ = await committed_login(guest=True)

    result = grant(migrated_database["app"], guest.email)  # type: ignore[arg-type]

    assert result.returncode == 1
    assert "institucional" in result.stderr.lower()
