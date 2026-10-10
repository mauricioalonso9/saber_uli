"""Puertos del contexto `content` (research R-01). Los implementa `content.infrastructure`."""

from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol
from uuid import UUID

from saber_uli.content.application.bundle import Bundle
from saber_uli.content.domain.context import Context, ContextVersion, Origin
from saber_uli.content.domain.events import HistoryEvent
from saber_uli.content.domain.import_job import ImportJob
from saber_uli.content.domain.item import Item
from saber_uli.content.domain.item_version import ItemKind, ItemVersion
from saber_uli.content.domain.media import Media
from saber_uli.content.domain.module import Module
from saber_uli.content.domain.rubric import Rubric
from saber_uli.content.domain.statistics import FirstResponse, VersionStats
from saber_uli.content.domain.taxonomy import TaxonomyNode
from saber_uli.shared.domain.errors import ConflictError


class UserNames(Protocol):
    """Lo que `content` pide de `identity` (su fachada lo implementa; research R-14)."""

    async def display_names(self, user_ids: Collection[UUID]) -> dict[UUID, str]: ...

    async def active_admin_ids(self) -> set[UUID]: ...


@dataclass(frozen=True)
class ItemFilters:
    """Filtros de `listItems` (contrato). `taxonomy_ids` ya incluye los descendientes."""

    module: str | None = None
    state: str | None = None
    origin: str | None = None
    difficulty: str | None = None
    taxonomy_ids: frozenset[UUID] | None = None
    signal: str | None = None
    q: str | None = None
    awaiting_review_of: UUID | None = None


@dataclass(frozen=True)
class ItemSummaryRow:
    code: str
    module: str
    kind: str
    origin: str
    difficulty: str
    stem: str
    context_code: str | None
    assertion_code: str | None
    part_code: str | None
    published_version: int | None
    open_version: int | None
    open_state: str | None
    open_involved: frozenset[UUID]
    signals: tuple[str, ...]
    updated_at: datetime


class ImmutableVersionError(ConflictError):
    """Se intentó cambiar el contenido de una versión publicada o retirada (ADR 0008)."""

    slug = "immutable-version"


class ModuleRepository(Protocol):
    async def add(self, module: Module) -> None: ...

    async def save(self, module: Module) -> None: ...

    async def get(self, code: str) -> Module | None: ...

    async def list(self) -> list[Module]:
        """Módulos en orden de presentación."""
        ...


class TaxonomyRepository(Protocol):
    async def add(self, node: TaxonomyNode) -> TaxonomyNode: ...

    async def save(self, node: TaxonomyNode) -> None: ...

    async def delete(self, node_id: UUID) -> None: ...

    async def get(self, node_id: UUID) -> TaxonomyNode | None: ...

    async def get_by_code(self, code: str) -> TaxonomyNode | None: ...

    async def list(self, *, module_code: str | None = None) -> list[TaxonomyNode]:
        """Categorías por módulo, tipo y posición (todas si `module_code` es None)."""
        ...

    async def used_ids(self) -> set[UUID]:
        """Categorías que usa alguna versión de ítem o de contexto, o alguna categoría hija."""
        ...


class RubricRepository(Protocol):
    async def add(self, rubric: Rubric) -> Rubric: ...

    async def save(self, rubric: Rubric) -> None: ...

    async def get(self, rubric_id: UUID) -> Rubric | None: ...

    async def get_by_code(self, code: str) -> Rubric | None: ...

    async def list(self) -> list[Rubric]: ...


class ContextRepository(Protocol):
    async def add(self, context: Context) -> Context:
        """Guarda el contexto y su primera versión; asigna los `id`."""
        ...

    async def add_version(self, context: Context, version: ContextVersion) -> None:
        """Agrega una versión, la deja vigente y sube `revision` (R-09)."""
        ...

    async def get_by_code(self, code: str, *, for_update: bool = False) -> Context | None: ...

    async def get_version(self, version_id: UUID) -> ContextVersion | None: ...

    async def codes_by_version(self, version_ids: Collection[UUID]) -> dict[UUID, str]:
        """Código del contexto de cada versión de contexto."""
        ...

    async def version_numbers(self, version_ids: Collection[UUID]) -> dict[UUID, int]:
        """Número de cada versión de contexto."""
        ...


