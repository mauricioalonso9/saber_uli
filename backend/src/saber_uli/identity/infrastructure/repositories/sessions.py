"""Repositorio de sesiones y tokens de renovación con SQLAlchemy (data-model §2.13)."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from saber_uli.identity.domain.session import (
    AuthMethod,
    RefreshToken,
    RevocationReason,
    Session,
)
from saber_uli.identity.infrastructure.orm import RefreshTokenRow, SessionRow


def _session_to_domain(row: SessionRow) -> Session:
    return Session(
        id=row.id,
        user_id=row.user_id,
        auth_method=AuthMethod(row.auth_method),
        auth_time=row.auth_time,
        last_seen_at=row.last_seen_at,
        last_privileged_activity_at=row.last_privileged_activity_at,
        absolute_expires_at=row.absolute_expires_at,
        revoked_at=row.revoked_at,
        revoked_reason=row.revoked_reason,
    )


def _copy_session(session: Session, row: SessionRow) -> None:
    row.user_id = session.user_id
    row.auth_method = session.auth_method.value
    row.auth_time = session.auth_time
    row.last_seen_at = session.last_seen_at
    row.last_privileged_activity_at = session.last_privileged_activity_at
    row.absolute_expires_at = session.absolute_expires_at
    row.revoked_at = session.revoked_at
    row.revoked_reason = session.revoked_reason


def _token_to_domain(row: RefreshTokenRow) -> RefreshToken:
    return RefreshToken(
        id=row.id,
        session_id=row.session_id,
        token_hash=row.token_hash,
        issued_at=row.issued_at,
        idle_expires_at=row.idle_expires_at,
        rotated_at=row.rotated_at,
    )


class SqlAlchemySessionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._db = session

    async def add(self, session: Session) -> Session:
        row = SessionRow()
        _copy_session(session, row)
        self._db.add(row)
        await self._db.flush()
        session.id = row.id
        return session

    async def save(self, session: Session) -> None:
        row = await self._db.get(SessionRow, session.id)
        if row is None:
            raise LookupError("la sesión no existe")
        _copy_session(session, row)
        await self._db.flush()

    async def get(self, session_id: UUID) -> Session | None:
        row = await self._db.get(SessionRow, session_id)
        return _session_to_domain(row) if row else None

    async def add_refresh_token(self, token: RefreshToken) -> RefreshToken:
        row = RefreshTokenRow(
            session_id=token.session_id,
            token_hash=token.token_hash,
            issued_at=token.issued_at,
            idle_expires_at=token.idle_expires_at,
            rotated_at=token.rotated_at,
        )
        self._db.add(row)
        await self._db.flush()
        token.id = row.id
        return token

    async def save_refresh_token(self, token: RefreshToken) -> None:
        row = await self._db.get(RefreshTokenRow, token.id)
        if row is None:
            raise LookupError("el token no existe")
        row.rotated_at = token.rotated_at
        await self._db.flush()

    async def get_refresh_token_for_update(self, token_hash: bytes) -> RefreshToken | None:
        """Bloquea el token hasta el fin de la transacción: dos renovaciones simultáneas con el
        mismo token no pueden rotarlo ambas (la segunda ve `rotated_at` y revoca la sesión)."""
        row = await self._db.scalar(
            select(RefreshTokenRow)
            .where(RefreshTokenRow.token_hash == token_hash)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        return _token_to_domain(row) if row else None

    async def revoke_all_for_user(
        self, user_id: UUID, *, now: datetime, reason: RevocationReason
    ) -> int:
        result = await self._db.execute(
            update(SessionRow)
            .where(SessionRow.user_id == user_id, SessionRow.revoked_at.is_(None))
            .values(revoked_at=now, revoked_reason=reason)
            .execution_options(synchronize_session=False)
        )
        return int(getattr(result, "rowcount", 0) or 0)
