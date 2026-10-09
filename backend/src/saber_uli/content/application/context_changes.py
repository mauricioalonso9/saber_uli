"""Efecto de una versión nueva de un contexto sobre sus ítems (FR-020; research R-02).

- Una versión abierta (Borrador o En revisión) pasa a la nueva versión del contexto
  (`rebased_on_context`); si estaba En revisión, sigue En revisión.
- Un ítem publicado sin versión abierta recibe una versión nueva En revisión con la nueva versión
  del contexto (`context_changed`); la publicada sigue entregándose hasta que se apruebe.

La huella de duplicados incluye el texto del contexto, así que se recalcula.
"""

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from saber_uli.content.application.resolution import context_text, item_hashes
from saber_uli.content.application.unit_of_work import ContentUnitOfWork
from saber_uli.content.domain.context import Context
from saber_uli.content.domain.events import HistoryEventType
from saber_uli.content.domain.item_version import VersionState


@dataclass
class PropagationResult:
    new_review_versions: list[str] = field(default_factory=list)
    rebased_open_versions: list[str] = field(default_factory=list)


async def propagate_context_change(
    uow: ContentUnitOfWork,
    context: Context,
    *,
    actor: UUID | None,
    now: datetime,
    skip: frozenset[str] = frozenset(),
) -> PropagationResult:
    """Aplica FR-020 a los ítems del contexto. `skip`: códigos que quien llama actualiza aparte."""
    if context.id is None or context.current.id is None:
        raise ValueError("el contexto y su versión deben estar guardados")
    result = PropagationResult()
    text = context_text(context.current.content)
    for code in await uow.items.codes_using_context(context.id):
        if code in skip:
            continue
        item = await uow.items.get_by_code(code, for_update=True)
        if item is None:  # pragma: no cover - lo acaba de listar la misma transacción
            continue
        version = item.open or item.published
        if version is None or version.context_version_id == context.current.id:
            continue
        hash_, print_ = item_hashes(version.content, text)
        if item.open is not None:
            item.edit(
                version.content,
                hash_,
                print_,
                context.current.id,
                actor,
                now,
                keep_in_review=version.state is VersionState.IN_REVIEW,
                event_type=HistoryEventType.REBASED_ON_CONTEXT,
            )
            result.rebased_open_versions.append(code)
        else:
            item.edit(
                version.content,
                hash_,
                print_,
                context.current.id,
                actor,
                now,
                start_state=VersionState.IN_REVIEW,
                event_type=HistoryEventType.CONTEXT_CHANGED,
            )
            result.new_review_versions.append(code)
        await uow.items.save(item)
    return result
