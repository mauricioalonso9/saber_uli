"""Importación y exportación del banco (contrato: `getImportTemplate`, `createImport`,
`listImports`, `getImport`, `getImportReport`, `confirmImport` y `exportItems`; FR-028 a FR-038;
research R-04, R-05 y R-18).

Permiso `content:author` con sesión privilegiada. Cada docente ve sus importaciones; quien revisa
(administración) las ve todas. Solo quien subió el archivo lo confirma. Subir cuenta para el
límite de 30 por hora por persona. El nombre del archivo no va a los logs.
"""

from typing import Annotated, Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query, Request, UploadFile
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel, ConfigDict

from saber_uli.content.api import schemas
from saber_uli.content.api.dependencies import (
    CONTENT_AUTHOR,
    CONTENT_REVIEW,
    privileged_with,
    reject_unknown_query,
)
from saber_uli.content.application.bank_export import BankExport, ExportRequest
from saber_uli.content.application.bank_import import BankImport
from saber_uli.content.application.bundle import MAX_IMPORT_BYTES
from saber_uli.content.domain.errors import FileTooLargeError
from saber_uli.content.domain.import_job import ImportAction, ImportJob
from saber_uli.content.domain.item_version import VersionState
from saber_uli.content.infrastructure.interchange.xlsx_format import (
    write_report,
    write_template,
)
from saber_uli.identity.application.public import AuthenticatedUser
from saber_uli.shared.api.pagination import PageParams, page_params
from saber_uli.shared.api.rate_limit import per_user
from saber_uli.shared.infrastructure.rate_limit import RateLimitRule

IMPORT_UPLOAD_PER_USER = RateLimitRule("content-import-user", "30/hour")
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
TEMPLATE_NAME = "plantilla-banco-saber-uli.xlsx"

router = APIRouter(
    prefix="/api/v1/content", tags=["transfer"], dependencies=[Depends(reject_unknown_query)]
)

_author = privileged_with(CONTENT_AUTHOR)
Author = Annotated[AuthenticatedUser, Depends(_author)]
ImportId = Annotated[UUID, Path(alias="importId")]


class ConfirmationIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    target_state: Literal["draft", "in_review"]
    originality_declared: Literal[True]


def _service(request: Request) -> BankImport:
    service: BankImport = request.app.state.content_bank_import
    return service


def _sees_all(user: AuthenticatedUser) -> bool:
    return CONTENT_REVIEW in user.permissions


