"""Módulos, taxonomía y rúbricas (contrato: `listContentModules`, `listRubrics`; US9 agrega la
edición).

Lectura: `content:author` con sesión privilegiada (docentes y administradores, R-08).
"""

from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel

from saber_uli.content.api.dependencies import Author, reject_unknown_query
from saber_uli.content.application.queries.modules import (
    ListContentModules,
    ListRubrics,
    ModuleView,
    NodeView,
)
from saber_uli.content.domain.rubric import Rubric

router = APIRouter(
    prefix="/api/v1/content", tags=["taxonomy"], dependencies=[Depends(reject_unknown_query)]
)

NodeKind = Literal[
    "competence", "assertion", "evidence", "component", "situation", "text_type", "part"
]


class TaxonomyNodeOut(BaseModel):
    id: UUID
    module: str
    kind: NodeKind
    code: str
    name: str
    description: str | None
    parent_id: UUID | None
    target_weight: float | None
    part_options: int | None
    part_format: Literal["matching", "selection"] | None
    active: bool
    in_use: bool

    @classmethod
    def of(cls, view: NodeView) -> "TaxonomyNodeOut":
        node = view.node
        return cls(
            id=node.id,
            module=node.module_code,
            kind=node.kind.value,
            code=node.code,
            name=node.name,
            description=node.description,
            parent_id=node.parent_id,
            target_weight=_float(node.target_weight),
            part_options=node.part_options,
            part_format=None if node.part_format is None else node.part_format.value,
            active=node.active,
            in_use=view.in_use,
        )


class ContentModuleOut(BaseModel):
    code: Literal["LC", "RC", "CC", "ING", "CE"]
    name: str
    question_type: Literal["selection", "writing"]
    options_per_item: int | None
    max_context_words: int | None
    exam_questions: int
    bank_target: int
    nodes: list[TaxonomyNodeOut]

    @classmethod
    def of(cls, view: ModuleView) -> "ContentModuleOut":
        module = view.module
        return cls(
            code=module.code,  # type: ignore[arg-type]
            name=module.name,
            question_type=module.question_type.value,
            options_per_item=module.options_per_item,
            max_context_words=module.max_context_words,
            exam_questions=module.exam_questions,
            bank_target=module.bank_target,
            nodes=[TaxonomyNodeOut.of(node) for node in view.nodes],
        )


class ContentModuleList(BaseModel):
    items: list[ContentModuleOut]


def _float(value: Decimal | None) -> float | None:
    return None if value is None else float(value)


def _list_modules(request: Request) -> ListContentModules:
    service: ListContentModules = request.app.state.content_list_modules
    return service


@router.get("/modules", operation_id="listContentModules")
async def list_content_modules(
    request: Request,
    _: Author,
    include_inactive: Annotated[bool, Query()] = False,
) -> ContentModuleList:
    views = await _list_modules(request).execute(include_inactive=include_inactive)
    return ContentModuleList(items=[ContentModuleOut.of(view) for view in views])


class RelevanceConditionOut(BaseModel):
    name: str
    description: str


class RubricLevelOut(BaseModel):
    level: int
    description: str


class RubricDimensionOut(BaseModel):
    code: str
    name: str
    levels: list[RubricLevelOut]


class RubricOut(BaseModel):
    id: UUID
    code: str
    name: str
    note: str | None
    active: bool
    relevance_condition: RelevanceConditionOut
    dimensions: list[RubricDimensionOut]

    @classmethod
    def of(cls, rubric: Rubric) -> "RubricOut":
        if rubric.id is None:
            raise ValueError("la rúbrica aún no se ha guardado")
        return cls(
            id=rubric.id,
            code=rubric.code,
            name=rubric.name,
            note=rubric.note,
            active=rubric.active,
            relevance_condition=RelevanceConditionOut(
                name=rubric.relevance_condition.name,
                description=rubric.relevance_condition.description,
            ),
            dimensions=[
                RubricDimensionOut(
                    code=dimension.code,
                    name=dimension.name,
                    levels=[
                        RubricLevelOut(level=level.level, description=level.description)
                        for level in dimension.levels
                    ],
                )
                for dimension in rubric.dimensions
            ],
        )


class RubricList(BaseModel):
    items: list[RubricOut]


@router.get("/rubrics", operation_id="listRubrics")
async def list_rubrics(request: Request, _: Author) -> RubricList:
    service: ListRubrics = request.app.state.content_list_rubrics
    return RubricList(items=[RubricOut.of(rubric) for rubric in await service.execute()])
