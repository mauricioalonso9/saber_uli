"""Sección `banco_de_items` de «Mis datos» (FR-031 de 001; research R-14).

`content` guarda a las personas solo por su UUID; esta sección le muestra a cada una dónde
aparece: versiones, eventos, importaciones, exportaciones y cambios de la taxonomía.
"""

from collections.abc import Callable, Mapping
from typing import Any
from uuid import UUID

from saber_uli.content.application.unit_of_work import ContentUnitOfWork


class ContentDataExport:
    section = "banco_de_items"

    def __init__(self, *, uow_factory: Callable[[], ContentUnitOfWork]) -> None:
        self._uow_factory = uow_factory

    async def export(self, user_id: UUID) -> Mapping[str, Any]:
        async with self._uow_factory() as uow:
            return await uow.personal_data.collect(user_id)
