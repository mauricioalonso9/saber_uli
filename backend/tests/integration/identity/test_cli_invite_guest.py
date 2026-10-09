"""T111: `saber-uli identity invite-guest --email <correo> [--days N] [--name <nombre>]`
(FR-006, FR-008; research R-19, R-20).

Crea la invitación con actor `system` (sin `invited_by`), rechaza los dominios institucionales y
encola `identity.InvitationCreated`; el worker envía el correo.
"""

import os
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import text

from tests.integration.identity.guests import Guests


def invite(url: str, *args: str) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if k != "DATABASE_URL"}
    env["DATABASE_URL"] = url
    env["INSTITUTIONAL_EMAIL_DOMAINS"] = "unilibre.edu.co"
    return subprocess.run(  # noqa: S603 - los argumentos los fija la propia prueba
        [sys.executable, "-m", "saber_uli.cli", "identity", "invite-guest", *args],
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
        timeout=120,
    )


async def invitation_for(guests: Guests, email: str) -> Any:
    async with guests.engine.connect() as conn:
        return (
            await conn.execute(
                text(
                    """SELECT id, status, invited_by, invitee_name, access_expires_at, created_at
                       FROM identity.invitations WHERE lower(email) = lower(:e)"""
                ),
                {"e": email},
            )
        ).one_or_none()


async def test_crea_la_invitacion_con_actor_sistema_y_encola_el_correo(
    migrated_database: dict[str, str], guests: Guests
) -> None:
    email = guests.new_email()

    result = invite(migrated_database["app"], "--email", email, "--days", "30", "--name", "Laura")

    assert result.returncode == 0, result.stderr
    row = await invitation_for(guests, email)
    assert row is not None
    assert row.status == "sent"
    assert row.invited_by is None
    assert row.invitee_name == "Laura"
    span = row.access_expires_at - row.created_at
    assert timedelta(days=30) - timedelta(minutes=1) < span <= timedelta(days=30)
    assert email not in result.stdout + result.stderr  # el correo no se repite en la salida
    assert await guests.outbox_events(row.id) == [
        ("identity.InvitationCreated", {"invitation_id": str(row.id)})
    ]
    async with guests.engine.connect() as conn:
        audit = (
            await conn.execute(
                text("SELECT action, actor_id FROM identity.audit_events WHERE target_id = :id"),
                {"id": row.id},
            )
        ).all()
    assert [(a.action, a.actor_id) for a in audit] == [("invitation.created", None)]


async def test_sin_dias_usa_el_plazo_por_defecto(
    migrated_database: dict[str, str], guests: Guests
) -> None:
    email = guests.new_email()

    result = invite(migrated_database["app"], "--email", email)

    assert result.returncode == 0, result.stderr
    row = await invitation_for(guests, email)
    span = row.access_expires_at - row.created_at
    assert abs(span - timedelta(days=90)) < timedelta(minutes=1)


async def test_rechaza_los_correos_institucionales(
    migrated_database: dict[str, str], guests: Guests
) -> None:
    email = f"x-{datetime.now(UTC).timestamp():.0f}@est.unilibre.edu.co"  # incluye subdominios
    guests.emails.append(email)

    result = invite(migrated_database["app"], "--email", email)

    assert result.returncode == 1
    assert "institucional" in result.stderr.lower()
    assert await invitation_for(guests, email) is None


async def test_no_duplica_una_invitacion_vigente(
    migrated_database: dict[str, str], guests: Guests
) -> None:
    email = guests.new_email()
    assert invite(migrated_database["app"], "--email", email).returncode == 0

    again = invite(migrated_database["app"], "--email", email.upper())

    assert again.returncode == 1
    assert "vigente" in again.stderr.lower()


async def test_datos_de_uso_invalidos(migrated_database: dict[str, str], guests: Guests) -> None:
    url = migrated_database["app"]

    assert invite(url, "--email", "no-es-correo").returncode == 2
    assert invite(url, "--email", guests.new_email(), "--days", "0").returncode == 2
