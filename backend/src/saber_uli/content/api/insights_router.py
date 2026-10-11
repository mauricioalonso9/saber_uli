"""Cobertura y estadísticas del banco (contrato: `getModuleCoverage`, `getItemStatistics`;
FR-039 a FR-044; research R-13 y R-16).

Permiso `content:author` con sesión privilegiada. Las estadísticas son agregadas: no llevan
ningún identificador (FR-044).
"""

from dataclasses import asdict
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, Path, Request

from saber_uli.content.api.dependencies import (
    CONTENT_AUTHOR,
    privileged_with,
    reject_unknown_query,
)
from saber_uli.content.application.coverage import Coverage
from saber_uli.content.application.ports import StoredVersionStats
from saber_uli.content.application.queries.statistics import ItemStatisticsQuery
from saber_uli.identity.application.public import AuthenticatedUser

router = APIRouter(
    prefix="/api/v1/content", tags=["insights"], dependencies=[Depends(reject_unknown_query)]
)

Author = Annotated[AuthenticatedUser, Depends(privileged_with(CONTENT_AUTHOR))]
ItemCode = Annotated[
    str, Path(alias="itemCode", pattern=r"^[A-Z]{2,3}(-[A-Z0-9]+){1,3}$", max_length=32)
]
ModuleCode = Annotated[Literal["LC", "RC", "CC", "ING", "CE"], Path(alias="moduleCode")]


@router.get("/coverage/{moduleCode}", operation_id="getModuleCoverage")
async def get_module_coverage(request: Request, _: Author, module: ModuleCode) -> dict[str, Any]:
    service: Coverage = request.app.state.content_coverage
    coverage = await service.module(module)
    body = asdict(coverage)
    for category in body["categories"]:
        category["node_id"] = str(category["node_id"])
    return body


@router.get("/items/{itemCode}/statistics", operation_id="getItemStatistics")
async def get_item_statistics(request: Request, _: Author, code: ItemCode) -> dict[str, Any]:
    service: ItemStatisticsQuery = request.app.state.content_item_statistics
    return {"items": [_version_statistics(entry) for entry in await service.execute(code)]}


def _version_statistics(entry: StoredVersionStats) -> dict[str, Any]:
    stats = entry.stats
    return {
        "version": entry.number,
        "state": entry.state,
        "first_responses": stats.first_responses,
        "sufficient_data": stats.sufficient_data,
        "correct_rate": stats.correct_rate,
        "option_rates": stats.option_rates,
        "discrimination": stats.discrimination,
        "signals": [signal.value for signal in stats.signals],
        "computed_at": None if entry.computed_at is None else entry.computed_at.isoformat(),
    }
