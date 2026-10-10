"""Cobertura del banco (contrato: `getModuleCoverage`; FR-039, FR-040; research R-16).

Permiso `content:author` con sesión privilegiada.
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
from saber_uli.identity.application.public import AuthenticatedUser

router = APIRouter(
    prefix="/api/v1/content", tags=["insights"], dependencies=[Depends(reject_unknown_query)]
)

Author = Annotated[AuthenticatedUser, Depends(privileged_with(CONTENT_AUTHOR))]
ModuleCode = Annotated[Literal["LC", "RC", "CC", "ING", "CE"], Path(alias="moduleCode")]


@router.get("/coverage/{moduleCode}", operation_id="getModuleCoverage")
async def get_module_coverage(request: Request, _: Author, module: ModuleCode) -> dict[str, Any]:
    service: Coverage = request.app.state.content_coverage
    coverage = await service.module(module)
    body = asdict(coverage)
    for category in body["categories"]:
        category["node_id"] = str(category["node_id"])
    return body
