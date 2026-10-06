"""T046: repositorio de sesiones y tokens de renovación (data-model §2.13)."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from saber_uli.identity.domain.session import AuthMethod, RefreshToken, Session
from saber_uli.identity.infrastructure.repositories.sessions import SqlAlchemySessionRepository
from saber_uli.identity.infrastructure.tokens import new_refresh_token
from tests.integration.conftest import UserFactory

NOW = datetime(2026, 10, 6, 12, 0, tzinfo=UTC)


@pytest.fixture
def repo(db_session: AsyncSession) -> SqlAlchemySessionRepository:
    return SqlAlchemySessionRepository(db_session)


async def test_guardar_y_leer_una_sesion(
    repo: SqlAlchemySessionRepository, user_factory: UserFactory
) -> None:
    user = await user_factory()
    assert user.id is not None

    session = await repo.add(Session.start(user.id, AuthMethod.ENTRA_ID, NOW))
    assert session.id is not None
    loaded = await repo.get(session.id)

    assert loaded is not None
    assert (loaded.user_id, loaded.auth_method, loaded.auth_time) == (
        user.id,
        AuthMethod.ENTRA_ID,
        NOW,
    )
    assert loaded.last_privileged_activity_at == NOW
    assert loaded.absolute_expires_at == NOW + timedelta(days=30)


async def test_tokens_por_hash_rotacion_y_revocacion(
    repo: SqlAlchemySessionRepository, user_factory: UserFactory
) -> None:
    user = await user_factory()
    assert user.id is not None
    session = await repo.add(Session.start(user.id, AuthMethod.GUEST_LINK, NOW))
    _, token_hash = new_refresh_token()
    token = await repo.add_refresh_token(
        RefreshToken.issue(session, token_hash=token_hash, now=NOW)
    )

    found = await repo.get_refresh_token_for_update(token_hash)
    assert found is not None
    assert found.id == token.id
    assert found.idle_expires_at == NOW + timedelta(days=7)

    found.rotated_at = NOW + timedelta(minutes=5)
    await repo.save_refresh_token(found)
    session.revoke(NOW + timedelta(minutes=6), "token_reuse")
    await repo.save(session)

    again = await repo.get_refresh_token_for_update(token_hash)
    reloaded = await repo.get(session.id)  # type: ignore[arg-type]
    assert again is not None and again.rotated_at == NOW + timedelta(minutes=5)
    assert reloaded is not None and reloaded.revoked_reason == "token_reuse"
    assert await repo.get_refresh_token_for_update(b"\x00" * 32) is None


async def test_revocar_todas_las_sesiones_de_un_usuario(
    repo: SqlAlchemySessionRepository, user_factory: UserFactory
) -> None:
    user = await user_factory()
    other = await user_factory()
    assert user.id is not None and other.id is not None
    for _ in range(2):
        await repo.add(Session.start(user.id, AuthMethod.ENTRA_ID, NOW))
    already = await repo.add(Session.start(user.id, AuthMethod.ENTRA_ID, NOW))
    already.revoke(NOW, "logout")
    await repo.save(already)
    other_session = await repo.add(Session.start(other.id, AuthMethod.ENTRA_ID, NOW))

    revoked = await repo.revoke_all_for_user(
        user.id, now=NOW + timedelta(hours=1), reason="access_changed"
    )

    assert revoked == 2
    untouched = await repo.get(other_session.id)  # type: ignore[arg-type]
    assert untouched is not None and untouched.revoked_at is None
    kept = await repo.get(already.id)  # type: ignore[arg-type]
    assert kept is not None and kept.revoked_reason == "logout"


async def test_el_token_queda_bloqueado_durante_la_renovacion(app_engine: AsyncEngine) -> None:
    # El bloqueo se ve entre conexiones, así que los datos se confirman (y se limpian al final;
    # saber_app no borra usuarios: se dejan como lápida).
    async with AsyncSession(app_engine, expire_on_commit=False) as first:
        user_id = (
            await first.execute(
                text("INSERT INTO identity.users (kind, email) VALUES ('guest', :e) RETURNING id"),
                {"e": "bloqueo@correo.co"},
            )
        ).scalar_one()
        repo = SqlAlchemySessionRepository(first)
        session = await repo.add(Session.start(user_id, AuthMethod.GUEST_LINK, NOW))
        _, token_hash = new_refresh_token()
        await repo.add_refresh_token(RefreshToken.issue(session, token_hash=token_hash, now=NOW))
        await first.commit()

        try:
            assert await repo.get_refresh_token_for_update(token_hash) is not None
            async with app_engine.connect() as second:
                with pytest.raises(DBAPIError, match="could not obtain lock"):
                    await second.execute(
                        text(
                            """SELECT id FROM identity.refresh_tokens WHERE token_hash = :h
                               FOR UPDATE NOWAIT"""
                        ),
                        {"h": token_hash},
                    )
            await first.rollback()
        finally:
            async with app_engine.begin() as cleanup:
                await cleanup.execute(
                    text("DELETE FROM identity.sessions WHERE user_id = :u"), {"u": user_id}
                )
                await cleanup.execute(
                    text(
                        "UPDATE identity.users SET status = 'deleted', email = NULL WHERE id = :u"
                    ),
                    {"u": user_id},
                )
