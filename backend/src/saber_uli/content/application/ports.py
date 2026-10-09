"""Puertos del contexto `content` (research R-01). Los implementa `content.infrastructure`."""

from collections.abc import Collection
from typing import Protocol
from uuid import UUID

from saber_uli.content.domain.context import Context, ContextVersion
from saber_uli.content.domain.events import HistoryEvent
from saber_uli.content.domain.item import Item
from saber_uli.content.domain.media import Media
from saber_uli.content.domain.module import Module
from saber_uli.content.domain.rubric import Rubric
from saber_uli.content.domain.taxonomy import TaxonomyNode
from saber_uli.shared.domain.errors import ConflictError


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


class MediaRepository(Protocol):
    async def add(self, media: Media) -> Media: ...

    async def get(self, media_id: UUID) -> Media | None: ...

    async def get_by_sha256(self, sha256: bytes) -> Media | None: ...