@dataclass(frozen=True)
class StatisticsTarget:
    version_id: UUID
    options: tuple[str, ...]
    key: str


@dataclass(frozen=True)
class StoredVersionStats:
    number: int
    state: str
    stats: VersionStats
    computed_at: datetime | None


class ResponseStatisticsSource(Protocol):
    """Primeras respuestas de cada estudiante por versión, sin identificarlo (FR-044; R-13).

    La implementa la práctica (003) por su fachada; en 002 es nula.
    """

    async def first_responses(
        self, version_ids: Collection[UUID]
    ) -> Mapping[UUID, Sequence[FirstResponse]]: ...


@dataclass(frozen=True)
class CoverageCounts:
    """Conteos de la cobertura: `(publicados, en revisión)` en total y por categoría."""

    published_total: int
    in_review_total: int
    by_node: dict[UUID, tuple[int, int]]


@dataclass(frozen=True)
class ExportedItem:
    """Un ítem con la versión que se exporta (con el código de su contexto)."""

    code: str
    module_code: str
    kind: ItemKind
    origin: Origin
    version: ItemVersion


class ItemRepository(Protocol):
    async def add(self, item: Item) -> Item:
        """Guarda un ítem nuevo con sus versiones y su historia pendiente."""
        ...

    async def save(self, item: Item) -> None:
        """Inserta versiones nuevas, actualiza las cambiadas, guarda la revisión y la historia.

        Lanza `ImmutableVersionError` si cambió el contenido de una versión que estaba
        publicada o retirada al cargarla.
        """
        ...

    async def get_by_code(self, code: str, *, for_update: bool = False) -> Item | None:
        """El ítem con su versión publicada y su versión abierta (si existen)."""
        ...

    async def code_with_fingerprint(
        self, fingerprint: bytes, *, excluding: UUID | None = None
    ) -> str | None:
        """Código de otro ítem con versión no retirada y esa huella (FR-032)."""
        ...

    async def history(self, code: str) -> list[HistoryEvent]:
        """Eventos del ítem en orden de ocurrencia."""
        ...

    async def codes_using_context(self, context_id: UUID) -> list[str]:
        """Ítems con una versión publicada o abierta que usa alguna versión del contexto."""
        ...

    async def context_usage(self, context_id: UUID) -> list[tuple[str, str]]:
        """`(código, estado)` de las versiones publicadas o abiertas que usan el contexto."""
        ...

    async def versions(self, code: str) -> list[ItemVersion]:
        """Todas las versiones del ítem, de la primera a la última."""
        ...

    async def count_matching_in_context(
        self, context_version_id: UUID, *, excluding: UUID | None
    ) -> int:
        """Otros ítems de emparejamiento (publicados o abiertos) que usan el mismo contexto."""
        ...

    async def search(
        self, filters: ItemFilters, *, offset: int, limit: int
    ) -> tuple[list[ItemSummaryRow], int]:
        """Página de ítems ordenada por código y el total (SC-009)."""
        ...

    async def coverage_counts(self, module_code: str, tag: str) -> CoverageCounts:
        """Ítems Publicados y En revisión del módulo, en total y por la categoría `tag`
        (`assertion_id`, `competence_id`, `part_id`…) de esa versión (FR-039)."""
        ...

    async def statistics_targets(self) -> list[StatisticsTarget]:
        """Versiones de ítems de selección que se publicaron (vigentes o ya retiradas)."""
        ...

    async def replace_statistics(
        self, stats: Sequence[tuple[UUID, VersionStats]], computed_at: datetime
    ) -> None:
        """Reemplaza `item_version_stats` completa (research R-13)."""
        ...

    async def statistics(self, code: str) -> list[StoredVersionStats] | None:
        """Estadísticas de las versiones publicadas o retiradas del ítem, de la más reciente a la
        primera; `None` si el ítem no existe."""
        ...

    async def export_batch(
        self, filters: ItemFilters, *, latest: bool, after: str | None, limit: int
    ) -> list[ExportedItem]:
        """Bloque de ítems para exportar, por código, con los códigos mayores que `after`.

        De cada ítem va su versión publicada o, con `latest`, la de número mayor; los filtros de
        estado, dificultad y taxonomía se aplican a esa versión (FR-038; research R-18).
        """
        ...


