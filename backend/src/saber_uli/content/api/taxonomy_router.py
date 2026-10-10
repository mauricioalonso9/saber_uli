"""Módulos, taxonomía y rúbricas (contrato: `listContentModules`, `listRubrics`,
`updateContentModule`, `createTaxonomyNode`, `updateTaxonomyNode`, `deleteTaxonomyNode`,
`createRubric` y `updateRubric`; FR-001, FR-040, FR-045).

Lectura: `content:author` con sesión privilegiada (docentes y administradores, R-08). Cambios:
`content:taxonomy_manage` (administración).
"""

from decimal import Decimal
from typing import Annotated, Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query, Request, Response
from pydantic import AfterValidator, BaseModel, ConfigDict, Field, StrictBool

from saber_uli.content.api.dependencies import Author, TaxonomyManager, reject_unknown_query
from saber_uli.content.application.queries.modules import (
    ListContentModules,
    ListRubrics,
    ModuleView,
    NodeView,
)
from saber_uli.content.application.rubrics import RubricAdmin
from saber_uli.content.application.taxonomy_admin import NewNode, NodeResult, TaxonomyAdmin
from saber_uli.content.domain.rubric import (
    RelevanceCondition,
    Rubric,
    RubricDimension,
    RubricLevel,
)
from saber_uli.content.domain.taxonomy import PartFormat, TaxonomyNodeKind
from saber_uli.shared.api.problems import FieldError, ProblemException

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


# ------------------------------------------------------------------------------- cambios (US9)


def _storable(value: str) -> str:
    """PostgreSQL no guarda el carácter NUL ni un sustituto UTF-16 suelto: es un 422, no un 500."""
    if "\x00" in value:
        raise ValueError("El texto no puede contener el carácter NUL.")
    try:
        value.encode("utf-8")
    except UnicodeEncodeError as error:
        raise ValueError("El texto tiene caracteres inválidos.") from error
    return value


Text = Annotated[str, AfterValidator(_storable)]
ModuleCode = Annotated[Literal["LC", "RC", "CC", "ING", "CE"], Path(alias="moduleCode")]
NodeId = Annotated[UUID, Path(alias="nodeId")]
RubricId = Annotated[UUID, Path(alias="rubricId")]


def _admin(request: Request) -> TaxonomyAdmin:
    service: TaxonomyAdmin = request.app.state.content_taxonomy_admin
    return service


def _decimal(value: float | None) -> Decimal | None:
    return None if value is None else Decimal(str(value))


class ModuleUpdateIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    bank_target: int = Field(ge=1, le=10000)


class TaxonomyNodeCreateIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    module: Literal["LC", "RC", "CC", "ING", "CE"]
    kind: NodeKind
    code: Text = Field(pattern=r"^[A-Z]{2,3}-[A-Z0-9.-]{1,20}$")
    name: Text = Field(min_length=1, max_length=200)
    description: Text | None = Field(default=None, max_length=1000)
    parent_id: UUID | None = None
    target_weight: float | None = Field(default=None, ge=0, le=1)
    part_options: int | None = Field(default=None, ge=2, le=8)
    part_format: Literal["matching", "selection"] | None = None


class TaxonomyNodeUpdateIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: Text = Field(default="-", min_length=1, max_length=200)
    description: Text | None = Field(default=None, max_length=1000)
    target_weight: float | None = Field(default=None, ge=0, le=1)
    active: StrictBool = True


class TaxonomyNodeWithWarnings(TaxonomyNodeOut):
    warnings: list[str]

    @classmethod
    def of_result(cls, result: NodeResult) -> "TaxonomyNodeWithWarnings":
        return cls(**TaxonomyNodeOut.of(result.view).model_dump(), warnings=result.warnings)


@router.patch("/modules/{moduleCode}", operation_id="updateContentModule")
async def update_content_module(
    request: Request, user: TaxonomyManager, code: ModuleCode, body: ModuleUpdateIn
) -> ContentModuleOut:
    view = await _admin(request).update_module(code, bank_target=body.bank_target, actor=user.id)
    return ContentModuleOut.of(view)