def _download(content: bytes, filename: str) -> Response:
    return Response(
        content,
        media_type=XLSX,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


async def _summary(request: Request, job: ImportJob) -> dict[str, Any]:
    names = await request.app.state.content_user_names.display_names({job.created_by})
    return _summary_body(job, names)


def _summary_body(job: ImportJob, names: dict[UUID, str]) -> dict[str, Any]:
    return {
        "id": str(job.id),
        "status": job.status.value,
        "source_name": job.source_name,
        "format": job.format,
        "created_at": job.created_at.isoformat(),
        "expires_at": None if job.expires_at is None else job.expires_at.isoformat(),
        "confirmed_at": None if job.confirmed_at is None else job.confirmed_at.isoformat(),
        "created_by": schemas.user_ref(job.created_by, names),
        "counts": job.counts(),
    }


async def _detail(
    request: Request,
    job: ImportJob,
    paging: PageParams,
    action: ImportAction | None = None,
) -> dict[str, Any]:
    rows = [row for row in job.rows if action is None or row.action is action]
    shown = rows[paging.offset : paging.offset + paging.limit]
    return {
        **await _summary(request, job),
        "rows": [
            {
                "code": row.code,
                "entity": row.entity,
                "action": row.action.value,
                "target_state": row.target_state,
                "changes": [schemas.field_change(change) for change in row.changes],
                "errors": [
                    {"field": e.field, "rule": e.rule.value, "message": e.message}
                    for e in row.errors
                ],
            }
            for row in shown
        ],
        "meta": {"page": paging.page, "page_size": paging.page_size, "total": len(rows)},
        "result": job.result,
    }


@router.get("/import-template", operation_id="getImportTemplate")
async def get_import_template(request: Request, _: Author) -> Response:
    return _download(write_template(await _service(request).active_nodes()), TEMPLATE_NAME)


@router.post(
    "/imports",
    operation_id="createImport",
    status_code=201,
    dependencies=[Depends(per_user(IMPORT_UPLOAD_PER_USER, _author))],
)
async def create_import(request: Request, user: Author, file: UploadFile) -> dict[str, Any]:
    # Un byte de más basta para saber si pasa del límite sin cargar archivos enormes.
    content = await file.read(MAX_IMPORT_BYTES + 1)
    if len(content) > MAX_IMPORT_BYTES:
        raise FileTooLargeError("El archivo pesa más de 10 MB.")
    job = await _service(request).preview(content, file.filename or "archivo", user.id)
    return await _detail(request, job, PageParams())


@router.get("/imports", operation_id="listImports")
async def list_imports(
    request: Request, user: Author, paging: Annotated[PageParams, Depends(page_params)]
) -> dict[str, Any]:
    jobs, total = await _service(request).list_imports(
        user.id, sees_all=_sees_all(user), offset=paging.offset, limit=paging.limit
    )
    names = await request.app.state.content_user_names.display_names(
        {job.created_by for job in jobs}
    )
    return {
        "items": [_summary_body(job, names) for job in jobs],
        "meta": {"page": paging.page, "page_size": paging.page_size, "total": total},
    }


@router.get("/imports/{importId}", operation_id="getImport")
async def get_import(
    request: Request,
    user: Author,
    import_id: ImportId,
    paging: Annotated[PageParams, Depends(page_params)],
    action: Annotated[ImportAction | None, Query()] = None,
) -> dict[str, Any]:
    job = await _service(request).get(import_id, user.id, sees_all=_sees_all(user))
    return await _detail(request, job, paging, action)


@router.get("/imports/{importId}/report", operation_id="getImportReport")
async def get_import_report(request: Request, user: Author, import_id: ImportId) -> Response:
    job = await _service(request).get(import_id, user.id, sees_all=_sees_all(user))
    lines = (
        (row.code, row.entity, issue.field, issue.rule.value, issue.message)
        for row in job.rows
        for issue in row.errors
    )
    return _download(write_report(lines), f"reporte-importacion-{job.id}.xlsx")


@router.post("/imports/{importId}/confirmation", operation_id="confirmImport")
async def confirm_import(
    request: Request, user: Author, import_id: ImportId, body: ConfirmationIn
) -> dict[str, Any]:
    job = await _service(request).confirm(
        import_id,
        user.id,
        target_state=VersionState(body.target_state),
        originality_declared=body.originality_declared,
    )
    return await _detail(request, job, PageParams())


@router.get("/export", operation_id="exportItems")
async def export_items(
    request: Request,
    user: Author,
    format: Annotated[Literal["json", "xlsx"], Query()],
    version: Annotated[Literal["published", "latest"], Query()] = "published",
    module: Annotated[Literal["LC", "RC", "CC", "ING", "CE"] | None, Query()] = None,
    state: Annotated[Literal["draft", "in_review", "published", "retired"] | None, Query()] = None,
    origin: Annotated[Literal["seed", "teacher", "ai"] | None, Query()] = None,
    difficulty: Annotated[Literal["low", "medium", "high"] | None, Query()] = None,
    taxonomy_node: Annotated[UUID | None, Query()] = None,
) -> StreamingResponse:
    """El archivo sale en flujo; `X-Skipped-Items` cuenta lo que la plantilla no representa."""
    service: BankExport = request.app.state.content_bank_export
    exported = await service.export(
        ExportRequest(
            format=format,
            version=version,
            module=module,
            state=state,
            origin=origin,
            difficulty=difficulty,
            taxonomy_node=taxonomy_node,
        ),
        user.id,
    )
    return StreamingResponse(
        exported.chunks,
        media_type=exported.media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{exported.filename}"',
            "X-Skipped-Items": str(exported.skipped),
        },
    )