class MediaRepository(Protocol):
    async def add(self, media: Media) -> Media: ...

    async def get(self, media_id: UUID) -> Media | None: ...

    async def get_by_sha256(self, sha256: bytes) -> Media | None: ...

    async def add_or_get(self, media: Media) -> Media:
        """Guarda la imagen o, si ya existe una con la misma huella, devuelve esa."""
        ...

    async def is_public(self, media_id: UUID) -> bool:
        """La usa un contexto de alguna versión Publicada o Retirada (FR-046)."""
        ...


@dataclass(frozen=True)
class ProcessedImage:
    """Imagen verificada y re-codificada sin metadatos (research R-11)."""

    data: bytes
    content_type: str
    width: int
    height: int


class ImageProcessor(Protocol):
    def process(self, data: bytes) -> ProcessedImage:
        """Verifica y re-codifica; `FileTooLargeError` o `UnsupportedMediaError` si no sirve."""
        ...


@dataclass(frozen=True)
class SeedLoadRecord:
    """Una carga del banco inicial (data-model §2.12)."""

    loaded_at: datetime
    file_sha256: bytes
    schema_version: str
    summary: dict[str, Any]
    pending_manual: list[str] = field(default_factory=list)


class SeedLoadRepository(Protocol):
    async def add(self, record: SeedLoadRecord) -> None: ...


class ImportRepository(Protocol):
    async def add(self, job: ImportJob) -> ImportJob: ...

    async def get(self, import_id: UUID, *, for_update: bool = False) -> ImportJob | None: ...

    async def save(self, job: ImportJob) -> None:
        """Guarda solo lo que cambia al confirmar o vencer (data-model §2.9)."""
        ...

    async def list(
        self, *, created_by: UUID | None, offset: int, limit: int
    ) -> tuple[list[ImportJob], int]:
        """Las más recientes primero; `created_by=None` lista todas (administración)."""
        ...

    async def expire_pending(self, now: datetime) -> int:
        """Marca vencidas las pendientes cuyo plazo pasó y borra su contenido (R-05)."""
        ...


@dataclass(frozen=True)
class ExportRecord:
    """Una exportación del banco (data-model §2.10; solo inserción)."""

    created_by: UUID
    created_at: datetime
    format: str
    filter: dict[str, Any]
    version_choice: str
    item_count: int
    skipped_count: int


@dataclass(frozen=True)
class TaxonomyChange:
    """Un cambio de la taxonomía, de un módulo o de una rúbrica (data-model §2.11)."""

    changed_by: UUID
    changed_at: datetime
    target: str  # node, rubric o module
    target_id: str
    action: str  # created, updated, deactivated, reactivated o deleted
    before: dict[str, Any] | None
    after: dict[str, Any] | None


class TaxonomyChangeRepository(Protocol):
    async def add(self, change: TaxonomyChange) -> None: ...


class ExportRepository(Protocol):
    async def add(self, record: ExportRecord) -> None: ...


class BundleCodec(Protocol):
    """Contenido de una importación pendiente, listo para aplicar al confirmar (`payload`)."""

    def dump(self, bundle: Bundle) -> dict[str, Any]: ...

    def load(self, payload: dict[str, Any]) -> Bundle: ...
