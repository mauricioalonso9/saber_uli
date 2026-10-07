"""Programas para las pruebas de administración (`new_program`)."""

from collections.abc import AsyncIterator, Awaitable, Callable
from uuid import UUID, uuid4

import pytest
from sqlalchemy import NullPool, text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

ProgramFactory = Callable[..., Awaitable[UUID]]


@pytest.fixture
async def new_program(
    app_engine: AsyncEngine, migrated_database: dict[str, str]
) -> AsyncIterator[ProgramFactory]:
    created: list[UUID] = []

    async def create(*, name: str = "Derecho", active: bool = True) -> UUID:
        async with app_engine.begin() as conn:
            program_id = (
                await conn.execute(
                    text(
                        """INSERT INTO identity.programs (code, name, campus, active)
                           VALUES (:code, :name, 'Bogotá', :active) RETURNING id"""
                    ),
                    {"code": f"T-{uuid4().hex[:8].upper()}", "name": name, "active": active},
                )
            ).scalar_one()
        created.append(UUID(str(program_id)))
        return UUID(str(program_id))

    yield create
    engine = create_async_engine(migrated_database["migrator"], poolclass=NullPool)
    async with engine.begin() as conn:
        for statement in (
            "DELETE FROM identity.director_programs WHERE program_id = ANY(:ids)",
            "UPDATE identity.groups SET program_id = NULL WHERE program_id = ANY(:ids)",
            "DELETE FROM identity.profiles WHERE program_id = ANY(:ids)",
            "DELETE FROM identity.audit_events WHERE target_id = ANY(:ids)",
            "DELETE FROM identity.programs WHERE id = ANY(:ids)",
        ):
            await conn.execute(text(statement), {"ids": created})
    await engine.dispose()
