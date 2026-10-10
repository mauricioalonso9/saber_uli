"""Fuente de respuestas de 002: aún no hay práctica (003), así que no hay respuestas (R-13)."""

from collections.abc import Collection, Mapping, Sequence
from uuid import UUID

from saber_uli.content.domain.statistics import FirstResponse


class NullStatisticsSource:
    async def first_responses(
        self,
        version_ids: Collection[UUID],  # noqa: ARG002 - 003 la reemplaza
    ) -> Mapping[UUID, Sequence[FirstResponse]]:
        return {}
