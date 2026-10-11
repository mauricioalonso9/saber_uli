"""Fixtures de integración de `content`.

- `clean_content` (automática): deja el esquema `content` vacío antes de cada prueba, con
  `saber_migrator`, porque los casos de uso confirman sus propias transacciones.
- `content_uow`: fábrica de unidades de trabajo de `content` sobre la base migrada.
- `lc_taxonomy`: módulo LC con una competencia, dos afirmaciones, evidencias y un tipo de texto.
- `staff` (de `identity`): docentes y administradores con sesión privilegiada y autorización.
"""

from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import NullPool, text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from saber_uli.content.application.unit_of_work import ContentUnitOfWork
from saber_uli.content.domain.module import Module, QuestionType
from saber_uli.content.domain.taxonomy import TaxonomyNode, TaxonomyNodeKind
from saber_uli.content.infrastructure.unit_of_work import SqlAlchemyContentUnitOfWork
from saber_uli.shared.application.event_bus import EventBus
from saber_uli.shared.infrastructure.db import create_session_factory
from tests.integration.identity.staff import staff

__all__ = ["staff"]

CONTENT_TABLES = (
    "item_version_stats, item_events, item_versions, items, context_versions, contexts, media,"
    " imports, exports, taxonomy_changes, seed_loads, rubrics, taxonomy_nodes, modules"
)


@pytest.fixture(autouse=True)
async def clean_content(migrated_database: dict[str, str]) -> AsyncIterator[None]:
    engine = create_async_engine(migrated_database["migrator"], poolclass=NullPool)
    async with engine.begin() as conn:
        await conn.execute(text("UPDATE content.contexts SET current_version_id = NULL"))
        await conn.execute(
            text(
                "TRUNCATE "
                + ", ".join(f"content.{t.strip()}" for t in CONTENT_TABLES.split(","))
                + " CASCADE"
            )
        )
    await engine.dispose()
    yield


UowFactory = Callable[[], ContentUnitOfWork]


@pytest.fixture
def content_uow(app_engine: AsyncEngine) -> UowFactory:
    factory = create_session_factory(app_engine)
    return lambda: SqlAlchemyContentUnitOfWork(factory, EventBus())


LC_MODULE = Module(
    code="LC",
    name="Lectura crítica",
    question_type=QuestionType.SELECTION,
    options_per_item=4,
    max_context_words=500,
    exam_questions=30,
    bank_target=150,
    position=1,
)


@dataclass
class LcTaxonomy:
    competence: TaxonomyNode
    assertion: TaxonomyNode
    evidence: TaxonomyNode
    other_assertion: TaxonomyNode
    text_type: TaxonomyNode


@pytest.fixture
async def lc_taxonomy(content_uow: UowFactory) -> LcTaxonomy:
    K = TaxonomyNodeKind
    competence = TaxonomyNode(uuid4(), "LC", K.COMPETENCE, "LC-C1", "Comprensión", 1)
    assertion = TaxonomyNode(
        uuid4(),
        "LC",
        K.ASSERTION,
        "LC-A1",
        "Contenidos locales",
        1,
        parent_id=competence.id,
        target_weight=Decimal("0.26"),
    )
    evidence = TaxonomyNode(
        uuid4(), "LC", K.EVIDENCE, "LC-E1.1", "Significado", 1, parent_id=assertion.id
    )
    other = TaxonomyNode(
        uuid4(),
        "LC",
        K.ASSERTION,
        "LC-A2",
        "Sentido global",
        2,
        parent_id=competence.id,
        target_weight=Decimal("0.40"),
    )
    text_type = TaxonomyNode(uuid4(), "LC", K.TEXT_TYPE, "continuo_informativo", "Continuo", 1)
    async with content_uow() as uow:
        await uow.modules.add(LC_MODULE)
        for node in (competence, assertion, evidence, other, text_type):
            await uow.taxonomy.add(node)
        await uow.commit()
    return LcTaxonomy(competence, assertion, evidence, other, text_type)
