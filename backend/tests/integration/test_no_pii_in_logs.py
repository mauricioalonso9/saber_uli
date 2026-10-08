"""T175: los registros no contienen datos personales (principio V, FR-036; quickstart V21).

Ejecuta, sobre la app ASGI completa y los manejadores del worker en el mismo proceso, los flujos
de US1 a US8 con correos, nombres y tokens únicos, capturando todos los logs (structlog y la
librería estándar, nivel DEBUG). Al final ninguno de esos valores aparece en los registros.

Los flujos: sesión con token (US1), autorización de datos (US2), perfil (US3), invitación y
enlace del invitado con su cookie de renovación (US4, US5, con el correo enviado a Mailpit),
roles y grupos (US6), aviso de conservación, solicitud de supresión y borrado (US7) y
exportación de mis datos (US8).
"""

import asyncio
import io
import re
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from saber_uli.identity.application.erase_user import EraseUser
from saber_uli.identity.domain.roles import Role
from saber_uli.identity.infrastructure.handlers.link_emails import LinkEmailHandlers
from saber_uli.identity.infrastructure.handlers.retention_notice import RetentionNoticeHandler
from saber_uli.identity.infrastructure.link_tokens import LinkTokenFactory
from saber_uli.identity.infrastructure.outbox_events import register_identity_outbox
from saber_uli.identity.infrastructure.tasks import process_deletion_requests, process_retention
from saber_uli.identity.infrastructure.unit_of_work import SqlAlchemyIdentityUnitOfWork
from saber_uli.main import create_app
from saber_uli.notifications.application.public import EmailService
from saber_uli.notifications.infrastructure.smtp import SmtpEmailSender
from saber_uli.notifications.infrastructure.templates import JinjaTemplateRenderer
from saber_uli.shared.application.event_bus import EventBus
from saber_uli.shared.domain.clock import SystemClock
from saber_uli.shared.infrastructure.db import create_session_factory
from saber_uli.shared.infrastructure.outbox import OutboxMessage
from tests.integration.conftest import CommittedLogin, settings_for
from tests.integration.identity.guests import Guests, guests

__all__ = ["guests"]  # fixture de identity, también para esta prueba transversal

XRW = {"X-Requested-With": "saber-uli"}
LINK = re.compile(r"/acceso#t=([A-Za-z0-9_-]{43})")
EMAIL = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9\-]+(\.[A-Za-z0-9\-]+)*\.[A-Za-z]{2,}")


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def sql(engine: AsyncEngine, statement: str, **params: Any) -> Any:
    async with engine.begin() as conn:
        result = await conn.execute(text(statement), params)
        return result.scalar_one_or_none() if result.returns_rows else None


async def latest_mail(api: str, address: str) -> dict[str, Any]:
    """Último correo para `address` en Mailpit (espera hasta 10 s a que llegue)."""
    async with httpx.AsyncClient(base_url=api, timeout=5) as mailpit:
        for _ in range(50):
            found = (
                await mailpit.get("/api/v1/search", params={"query": f'to:"{address}"'})
            ).json()["messages"]
            if found:
                message: dict[str, Any] = (
                    await mailpit.get(f"/api/v1/message/{found[0]['ID']}")
                ).json()
                return message
            await asyncio.sleep(0.2)
    raise AssertionError("no llegó el correo")


async def outbox(engine: AsyncEngine, event_type: str, key: str, value: str) -> OutboxMessage:
    async with engine.connect() as conn:
        row = (
            await conn.execute(
                text(
                    f"""SELECT id, event_type, context, payload, occurred_at
                        FROM shared.outbox_events
                        WHERE event_type = :t AND payload->>'{key}' = :v
                        ORDER BY occurred_at DESC LIMIT 1"""  # noqa: S608 - clave fija
                ),
                {"t": event_type, "v": value},
            )
        ).one()
    return OutboxMessage(
        event_id=row.id,
        event_type=row.event_type,
        context=row.context,
        payload=row.payload,
        occurred_at=row.occurred_at,
        attempt=1,
    )


