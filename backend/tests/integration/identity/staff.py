"""Personal (docentes y administradores) para las pruebas de API de gestión.

`staff(Role.TEACHER)` crea el usuario con sesión privilegiada y la autorización de datos vigente
(las rutas de `/api/v1` la exigen, FR-014) y devuelve el usuario y las cabeceras.
"""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from uuid import UUID

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from saber_uli.identity.domain.roles import Role
from tests.integration.conftest import CommittedLogin


@dataclass(frozen=True)
class Staff:
    id: UUID
    display_name: str
    headers: dict[str, str]


StaffFactory = Callable[..., Awaitable[Staff]]


async def accept_current_policy(engine: AsyncEngine, user_id: UUID) -> None:
    async with engine.begin() as conn:
        await conn.execute(
            text(
                """INSERT INTO identity.consents (user_id, policy_version_id, decision, channel)
                   SELECT :u, id, 'accepted', 'web_pwa' FROM identity.policy_versions
                   WHERE effective_from <= now()
                   ORDER BY effective_from DESC, created_at DESC LIMIT 1"""
            ),
            {"u": user_id},
        )


@pytest.fixture
def staff(committed_login: CommittedLogin, app_engine: AsyncEngine) -> StaffFactory:
    async def create(*roles: Role, priv: bool = True) -> Staff:
        user, token = await committed_login(*roles, priv=priv)
        assert user.id is not None
        await accept_current_policy(app_engine, user.id)
        return Staff(
            id=user.id,
            display_name=user.display_name or "",
            headers={"Authorization": f"Bearer {token}"},
        )

    return create
