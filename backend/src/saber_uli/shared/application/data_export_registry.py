"""Registro de proveedores de «Mis datos» (FR-031; research R-26).

Cada contexto que guarde datos personales (progreso, respuestas… en 002 en adelante) registra un
proveedor con su sección. La exportación de `identity` llama a todos y agrega sus secciones,
así ningún contexto necesita conocer a los demás.
"""

from collections.abc import Mapping
from typing import Any, Protocol
from uuid import UUID


class DataExportProvider(Protocol):
    section: str

    async def export(self, user_id: UUID) -> Mapping[str, Any]:
        """Datos personales del usuario en este contexto; solo los suyos, nunca de otras
        personas."""
        ...


class DataExportRegistry:
    def __init__(self) -> None:
        self._providers: dict[str, DataExportProvider] = {}

    def register(self, provider: DataExportProvider) -> None:
        if provider.section in self._providers:
            raise ValueError(f"la sección {provider.section!r} ya tiene proveedor")
        self._providers[provider.section] = provider

    async def sections(self, user_id: UUID) -> dict[str, Any]:
        return {
            section: dict(await provider.export(user_id))
            for section, provider in sorted(self._providers.items())
        }
