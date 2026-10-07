"""T124: API de invitaciones (FR-006 a FR-010; escenarios 5.1 y 5.3 a 5.8; SC-004).

Todas las operaciones exigen `invitations:manage_own` (docente, solo las suyas) o
`invitations:manage_all` (administrador) y sesión privilegiada.
"""

from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
import pytest
from sqlalchemy import text

from saber_uli.identity.domain.roles import Role
from tests.integration.identity.guests import Guests
from tests.integration.identity.staff import Staff, StaffFactory

INVITATIONS = "/api/v1/invitations"


def problem_type(response: httpx.Response) -> str:
    assert response.headers["content-type"].startswith("application/problem+json"), response.text
    value: str = response.json()["type"]
    return value.removeprefix("urn:saber-uli:problem:")


def in_days(days: float) -> str:
    return (datetime.now(UTC) + timedelta(days=days)).isoformat()


async def invite(client: httpx.AsyncClient, who: Staff, email: str, **body: Any) -> httpx.Response:
    return await client.post(INVITATIONS, json={"email": email, **body}, headers=who.headers)


async def audit_actions(guests: Guests, invitation_id: str) -> list[tuple[str, Any]]:
    async with guests.engine.connect() as conn:
        rows = await conn.execute(
            text(
                "SELECT action, actor_id FROM identity.audit_events WHERE target_id = :id"
                " ORDER BY occurred_at, id"
            ),
            {"id": invitation_id},
        )
        return [(row.action, row.actor_id) for row in rows]


# ------------------------------------------------------------------- crear


async def test_el_docente_invita_y_queda_enviada_auditada_y_encolada(
    api_client: httpx.AsyncClient, staff: StaffFactory, guests: Guests
) -> None:
    teacher = await staff(Role.TEACHER)
    email = guests.new_email()

    response = await invite(api_client, teacher, email, invitee_name="Laura Gómez")

    assert response.status_code == 201, response.text
    body = response.json()
    assert (body["email"], body["invitee_name"], body["status"]) == (email, "Laura Gómez", "sent")
    assert body["invited_by"] == {"id": str(teacher.id), "display_name": teacher.display_name}
    expires = datetime.fromisoformat(body["access_expires_at"])
    assert abs(expires - (datetime.now(UTC) + timedelta(days=90))) < timedelta(minutes=1)
    assert await audit_actions(guests, body["id"]) == [("invitation.created", teacher.id)]
    events = await guests.outbox_events(body["id"])
    assert [kind for kind, _ in events] == ["identity.InvitationCreated"]


async def test_correo_institucional_rechazado(
    api_client: httpx.AsyncClient, staff: StaffFactory
) -> None:
    admin = await staff(Role.ADMIN)

    response = await invite(api_client, admin, "ana@est.unilibre.edu.co")

    assert response.status_code == 422
    assert problem_type(response) == "institutional-email-not-invitable"


async def test_plazo_maximo_del_docente_y_sin_limite_para_el_administrador(
    api_client: httpx.AsyncClient, staff: StaffFactory, guests: Guests
) -> None:
    teacher = await staff(Role.TEACHER)
    admin = await staff(Role.ADMIN)

    rejected = await invite(api_client, teacher, guests.new_email(), access_expires_at=in_days(200))
    accepted = await invite(api_client, admin, guests.new_email(), access_expires_at=in_days(200))

    assert rejected.status_code == 422
    assert problem_type(rejected) == "access-expiry-out-of-range"
    assert "180" in rejected.json()["detail"]
    assert accepted.status_code == 201


async def test_una_invitacion_vigente_al_mismo_correo_responde_409(
    api_client: httpx.AsyncClient, staff: StaffFactory, guests: Guests
) -> None:
    teacher = await staff(Role.TEACHER)
    email = guests.new_email()
    assert (await invite(api_client, teacher, email)).status_code == 201

    again = await invite(api_client, teacher, email.upper())

    assert again.status_code == 409
    assert problem_type(again) == "invitation-already-active"


# ------------------------------------------------------------------- alcance y listado


async def test_el_docente_solo_ve_las_suyas_y_las_ajenas_son_404(
    api_client: httpx.AsyncClient, staff: StaffFactory, guests: Guests
) -> None:
    teacher_a = await staff(Role.TEACHER)
    teacher_b = await staff(Role.TEACHER)
    admin = await staff(Role.ADMIN)
    mine = (await invite(api_client, teacher_a, guests.new_email())).json()
    theirs = (await invite(api_client, teacher_b, guests.new_email())).json()

    listed = await api_client.get(
        INVITATIONS, params={"invited_by": str(teacher_b.id)}, headers=teacher_a.headers
    )
    assert listed.status_code == 200
    ids = {item["id"] for item in listed.json()["items"]}
    assert mine["id"] in ids and theirs["id"] not in ids

    for method, path, body in (
        ("GET", f"{INVITATIONS}/{theirs['id']}", None),
        ("PATCH", f"{INVITATIONS}/{theirs['id']}", {"access_expires_at": in_days(10)}),
        ("POST", f"{INVITATIONS}/{theirs['id']}/resend", None),
        ("POST", f"{INVITATIONS}/{theirs['id']}/revocation", None),
    ):
        response = await api_client.request(method, path, json=body, headers=teacher_a.headers)
        assert response.status_code == 404, (method, path)

    as_admin = await api_client.get(f"{INVITATIONS}/{theirs['id']}", headers=admin.headers)
    assert as_admin.status_code == 200


