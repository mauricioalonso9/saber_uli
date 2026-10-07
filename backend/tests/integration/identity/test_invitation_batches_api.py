"""T125: API de lotes de invitaciones (FR-009; escenario 5.2; SC-005)."""

from datetime import UTC, datetime, timedelta

import httpx
from sqlalchemy import text

from saber_uli.identity.domain.roles import Role
from tests.integration.identity.guests import Guests
from tests.integration.identity.staff import Staff, StaffFactory

BATCHES = "/api/v1/invitation-batches"


def problem_type(response: httpx.Response) -> str:
    assert response.headers["content-type"].startswith("application/problem+json"), response.text
    value: str = response.json()["type"]
    return value.removeprefix("urn:saber-uli:problem:")


async def upload_csv(client: httpx.AsyncClient, who: Staff, content: str) -> httpx.Response:
    return await client.post(
        BATCHES,
        content=content.encode("utf-8"),
        headers={**who.headers, "Content-Type": "text/csv"},
    )


def csv_for(guests: Guests, *, valid: int = 2) -> tuple[str, list[str]]:
    emails = [guests.new_email() for _ in range(valid)]
    lines = ["correo,nombre,vence"]
    lines += [f"{email},Persona {i}," for i, email in enumerate(emails)]
    lines += [
        "no-es-correo,,",
        f"{emails[0].upper()},,",  # duplicado en el archivo
        "ana@unilibre.edu.co,,",
    ]
    return "\n".join(lines) + "\n", emails


async def test_validar_un_csv_devuelve_el_reporte_por_fila(
    api_client: httpx.AsyncClient, staff: StaffFactory, guests: Guests
) -> None:
    teacher = await staff(Role.TEACHER)
    content, _ = csv_for(guests)

    response = await upload_csv(api_client, teacher, content)

    assert response.status_code == 201, response.text
    batch = response.json()
    assert batch["status"] == "pending_confirmation"
    assert (batch["valid_count"], batch["invalid_count"]) == (2, 3)
    assert [row["result"] for row in batch["rows"]] == [
        "valid",
        "valid",
        "invalid_email",
        "duplicate_in_file",
        "institutional_email",
    ]
    assert [row["line"] for row in batch["rows"]] == [2, 3, 4, 5, 6]
    expires = datetime.fromisoformat(batch["expires_at"])
    assert abs(expires - (datetime.now(UTC) + timedelta(hours=24))) < timedelta(minutes=1)
    assert (
        await api_client.get(f"{BATCHES}/{batch['id']}", headers=teacher.headers)
    ).json() == batch


async def test_el_json_equivalente_da_el_mismo_reporte(
    api_client: httpx.AsyncClient, staff: StaffFactory, guests: Guests
) -> None:
    teacher = await staff(Role.TEACHER)
    email = guests.new_email()

    response = await api_client.post(
        BATCHES,
        json={
            "rows": [
                {"email": email, "name": "Laura"},
                {"email": "no-es-correo"},
                {"email": guests.new_email(), "access_expires_at": "2099-01-01T00:00:00Z"},
            ]
        },
        headers=teacher.headers,
    )

    assert response.status_code == 201, response.text
    assert [row["result"] for row in response.json()["rows"]] == [
        "valid",
        "invalid_email",
        "expiry_out_of_range",
    ]


async def test_confirmar_crea_solo_las_validas_y_encola_sus_correos(
    api_client: httpx.AsyncClient, staff: StaffFactory, guests: Guests
) -> None:
    teacher = await staff(Role.TEACHER)
    content, emails = csv_for(guests)
    batch = (await upload_csv(api_client, teacher, content)).json()

    response = await api_client.post(
        f"{BATCHES}/{batch['id']}/confirmation", headers=teacher.headers
    )

    assert response.status_code == 200, response.text
    confirmed = response.json()
    assert confirmed["status"] == "confirmed"
    assert confirmed["confirmed_at"]
    async with guests.engine.connect() as conn:
        rows = (
            await conn.execute(
                text(
                    "SELECT id, lower(email) AS email, status, invited_by FROM identity.invitations"
                    " WHERE batch_id = :b"
                ),
                {"b": batch["id"]},
            )
        ).all()
        audit = (
            (
                await conn.execute(
                    text("SELECT details FROM identity.audit_events WHERE target_id = :b"),
                    {"b": batch["id"]},
                )
            )
            .scalars()
            .all()
        )
    assert sorted(row.email for row in rows) == sorted(e.lower() for e in emails)
    assert {row.status for row in rows} == {"sent"}
    assert {row.invited_by for row in rows} == {teacher.id}
    for row in rows:
        kinds = [kind for kind, _ in await guests.outbox_events(row.id)]
        assert kinds == ["identity.InvitationCreated"]
    assert audit == [{"created": 2, "rejected": 3}]


async def test_confirmar_dos_veces_o_vencido_responde_409(
    api_client: httpx.AsyncClient, staff: StaffFactory, guests: Guests
) -> None:
    teacher = await staff(Role.TEACHER)
    first = (await upload_csv(api_client, teacher, csv_for(guests)[0])).json()
    second = (await upload_csv(api_client, teacher, csv_for(guests)[0])).json()
    confirm = f"{BATCHES}/{first['id']}/confirmation"
    assert (await api_client.post(confirm, headers=teacher.headers)).status_code == 200
    async with guests.engine.begin() as conn:
        await conn.execute(
            text(
                "UPDATE identity.invitation_batches SET expires_at = now() - interval '1 minute'"
                " WHERE id = :b"
            ),
            {"b": second["id"]},
        )

    twice = await api_client.post(confirm, headers=teacher.headers)
    expired = await api_client.post(
        f"{BATCHES}/{second['id']}/confirmation", headers=teacher.headers
    )

    for response in (twice, expired):
        assert response.status_code == 409
        assert problem_type(response) == "batch-not-pending"


async def test_un_docente_no_ve_lotes_ajenos(
    api_client: httpx.AsyncClient, staff: StaffFactory, guests: Guests
) -> None:
    owner = await staff(Role.TEACHER)
    other = await staff(Role.TEACHER)
    batch = (await upload_csv(api_client, owner, csv_for(guests)[0])).json()

    seen = await api_client.get(f"{BATCHES}/{batch['id']}", headers=other.headers)
    confirmed = await api_client.post(
        f"{BATCHES}/{batch['id']}/confirmation", headers=other.headers
    )

    assert (seen.status_code, confirmed.status_code) == (404, 404)


async def test_mas_de_500_filas_responde_413(
    api_client: httpx.AsyncClient, staff: StaffFactory
) -> None:
    admin = await staff(Role.ADMIN)
    content = "correo,nombre,vence\n" + "".join(f"p{i}@correo.co,,\n" for i in range(501))

    response = await upload_csv(api_client, admin, content)

    assert response.status_code == 413
    assert problem_type(response) == "batch-too-large"


async def test_un_encabezado_distinto_responde_422(
    api_client: httpx.AsyncClient, staff: StaffFactory
) -> None:
    admin = await staff(Role.ADMIN)

    response = await upload_csv(api_client, admin, "email,name\nx@correo.co,X\n")

    assert response.status_code == 422