@router.post("/taxonomy-nodes", operation_id="createTaxonomyNode", status_code=201)
async def create_taxonomy_node(
    request: Request, user: TaxonomyManager, body: TaxonomyNodeCreateIn
) -> TaxonomyNodeWithWarnings:
    result = await _admin(request).create_node(
        NewNode(
            module=body.module,
            kind=TaxonomyNodeKind(body.kind),
            code=body.code,
            name=body.name,
            description=body.description,
            parent_id=body.parent_id,
            target_weight=_decimal(body.target_weight),
            part_options=body.part_options,
            part_format=None if body.part_format is None else PartFormat(body.part_format),
        ),
        user.id,
    )
    return TaxonomyNodeWithWarnings.of_result(result)


@router.patch("/taxonomy-nodes/{nodeId}", operation_id="updateTaxonomyNode")
async def update_taxonomy_node(
    request: Request, user: TaxonomyManager, node_id: NodeId, body: TaxonomyNodeUpdateIn
) -> TaxonomyNodeWithWarnings:
    sent = body.model_fields_set
    if not sent:
        raise ProblemException(
            422,
            "validation-error",
            detail="Indica qué cambiar.",
            errors=[FieldError(field="body", message="Indica al menos un campo.")],
        )
    changes: dict[str, Any] = {name: getattr(body, name) for name in sent}
    if "target_weight" in changes:
        changes["target_weight"] = _decimal(changes["target_weight"])
    result = await _admin(request).update_node(node_id, user.id, **changes)
    return TaxonomyNodeWithWarnings.of_result(result)


@router.delete("/taxonomy-nodes/{nodeId}", operation_id="deleteTaxonomyNode", status_code=204)
async def delete_taxonomy_node(
    request: Request, user: TaxonomyManager, node_id: NodeId
) -> Response:
    await _admin(request).delete_node(node_id, user.id)
    return Response(status_code=204)


# Como en el contrato, solo el cuerpo rechaza campos de más; los objetos anidados los ignoran.
class RelevanceConditionIn(BaseModel):
    name: Text
    description: Text


class RubricLevelIn(BaseModel):
    level: int = Field(ge=1)
    description: Text


class RubricDimensionIn(BaseModel):
    code: Text
    name: Text
    levels: list[RubricLevelIn] = Field(min_length=2)


class RubricIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: Text = Field(pattern=r"^RUB-[A-Z0-9-]{1,20}$")
    name: Text = Field(min_length=1, max_length=200)
    note: Text | None = Field(default=None, max_length=1000)
    active: StrictBool
    relevance_condition: RelevanceConditionIn
    dimensions: list[RubricDimensionIn] = Field(min_length=1)

    def to_domain(self) -> Rubric:
        return Rubric(
            id=None,
            code=self.code,
            name=self.name,
            note=self.note,
            active=self.active,
            relevance_condition=RelevanceCondition(
                name=self.relevance_condition.name,
                description=self.relevance_condition.description,
            ),
            dimensions=tuple(
                RubricDimension(
                    code=d.code,
                    name=d.name,
                    levels=tuple(RubricLevel(lv.level, lv.description) for lv in d.levels),
                )
                for d in self.dimensions
            ),
        )


def _rubrics(request: Request) -> RubricAdmin:
    service: RubricAdmin = request.app.state.content_rubric_admin
    return service


@router.post("/rubrics", operation_id="createRubric", status_code=201)
async def create_rubric(request: Request, user: TaxonomyManager, body: RubricIn) -> RubricOut:
    return RubricOut.of(await _rubrics(request).create(body.to_domain(), user.id))


@router.put("/rubrics/{rubricId}", operation_id="updateRubric")
async def update_rubric(
    request: Request, user: TaxonomyManager, rubric_id: RubricId, body: RubricIn
) -> RubricOut:
    return RubricOut.of(await _rubrics(request).update(rubric_id, body.to_domain(), user.id))
