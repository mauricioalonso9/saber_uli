"""Cuerpos de entrada de la autoría (contrato: `ItemCreate`, `ItemContent`, `ContextCreate`,
`ContextContent`).

Pydantic solo comprueba la forma (tipos, longitudes, llaves); las reglas del banco (opciones por
módulo y parte, una correcta, retroalimentación, categorías existentes) las aplica el dominio y
llegan como `validation-error` con `field` y `rule` (FR-024).
"""

from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from saber_uli.content.domain.context import ContextContent, ContextKind, SharedOption
from saber_uli.content.domain.item_version import Difficulty, ItemContent, ItemKind, Option
from saber_uli.content.domain.taxonomy import TaxonomyTags

BusinessCode = Annotated[str, Field(pattern=r"^[A-Z]{2,3}(-[A-Z0-9]+){1,3}$", max_length=32)]
ModuleCode = Literal["LC", "RC", "CC", "ING", "CE"]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class OptionIn(_Strict):
    key: Annotated[str, Field(pattern=r"^[A-D]$")]
    text: Annotated[str, Field(min_length=1, max_length=2000)]
    correct: bool
    feedback: Annotated[str, Field(max_length=2000)]


class TaxonomyIn(_Strict):
    competence_id: UUID | None = None
    assertion_id: UUID | None = None
    evidence_id: UUID | None = None
    component_id: UUID | None = None
    situation_id: UUID | None = None
    part_id: UUID | None = None


class ItemContentIn(_Strict):
    difficulty: Literal["low", "medium", "high"]
    context_code: BusinessCode | None = None
    taxonomy: TaxonomyIn
    stem_md: Annotated[str, Field(max_length=5000)]
    options: Annotated[list[OptionIn] | None, Field(max_length=4)] = None
    answer_key: Annotated[str | None, Field(pattern=r"^[A-H]$")] = None
    explanation_md: Annotated[str, Field(max_length=5000)]
    prompt_context_md: Annotated[str | None, Field(max_length=5000)] = None
    rubric_id: UUID | None = None

    def to_domain(self) -> ItemContent:
        return ItemContent(
            difficulty=Difficulty(self.difficulty),
            stem_md=self.stem_md,
            explanation_md=self.explanation_md,
            taxonomy=TaxonomyTags(**self.taxonomy.model_dump()),
            options=None
            if self.options is None
            else tuple(Option(**option.model_dump()) for option in self.options),
            answer_key=self.answer_key,
            prompt_context_md=self.prompt_context_md,
            rubric_id=self.rubric_id,
            context_code=self.context_code,
        )


class ItemCreateIn(_Strict):
    code: BusinessCode
    module: ModuleCode
    kind: Literal["selection", "matching", "writing_prompt"]
    content: ItemContentIn

    @property
    def item_kind(self) -> ItemKind:
        return ItemKind(self.kind)


class SharedOptionIn(_Strict):
    key: Annotated[str, Field(pattern=r"^[A-H]$")]
    text: Annotated[str, Field(min_length=1, max_length=500)]
    feedback: Annotated[str, Field(min_length=1, max_length=2000)]


class ContextContentIn(_Strict):
    kind: Literal["text", "table", "image", "shared_options"]
    title: Annotated[str, Field(min_length=1, max_length=200)]
    body_md: Annotated[str | None, Field(max_length=20000)] = None
    media_id: UUID | None = None
    alt_text: Annotated[str | None, Field(max_length=1000)] = None
    text_type_node_id: UUID | None = None
    part_node_id: UUID | None = None
    subtype: Annotated[str | None, Field(max_length=60)] = None
    shared_options: Annotated[list[SharedOptionIn] | None, Field(min_length=2, max_length=8)] = None

    def to_domain(self) -> ContextContent:
        return ContextContent(
            kind=ContextKind(self.kind),
            title=self.title,
            body_md=self.body_md,
            media_id=self.media_id,
            alt_text=self.alt_text,
            text_type_node_id=self.text_type_node_id,
            part_node_id=self.part_node_id,
            subtype=self.subtype,
            shared_options=None
            if self.shared_options is None
            else tuple(SharedOption(**option.model_dump()) for option in self.shared_options),
        )


class ContextCreateIn(ContextContentIn):
    code: BusinessCode
    module: ModuleCode
