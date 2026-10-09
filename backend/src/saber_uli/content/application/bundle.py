"""Paquete de intercambio ya leído (research R-03; data-model §6).

Los lectores (JSON y XLSX) entregan especificaciones con **códigos** de taxonomía, contexto y
rúbrica; la carga del banco inicial y la importación los resuelven contra la base. Los errores
de forma de cada entrada van en `errors`: una entrada mal formada no invalida el archivo.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
from decimal import Decimal
from enum import StrEnum
from typing import Any
from uuid import UUID

from saber_uli.content.domain.context import ContextKind, Origin, SharedOption
from saber_uli.content.domain.item_version import Difficulty, ItemKind, Option, VersionState
from saber_uli.content.domain.module import Module
from saber_uli.content.domain.rubric import Rubric
from saber_uli.content.domain.taxonomy import PartFormat, TaxonomyNodeKind
from saber_uli.content.domain.validation import ContentIssue
from saber_uli.shared.domain.errors import RuleViolationError


class UnreadableFileError(RuleViolationError):
    """El archivo no se puede leer como un todo: otro esquema, otra versión o mala codificación."""

    slug = "unreadable-file"


class UnsupportedFileFormatError(RuleViolationError):
    """No es JSON ni una plantilla XLSX (un `.xlsm`, otro ZIP u otro tipo de archivo); 415."""

    slug = "unsupported-file-format"


class BatchTooLargeError(RuleViolationError):
    """Más ítems de los que admite un lote (FR-037; research R-05); 413."""

    slug = "batch-too-large"


# Límites de un archivo de importación (FR-037; research R-05).
MAX_IMPORT_BYTES = 10 * 1024 * 1024
MAX_IMPORT_ITEMS = 1000


class EntryKind(StrEnum):
    ITEM = "item"
    WRITING_PROMPT = "writing_prompt"
    CONTEXT = "context"
    RUBRIC = "rubric"
    TAXONOMY_NODE = "taxonomy_node"


@dataclass(frozen=True)
class NodeSpec:
    module_code: str
    kind: TaxonomyNodeKind
    code: str
    name: str
    position: int
    description: str | None = None
    parent_code: str | None = None
    target_weight: Decimal | None = None
    part_options: int | None = None
    part_format: PartFormat | None = None


@dataclass(frozen=True)
class ModuleSpec:
    module: Module
    nodes: tuple[NodeSpec, ...]


@dataclass(frozen=True)
class ContextSpec:
    code: str
    module_code: str
    kind: ContextKind
    title: str
    origin: Origin
    body_md: str | None = None
    media_id: UUID | None = None
    alt_text: str | None = None
    text_type_code: str | None = None
    part_code: str | None = None
    subtype: str | None = None
    shared_options: tuple[SharedOption, ...] | None = None
    state: VersionState | None = None


@dataclass(frozen=True)
class ItemSpec:
    code: str
    module_code: str
    kind: ItemKind
    difficulty: Difficulty
    stem_md: str
    explanation_md: str
    origin: Origin
    tags: Mapping[TaxonomyNodeKind, str] = field(default_factory=dict)
    options: tuple[Option, ...] | None = None
    answer_key: str | None = None
    prompt_context_md: str | None = None
    rubric_code: str | None = None
    context_code: str | None = None
    state: VersionState | None = None
    version: int | None = None


@dataclass(frozen=True)
class EntryError:
    code: str
    entity: EntryKind
    issues: tuple[ContentIssue, ...]


@dataclass
class Bundle:
    schema_version: str
    modules: list[ModuleSpec] = field(default_factory=list)
    contexts: list[ContextSpec] = field(default_factory=list)
    items: list[ItemSpec] = field(default_factory=list)
    rubrics: list[Rubric] = field(default_factory=list)
    errors: list[EntryError] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
