"""Rúbricas de Comunicación escrita como datos que mantiene el administrador (US9; FR-004, FR-045).

El dominio exige al menos una dimensión y dos niveles por dimensión. El código es único. Cada
cambio queda en `content.taxonomy_changes`.
"""

from collections.abc import Callable
from dataclasses import replace
from typing import Any
from uuid import UUID

from saber_uli.content.application.ports import TaxonomyChange
from saber_uli.content.application.unit_of_work import ContentUnitOfWork
from saber_uli.content.domain.errors import RubricCodeTakenError, RubricNotFoundError
from saber_uli.content.domain.rubric import Rubric
from saber_uli.shared.domain.clock import Clock


def _snapshot(rubric: Rubric) -> dict[str, Any]:
    return {
        "code": rubric.code,
        "name": rubric.name,
        "note": rubric.note,
        "active": rubric.active,
        "relevance_condition": vars(rubric.relevance_condition),
        "dimensions": [
            {
                "code": d.code,
                "name": d.name,
                "levels": [{"level": lv.level, "description": lv.description} for lv in d.levels],
            }
            for d in rubric.dimensions
        ],
    }


class RubricAdmin:
    def __init__(self, *, uow_factory: Callable[[], ContentUnitOfWork], clock: Clock) -> None:
        self._uow_factory = uow_factory
        self._clock = clock

    async def create(self, rubric: Rubric, actor: UUID) -> Rubric:
        async with self._uow_factory() as uow:
            if await uow.rubrics.get_by_code(rubric.code) is not None:
                raise RubricCodeTakenError(f"Ya existe una rúbrica con el código {rubric.code}.")
            saved = await uow.rubrics.add(rubric)
            await self._record(uow, saved, "created", None, _snapshot(saved), actor)
            await uow.commit()
        return saved

    async def update(self, rubric_id: UUID, rubric: Rubric, actor: UUID) -> Rubric:
        async with self._uow_factory() as uow:
            stored = await uow.rubrics.get(rubric_id)
            if stored is None:
                raise RubricNotFoundError("La rúbrica no existe.")
            other = await uow.rubrics.get_by_code(rubric.code)
            if other is not None and other.id != rubric_id:
                raise RubricCodeTakenError(f"Ya existe una rúbrica con el código {rubric.code}.")
            updated = replace(rubric, id=rubric_id)
            await uow.rubrics.save(updated)
            await self._record(
                uow, updated, "updated", _snapshot(stored), _snapshot(updated), actor
            )
            await uow.commit()
        return updated

    async def _record(
        self,
        uow: ContentUnitOfWork,
        rubric: Rubric,
        action: str,
        before: dict[str, Any] | None,
        after: dict[str, Any] | None,
        actor: UUID,
    ) -> None:
        await uow.taxonomy_changes.add(
            TaxonomyChange(
                changed_by=actor,
                changed_at=self._clock.now(),
                target="rubric",
                target_id=str(rubric.id),
                action=action,
                before=before,
                after=after,
            )
        )
