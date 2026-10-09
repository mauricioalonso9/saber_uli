"""Módulos, taxonomía y rúbricas (data-model §2.1 a §2.3)."""

from typing import Any
from uuid import UUID

from sqlalchemy import delete, select, union
from sqlalchemy.ext.asyncio import AsyncSession

from saber_uli.content.domain.module import Module, QuestionType
from saber_uli.content.domain.rubric import (
    RelevanceCondition,
    Rubric,
    RubricDimension,
    RubricLevel,
)
from saber_uli.content.domain.taxonomy import PartFormat, TaxonomyNode, TaxonomyNodeKind
from saber_uli.content.infrastructure.orm import (
    ContextVersionRow,
    ItemVersionRow,
    ModuleRow,
    RubricRow,
    TaxonomyNodeRow,
)


class SqlAlchemyModuleRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._db = session

    async def add(self, module: Module) -> None:
        row = ModuleRow(code=module.code)
        _copy_module(module, row)
        self._db.add(row)
        await self._db.flush()

    async def save(self, module: Module) -> None:
        row = await self._db.get(ModuleRow, module.code)
        if row is None:
            raise LookupError("el módulo no existe")
        _copy_module(module, row)
        await self._db.flush()

    async def get(self, code: str) -> Module | None:
        row = await self._db.get(ModuleRow, code)
        return None if row is None else _module(row)

    async def list(self) -> list[Module]:
        rows = await self._db.scalars(select(ModuleRow).order_by(ModuleRow.position))
        return [_module(row) for row in rows]


def _copy_module(module: Module, row: ModuleRow) -> None:
    row.name = module.name
    row.question_type = module.question_type.value
    row.options_per_item = module.options_per_item
    row.max_context_words = module.max_context_words
    row.exam_questions = module.exam_questions
    row.bank_target = module.bank_target
    row.position = module.position


def _module(row: ModuleRow) -> Module:
    return Module(
        code=row.code,
        name=row.name,
        question_type=QuestionType(row.question_type),
        options_per_item=row.options_per_item,
        max_context_words=row.max_context_words,
        exam_questions=row.exam_questions,
        bank_target=row.bank_target,
        position=row.position,
    )


class SqlAlchemyTaxonomyRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._db = session

    async def add(self, node: TaxonomyNode) -> TaxonomyNode:
        row = TaxonomyNodeRow(id=node.id)
        _copy_node(node, row)
        self._db.add(row)
        await self._db.flush()
        node.id = row.id
        return node

    async def save(self, node: TaxonomyNode) -> None:
        row = await self._db.get(TaxonomyNodeRow, node.id)
        if row is None:
            raise LookupError("la categoría no existe")
        _copy_node(node, row)
        await self._db.flush()

    async def delete(self, node_id: UUID) -> None:
        await self._db.execute(delete(TaxonomyNodeRow).where(TaxonomyNodeRow.id == node_id))

    async def get(self, node_id: UUID) -> TaxonomyNode | None:
        row = await self._db.get(TaxonomyNodeRow, node_id)
        return None if row is None else _node(row)

    async def get_by_code(self, code: str) -> TaxonomyNode | None:
        row = await self._db.scalar(select(TaxonomyNodeRow).where(TaxonomyNodeRow.code == code))
        return None if row is None else _node(row)

    async def list(self, *, module_code: str | None = None) -> list[TaxonomyNode]:
        query = select(TaxonomyNodeRow).order_by(
            TaxonomyNodeRow.module_code,
            TaxonomyNodeRow.kind,
            TaxonomyNodeRow.position,
            TaxonomyNodeRow.code,
        )
        if module_code is not None:
            query = query.where(TaxonomyNodeRow.module_code == module_code)
        return [_node(row) for row in await self._db.scalars(query)]

    async def used_ids(self) -> set[UUID]:
        v = ItemVersionRow
        c = ContextVersionRow
        columns = (
            v.competence_id,
            v.assertion_id,
            v.evidence_id,
            v.component_id,
            v.situation_id,
            v.part_id,
            c.text_type_node_id,
            c.part_node_id,
            TaxonomyNodeRow.parent_id,
        )
        used = union(*(select(column).where(column.is_not(None)) for column in columns))
        return set((await self._db.scalars(select(used.subquery().c[0]))).all())


def _copy_node(node: TaxonomyNode, row: TaxonomyNodeRow) -> None:
    row.module_code = node.module_code
    row.kind = node.kind.value
    row.code = node.code
    row.name = node.name
    row.description = node.description
    row.parent_id = node.parent_id
    row.target_weight = node.target_weight
    row.part_options = node.part_options
    row.part_format = None if node.part_format is None else node.part_format.value
    row.active = node.active
    row.position = node.position


def _node(row: TaxonomyNodeRow) -> TaxonomyNode:
    return TaxonomyNode(
        id=row.id,
        module_code=row.module_code,
        kind=TaxonomyNodeKind(row.kind),
        code=row.code,
        name=row.name,
        position=row.position,
        description=row.description,
        parent_id=row.parent_id,
        target_weight=row.target_weight,
        part_options=row.part_options,
        part_format=None if row.part_format is None else PartFormat(row.part_format),
        active=row.active,
    )


class SqlAlchemyRubricRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._db = session

    async def add(self, rubric: Rubric) -> Rubric:
        row = RubricRow()
        _copy_rubric(rubric, row)
        self._db.add(row)
        await self._db.flush()
        return _rubric(row)

    async def save(self, rubric: Rubric) -> None:
        row = await self._db.get(RubricRow, rubric.id)
        if row is None:
            raise LookupError("la rúbrica no existe")
        _copy_rubric(rubric, row)
        await self._db.flush()

    async def get(self, rubric_id: UUID) -> Rubric | None:
        row = await self._db.get(RubricRow, rubric_id)
        return None if row is None else _rubric(row)

    async def get_by_code(self, code: str) -> Rubric | None:
        row = await self._db.scalar(select(RubricRow).where(RubricRow.code == code))
        return None if row is None else _rubric(row)

    async def list(self) -> list[Rubric]:
        rows = await self._db.scalars(select(RubricRow).order_by(RubricRow.code))
        return [_rubric(row) for row in rows]


def _copy_rubric(rubric: Rubric, row: RubricRow) -> None:
    row.code = rubric.code
    row.name = rubric.name
    row.note = rubric.note
    row.active = rubric.active
    row.relevance_condition = {
        "name": rubric.relevance_condition.name,
        "description": rubric.relevance_condition.description,
    }
    row.dimensions = [
        {
            "code": dimension.code,
            "name": dimension.name,
            "levels": [
                {"level": level.level, "description": level.description}
                for level in dimension.levels
            ],
        }
        for dimension in rubric.dimensions
    ]


def _rubric(row: RubricRow) -> Rubric:
    condition: dict[str, Any] = row.relevance_condition
    return Rubric(
        id=row.id,
        code=row.code,
        name=row.name,
        note=row.note,
        active=row.active,
        relevance_condition=RelevanceCondition(
            name=condition["name"], description=condition["description"]
        ),
        dimensions=tuple(
            RubricDimension(
                code=dimension["code"],
                name=dimension["name"],
                levels=tuple(
                    RubricLevel(level=level["level"], description=level["description"])
                    for level in dimension["levels"]
                ),
            )
            for dimension in row.dimensions
        ),
    )