async def test_ningun_flujo_deja_datos_personales_en_los_registros(
    migrated_database: dict[str, str],
    redis_url: str,
    redis_client: Any,
    committed_login: CommittedLogin,
    guests: Guests,
    app_engine: AsyncEngine,
    mailpit: tuple[str, int, str],
) -> None:
    logs = io.StringIO()
    settings = settings_for(migrated_database, redis_url).model_copy(update={"log_level": "DEBUG"})
    app = create_app(settings, log_stream=logs)
    secrets_seen: list[str] = []

    # Personas con nombres únicos (los correos ya lo son).
    admin, admin_token = await committed_login(Role.ADMIN, priv=True)
    student, student_token = await committed_login()
    assert admin.id and student.id and admin.email and student.email
    student_name = f"Estudiante Registro {uuid4().hex[:8]}"
    await sql(
        app_engine,
        "UPDATE identity.users SET display_name = :n WHERE id = :u",
        n=student_name,
        u=student.id,
    )
    policy_id = await sql(
        app_engine,
        """SELECT id FROM identity.policy_versions WHERE effective_from <= now()
           ORDER BY effective_from DESC LIMIT 1""",
    )
    secrets_seen += [admin.email, student.email, student_name, admin_token, student_token]

    session_factory = create_session_factory(app_engine)
    bus = EventBus()
    register_identity_outbox(bus)

    def uow() -> SqlAlchemyIdentityUnitOfWork:
        return SqlAlchemyIdentityUnitOfWork(session_factory, bus)

    host, port, api = mailpit
    email = EmailService(
        renderer=JinjaTemplateRenderer(public_base_url="http://localhost"),
        sender=SmtpEmailSender(
            host=host, port=port, sender="Saber Uli <no-responder@unilibre.edu.co>", starttls=False
        ),
    )

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        admin_h, student_h = bearer(admin_token), bearer(student_token)

        # US1, US2 y US3: sesión, autorización de datos y perfil.
        assert (await client.get("/api/v1/me", headers=student_h)).status_code == 200
        decided = await client.post(
            "/api/v1/me/consents",
            json={"policy_version_id": str(policy_id), "decision": "accepted"},
            headers=student_h,
        )
        assert decided.status_code == 201, decided.text
        await sql(
            app_engine,
            """INSERT INTO identity.consents (user_id, policy_version_id, decision, channel)
               VALUES (:u, :p, 'accepted', 'web_pwa')""",
            u=admin.id,
            p=policy_id,
        )
        assert (await client.get("/api/v1/me/profile", headers=student_h)).status_code == 200
        # Peticiones rechazadas con datos personales en el cuerpo y un token falso.
        await client.get("/api/v1/me", headers=bearer("token-falso-" + uuid4().hex))
        await client.post("/api/auth/guest/link-requests", json={"email": student.email})

        # US5 y US4: invitación, correo con el enlace, ingreso del invitado y renovación.
        guest_email = guests.new_email()
        guest_name = f"Invitada Registro {uuid4().hex[:8]}"
        secrets_seen += [guest_email, guest_name]
        created = await client.post(
            "/api/v1/invitations",
            json={"email": guest_email, "invitee_name": guest_name},
            headers=admin_h,
        )
        assert created.status_code == 201, created.text
        invitation_id = created.json()["id"]
        handlers = LinkEmailHandlers(
            uow_factory=uow, email=email, clock=SystemClock(), tokens=LinkTokenFactory()
        )
        await handlers.on_invitation_created(
            await outbox(app_engine, "identity.InvitationCreated", "invitation_id", invitation_id)
        )
        mail = await latest_mail(api, guest_email)
        match = LINK.search(mail["Text"])
        assert match, "el correo no trae el enlace"
        link_token = match.group(1)
        secrets_seen.append(link_token)

        session = await client.post("/api/auth/guest/sessions", json={"token": link_token})
        assert session.status_code == 200, session.text
        guest_token = session.json()["access_token"]
        cookie = session.headers["set-cookie"].split(";", 1)[0]
        secrets_seen += [guest_token, cookie.split("=", 1)[1]]
        renewed = await client.post("/api/auth/refresh", headers={**XRW, "Cookie": cookie})
        assert renewed.status_code == 200, renewed.text
        secrets_seen.append(renewed.json()["access_token"])
        guest_h = bearer(guest_token)
        guest_id = UUID(str((await client.get("/api/v1/me", headers=guest_h)).json()["id"]))
        await client.post(
            "/api/v1/me/consents",
            json={"policy_version_id": str(policy_id), "decision": "accepted"},
            headers=guest_h,
        )
        profile = await client.put(
            "/api/v1/me/profile",
            json={"daily_goal": "casual", "guest_display_name": guest_name},
            headers=guest_h,
        )
        assert profile.status_code == 200, profile.text

        # US6: roles, búsqueda de cuentas por nombre y correo, y grupos.
        roles = await client.put(
            f"/api/v1/admin/users/{student.id}/roles",
            json={"roles": ["student", "teacher"], "director_program_ids": []},
            headers=admin_h,
        )
        assert roles.status_code == 200, roles.text
        for q in (student_name, student.email):
            await client.get("/api/v1/admin/users", params={"q": q}, headers=admin_h)
        group = await client.post(
            "/api/v1/admin/groups", json={"name": f"Grupo {student_name}"}, headers=admin_h
        )
        assert group.status_code == 201, group.text
        await client.post(
            f"/api/v1/admin/groups/{group.json()['id']}/members",
            json={"user_ids": [str(guest_id)]},
            headers=admin_h,
        )

        # US8: exportación de mis datos.
        assert (await client.get("/api/v1/me/data-export", headers=guest_h)).status_code == 200

        # US7: supresión voluntaria procesada por el worker.
        deletion = await client.post(
            "/api/v1/me/deletion-request", json={"confirmation": "ELIMINAR"}, headers=guest_h
        )
        assert deletion.status_code == 202, deletion.text

    await EraseUser(uow_factory=uow, clock=SystemClock()).execute(UUID(deletion.json()["id"]))
    await process_deletion_requests(uow_factory=uow, clock=SystemClock())

    # US7: aviso de conservación por correo (institucional sin ingresar hace 340 días).
    await sql(
        app_engine,
        "UPDATE identity.users SET last_login_at = :t WHERE id = :u",
        t=datetime.now(UTC) - timedelta(days=340),
        u=student.id,
    )
    await process_retention(uow_factory=uow, clock=SystemClock())
    await RetentionNoticeHandler(uow_factory=uow, email=email, clock=SystemClock()).on_notice_due(
        await outbox(app_engine, "identity.RetentionNoticeDue", "user_id", str(student.id))
    )

    captured = logs.getvalue()
    # Hubo registros de todos los frentes (la prueba no pasa por no registrar nada).
    for expected in ("http_request", "email_sent", "deletion_completed", "retention_processed"):
        assert f'"{expected}"' in captured, expected
    # Se informa la posición, no el valor: la salida de la prueba tampoco debe mostrarlos.
    leaked = [index for index, value in enumerate(secrets_seen) if value and value in captured]
    assert leaked == [], f"datos personales o tokens en los registros (posiciones {leaked})"
    assert not EMAIL.search(captured), "un correo en los registros"
