"""T053: escritura de auditoría (FR-035, SC-004; research R-24; data-model §2.14 y §5)."""

import re
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

import pytest
from sqlalchemy import NullPool, text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from saber_uli.identity.application.audit import (
    AuditAction,
    AuditTarget,
    PersonalDataInAuditError,
    record_audit,
)
from saber_uli.identity.infrastructure.unit_of_work import SqlAlchemyIdentityUnitOfWork
from saber_uli.shared.application.event_bus import EventBus
from saber_uli.shared.infrastructure.db import create_session_factory
from tests.integration.conftest import REPO

NOW = datetime(2026, 10, 6, 12, 0, tzinfo=UTC)
DATA_MODEL = REPO / "specs" / "001-identidad-acceso" / "data-model.md"


def test_el_catalogo_coincide_con_data_model() -> None:
    section = DATA_MODEL.read_text(encoding="utf-8").split("## 5. Catálogo de acciones auditadas")[
        1
    ]
    section = section.split("\n## ")[0]
    catalog = set(re.findall(r"`([a-z_]+\.[a-z_]+)`", section))

    assert catalog == {action.value for action in AuditAction}


@pytest.fixture
async def target_ids(migrated_database: dict[str, str]) -> AsyncIterator[list[UUID]]:
    ids: list[UUID] = []
    yield ids
    engine = create_async_engine(migrated_database["migrator"], poolclass=NullPool)
    async with engine.begin() as conn:
        await conn.execute(
            text("DELETE FROM identity.audit_events WHERE target_id = ANY(:ids)"), {"ids": ids}
        )
    await engine.dispose()


@pytest.fixture
def uow_factory(app_engine: AsyncEngine) -> Any:
    factory = create_session_factory(app_engine)
    return lambda: SqlAlchemyIdentityUnitOfWork(factory, EventBus())


async def rows(engine: AsyncEngine, target_id: UUID) -> list[Any]:
    async with engine.connect() as conn:
        result = await conn.execute(
            text(
                """SELECT action, target_type, actor_id, subject_user_id, details, occurred_at
                   FROM identity.audit_events WHERE target_id = :t"""
            ),
            {"t": target_id},
        )
        return list(result.all())


async def test_se_confirma_con_la_accion(
    uow_factory: Any, app_engine: AsyncEngine, target_ids: list[UUID]
) -> None:
    target, actor = uuid4(), uuid4()
    target_ids.append(target)

    async with uow_factory() as uow:
        await record_audit(
            uow,
            AuditAction.USER_ROLE_GRANTED,
            target=AuditTarget.USER,
            target_id=target,
            subject_user_id=target,
            actor_id=actor,
            details={"roles_before": ["student"], "roles_after": ["student", "teacher"]},
            now=NOW,
        )
        await uow.commit()

    [row] = await rows(app_engine, target)
    assert row.action == "user.role_granted"
    assert row.target_type == "user"
    assert (row.actor_id, row.subject_user_id) == (actor, target)
    assert row.details == {"roles_before": ["student"], "roles_after": ["student", "teacher"]}
    assert row.occurred_at == NOW


async def test_si_la_accion_se_revierte_no_queda_auditoria(
    uow_factory: Any, app_engine: AsyncEngine, target_ids: list[UUID]
) -> None:
    target = uuid4()
    target_ids.append(target)

    with pytest.raises(RuntimeError):
        async with uow_factory() as uow:
            await record_audit(
                uow, AuditAction.USER_DISABLED, target=AuditTarget.USER, target_id=target, now=NOW
            )
            raise RuntimeError("la acción falló")

    assert await rows(app_engine, target) == []


async def test_actor_nulo_es_el_sistema(
    uow_factory: Any, app_engine: AsyncEngine, target_ids: list[UUID]
) -> None:
    target = uuid4()
    target_ids.append(target)

    async with uow_factory() as uow:
        await record_audit(
            uow,
            AuditAction.RETENTION_NOTICE_SENT,
            target=AuditTarget.USER,
            target_id=target,
            subject_user_id=target,
            now=NOW,
        )
        await uow.commit()

    [row] = await rows(app_engine, target)
    assert row.actor_id is None
    assert row.details == {}


def test_la_accion_debe_ser_del_catalogo() -> None:
    with pytest.raises(ValueError):
        AuditAction("user.hacked")


@pytest.mark.parametrize(
    "details",
    [
        {"email": "x"},
        {"Name": "Ana"},
        {"display_name": "Ana"},
        {"cambios": {"correo_anterior": "ana@unilibre.edu.co"}},
        {"invitados": ["ana@unilibre.edu.co"]},
        {"nota": "enviado a ana@unilibre.edu.co"},
    ],
)
async def test_rechaza_datos_personales_en_details(
    uow_factory: Any, app_engine: AsyncEngine, target_ids: list[UUID], details: dict[str, Any]
) -> None:
    target = uuid4()
    target_ids.append(target)

    with pytest.raises(PersonalDataInAuditError):
        async with uow_factory() as uow:
            await record_audit(
                uow,
                AuditAction.INVITATION_CREATED,
                target=AuditTarget.INVITATION,
                target_id=target,
                details=details,
                now=NOW,
            )
            await uow.commit()

    assert await rows(app_engine, target) == []