async def test_el_administrador_filtra_por_estado_correo_y_quien_invito(
    api_client: httpx.AsyncClient, staff: StaffFactory, guests: Guests
) -> None:
    teacher = await staff(Role.TEACHER)
    admin = await staff(Role.ADMIN)
    email = guests.new_email()
    first = (await invite(api_client, teacher, email)).json()
    second = (await invite(api_client, teacher, guests.new_email())).json()
    await api_client.post(f"{INVITATIONS}/{second['id']}/revocation", headers=teacher.headers)

    by_teacher = await api_client.get(
        INVITATIONS,
        params={"invited_by": str(teacher.id), "status": "sent", "page_size": 50},
        headers=admin.headers,
    )
    by_email = await api_client.get(INVITATIONS, params={"q": email[:12]}, headers=admin.headers)

    page = by_teacher.json()
    assert {"page", "page_size", "total", "items"} <= set(page)
    assert [item["id"] for item in page["items"]] == [first["id"]]
    assert page["total"] == 1
    assert first["id"] in {item["id"] for item in by_email.json()["items"]}


# ------------------------------------------------------------------- gestionar


async def test_cambiar_el_vencimiento_dentro_del_plazo(
    api_client: httpx.AsyncClient, staff: StaffFactory, guests: Guests
) -> None:
    teacher = await staff(Role.TEACHER)
    created = (await invite(api_client, teacher, guests.new_email())).json()
    path = f"{INVITATIONS}/{created['id']}"

    ok = await api_client.patch(
        path, json={"access_expires_at": in_days(30)}, headers=teacher.headers
    )
    too_far = await api_client.patch(
        path, json={"access_expires_at": in_days(181)}, headers=teacher.headers
    )

    assert ok.status_code == 200, ok.text
    expires = datetime.fromisoformat(ok.json()["access_expires_at"])
    assert abs(expires - (datetime.now(UTC) + timedelta(days=30))) < timedelta(minutes=1)
    assert too_far.status_code == 422
    actions = [action for action, _ in await audit_actions(guests, created["id"])]
    assert actions == ["invitation.created", "invitation.expiry_changed"]


async def test_reenviar_solo_sin_aceptar(
    api_client: httpx.AsyncClient, staff: StaffFactory, guests: Guests
) -> None:
    teacher = await staff(Role.TEACHER)
    created = (await invite(api_client, teacher, guests.new_email())).json()

    resent = await api_client.post(f"{INVITATIONS}/{created['id']}/resend", headers=teacher.headers)

    assert resent.status_code == 202, resent.text
    assert resent.json()["status"] == "sent"
    kinds = [kind for kind, _ in await guests.outbox_events(created["id"])]
    assert kinds == ["identity.InvitationCreated", "identity.InvitationResent"]

    token = await guests.link(created["id"])
    assert (
        await api_client.post("/api/auth/guest/sessions", json={"token": token})
    ).status_code == 200
    conflict = await api_client.post(
        f"{INVITATIONS}/{created['id']}/resend", headers=teacher.headers
    )
    assert conflict.status_code == 409


async def test_revocar_termina_las_sesiones_abiertas_del_invitado(
    api_client: httpx.AsyncClient, staff: StaffFactory, guests: Guests
) -> None:
    teacher = await staff(Role.TEACHER)
    created = (await invite(api_client, teacher, guests.new_email())).json()
    session = await api_client.post(
        "/api/auth/guest/sessions", json={"token": await guests.link(created["id"])}
    )
    guest_headers = {"Authorization": f"Bearer {session.json()['access_token']}"}
    assert (await api_client.get("/api/v1/me", headers=guest_headers)).status_code == 200

    revoked = await api_client.post(
        f"{INVITATIONS}/{created['id']}/revocation", headers=teacher.headers
    )

    assert revoked.status_code == 200, revoked.text
    assert revoked.json()["status"] == "revoked"
    after = await api_client.get("/api/v1/me", headers=guest_headers)
    assert after.status_code == 401
    assert problem_type(after) == "guest-access-revoked"
    assert ("invitation.revoked", teacher.id) in await audit_actions(guests, created["id"])
    again = await api_client.post(
        f"{INVITATIONS}/{created['id']}/revocation", headers=teacher.headers
    )
    assert again.status_code == 409


# ------------------------------------------------------------------- permisos


async def test_un_estudiante_no_gestiona_invitaciones(
    api_client: httpx.AsyncClient, staff: StaffFactory
) -> None:
    student = await staff(Role.STUDENT, priv=True)

    response = await api_client.get(INVITATIONS, headers=student.headers)

    assert response.status_code == 403


@pytest.mark.parametrize("method", ["GET", "POST"])
async def test_exige_sesion_privilegiada(
    api_client: httpx.AsyncClient, staff: StaffFactory, guests: Guests, method: str
) -> None:
    teacher = await staff(Role.TEACHER, priv=False)

    response = await api_client.request(
        method, INVITATIONS, json={"email": guests.new_email()}, headers=teacher.headers
    )

    assert response.status_code == 401
    assert problem_type(response) == "reauthentication-required"
