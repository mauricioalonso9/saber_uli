"""Revisión y publicación (US2; FR-010 a FR-015; data-model §4).

Solo los administradores llegan aquí (permiso `content:review`, R-08); los comentarios los hacen
docentes y administradores (`content:author`). Cada acción bloquea el ítem, compara la revisión
que la persona estaba viendo (`If-Match`, R-09) y guarda la transición y su historia en la misma
transacción. Las reglas (autoaprobación, confirmaciones, comentario o motivo) son del dominio.
"""

from collections.abc import Callable
from uuid import UUID

from saber_uli.content.application.unit_of_work import ContentUnitOfWork
from saber_uli.content.domain.errors import EditConflictError, ItemNotFoundError
from saber_uli.content.domain.events import HistoryEvent
from saber_uli.content.domain.item import Item
from saber_uli.shared.domain.clock import Clock


async def load_for_change(uow: ContentUnitOfWork, code: str, expected_revision: int | None) -> Item:
    """El ítem bloqueado para cambiarlo; `None` en la revisión omite la comparación."""
    item = await uow.items.get_by_code(code, for_update=True)
    if item is None:
        raise ItemNotFoundError("El ítem no existe.")
    if expected_revision is not None and item.revision != expected_revision:
        raise EditConflictError("Otra persona cambió este ítem mientras lo revisabas.")
    return item


class Review:
    def __init__(self, *, uow_factory: Callable[[], ContentUnitOfWork], clock: Clock) -> None:
        self._uow_factory = uow_factory
        self._clock = clock

    async def approve(
        self,
        code: str,
        actor: UUID,
        *,
        expected_revision: int,
        confirms_alignment: bool,
        confirms_originality: bool,
    ) -> Item:
        async with self._uow_factory() as uow:
            item = await load_for_change(uow, code, expected_revision)
            item.approve(
                actor,
                self._clock.now(),
                confirms_alignment=confirms_alignment,
                confirms_originality=confirms_originality,
            )
            await uow.items.save(item)
            await uow.commit()
        return item

    async def return_to_draft(
        self, code: str, actor: UUID, *, expected_revision: int, comment: str
    ) -> Item:
        async with self._uow_factory() as uow:
            item = await load_for_change(uow, code, expected_revision)
            item.return_to_draft(actor, self._clock.now(), comment)
            await uow.items.save(item)
            await uow.commit()
        return item

    async def reject(self, code: str, actor: UUID, *, expected_revision: int, reason: str) -> Item:
        async with self._uow_factory() as uow:
            item = await load_for_change(uow, code, expected_revision)
            item.reject(actor, self._clock.now(), reason)
            await uow.items.save(item)
            await uow.commit()
        return item

    async def retire(self, code: str, actor: UUID, *, expected_revision: int, reason: str) -> Item:
        async with self._uow_factory() as uow:
            item = await load_for_change(uow, code, expected_revision)
            item.retire(actor, self._clock.now(), reason)
            await uow.items.save(item)
            await uow.commit()
        return item

    async def comment(self, code: str, actor: UUID, text: str) -> HistoryEvent:
        """Comentario de docente o administrador; no cambia el estado ni la revisión."""
        async with self._uow_factory() as uow:
            item = await load_for_change(uow, code, None)
            item.comment(actor, self._clock.now(), text)
            await uow.items.save(item)
            history = await uow.items.history(code)
            await uow.commit()
        return history[-1]
