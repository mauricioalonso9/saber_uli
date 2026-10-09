"""Datos de invitados para las pruebas de integración de US4.

`guests` siembra invitaciones y enlaces con tokens conocidos (en la base solo queda su hash,
como en producción) y al terminar borra, con saber_migrator, las invitaciones, los usuarios
invitados que se hayan creado y sus eventos del outbox.
"""

from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import NullPool, text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from saber_uli.identity.infrastructure.link_tokens import hash_link_token, new_link_token


@dataclass
class Guests:
    engine: AsyncEngine
    invitations: list[UUID] = field(default_factory=list)
    emails: list[str] = field(default_factory=list)

    def new_email(self) -> str:
        email = f"invitado-{uuid4().hex[:10]}@correo.co"
        self.emails.append(email)
        return email

    async def invitation(
        self,
        invited_by: UUID,
        *,
        email: str | None = None,
        access_days: float = 30,
        status: str = "sent",
        guest_user_id: UUID | None = None,
        revoked: bool = False,
    ) -> tuple[UUID, str]:
        email = email or self.new_email()
        now = datetime.now(UTC)
        async with self.engine.begin() as conn:
            invitation_id = (
                await conn.execute(
                    text(
                        """INSERT INTO identity.invitations
                               (email, invited_by, status, access_expires_at, sent_at,
                                guest_user_id, accepted_at, revoked_at, created_at)
                           VALUES (:email, :by, :status, :expires, :now, :guest, :accepted,
                                   :revoked, :created)
                           RETURNING id"""
                    ),
                    {
                        "email": email,
                        "by": invited_by,
                        "status": status,
                        "expires": now + timedelta(days=access_days),
                        "now": now,
                        "guest": guest_user_id,
                        "accepted": now if guest_user_id else None,
                        "revoked": now if revoked else None,
                        # `access_expires_at > created_at` (CHECK): un acceso ya vencido se
                        # siembra como creado antes.
                        "created": min(now, now + timedelta(days=access_days) - timedelta(days=1)),
                    },
                )
            ).scalar_one()
        self.invitations.append(invitation_id)
        return UUID(str(invitation_id)), email

    async def link(
        self,
        invitation_id: UUID,
        *,
        purpose: str = "invitation",
        minutes: float = 60,
        used: bool = False,
    ) -> str:
        """Siembra un enlace y devuelve el token en claro."""
        plaintext, token_hash = new_link_token()
        now = datetime.now(UTC)
        async with self.engine.begin() as conn:
            await conn.execute(
                text(
                    """INSERT INTO identity.access_links
                           (invitation_id, purpose, token_hash, expires_at, used_at)
                       VALUES (:inv, :purpose, :hash, :expires, :used)"""
                ),
                {
                    "inv": invitation_id,
                    "purpose": purpose,
                    "hash": token_hash,
                    "expires": now + timedelta(minutes=minutes),
                    "used": now if used else None,
                },
            )
        return plaintext

    async def guest_user_id(self, email: str) -> UUID | None:
        async with self.engine.connect() as conn:
            value = (
                await conn.execute(
                    text("SELECT id FROM identity.users WHERE lower(email) = lower(:e)"),
                    {"e": email},
                )
            ).scalar_one_or_none()
        return None if value is None else UUID(str(value))

    async def link_used(self, plaintext: str) -> bool:
        async with self.engine.connect() as conn:
            used = (
                await conn.execute(
                    text("SELECT used_at FROM identity.access_links WHERE token_hash = :h"),
                    {"h": hash_link_token(plaintext)},
                )
            ).scalar_one()
        return used is not None

    async def outbox_events(self, invitation_id: UUID) -> list[tuple[str, dict[str, object]]]:
        async with self.engine.connect() as conn:
            rows = await conn.execute(
                text(
                    """SELECT event_type, payload FROM shared.outbox_events
                       WHERE payload->>'invitation_id' = :id ORDER BY occurred_at"""
                ),
                {"id": str(invitation_id)},
            )
            return [(row.event_type, row.payload) for row in rows]


@pytest.fixture
async def guests(
    app_engine: AsyncEngine, migrated_database: dict[str, str]
) -> AsyncIterator[Guests]:
    world = Guests(app_engine)
    yield world
    engine = create_async_engine(migrated_database["migrator"], poolclass=NullPool)
    async with engine.begin() as conn:
        users = list(
            (
                await conn.execute(
                    text("SELECT id FROM identity.users WHERE lower(email) = ANY(:emails)"),
                    {"emails": [email.lower() for email in world.emails]},
                )
            ).scalars()
        )
        invitations = list(
            (
                await conn.execute(
                    text(
                        "SELECT id FROM identity.invitations WHERE id = ANY(:ids)"
                        " OR lower(email) = ANY(:emails) OR guest_user_id = ANY(:users)"
                    ),
                    {
                        "ids": world.invitations,
                        "emails": [email.lower() for email in world.emails],
                        "users": users,
                    },
                )
            ).scalars()
        )
        for statement, params in (
            (
                "DELETE FROM shared.outbox_events WHERE payload->>'invitation_id' = ANY(:ids)",
                {"ids": [str(i) for i in invitations]},
            ),
            (
                "DELETE FROM identity.audit_events WHERE target_id = ANY(:inv)"
                " OR subject_user_id = ANY(:users)",
                {"inv": invitations, "users": users},
            ),
            ("DELETE FROM identity.invitations WHERE id = ANY(:ids)", {"ids": invitations}),
            ("DELETE FROM identity.consents WHERE user_id = ANY(:ids)", {"ids": users}),
            ("DELETE FROM identity.users WHERE id = ANY(:ids)", {"ids": users}),
        ):
            await conn.execute(text(statement), params)
    await engine.dispose()
