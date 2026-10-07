"""Lotes de invitaciones (FR-009; escenario 5.2; SC-005).

Validar guarda el reporte por fila y deja el lote 24 horas pendiente; confirmar crea solo las
filas válidas, cada una con su evento `InvitationCreated` para que el worker envíe el correo. Un
docente solo ve y confirma sus lotes.
"""

from collections.abc import Callable, Sequence
from datetime import datetime
from uuid import UUID

from saber_uli.identity.application.audit import AuditAction, AuditTarget, record_audit
from saber_uli.identity.application.invitations import Inviter
from saber_uli.identity.application.unit_of_work import IdentityUnitOfWork
from saber_uli.identity.domain.events import InvitationCreated
from saber_uli.identity.domain.invitation import (
    AccessExpiryOutOfRangeError,
    Invitation,
    InvitationAlreadyActiveError,
    validate_access_expiry,
)
from saber_uli.identity.domain.invitation_batch import (
    BatchRowInput,
    InvitationBatch,
    RowResult,
)
from saber_uli.shared.domain.clock import Clock
from saber_uli.shared.domain.errors import NotFoundError


class BatchNotFoundError(NotFoundError):
    slug = "not-found"


class InvitationBatchService:
    def __init__(
        self,
        *,
        uow_factory: Callable[[], IdentityUnitOfWork],
        clock: Clock,
        institutional_domains: Sequence[str],
    ) -> None:
        self._uow_factory = uow_factory
        self._clock = clock
        self._domains = tuple(institutional_domains)

    async def validate(
        self,
        inviter: Inviter,
        rows: Sequence[BatchRowInput],
        *,
        default_access_expires_at: datetime | None = None,
    ) -> InvitationBatch:
        now = self._clock.now()
        async with self._uow_factory() as uow:
            batch = InvitationBatch.validate(
                rows,
                created_by=inviter.user_id,
                is_admin=inviter.is_admin,
                existing_emails=await uow.invitations.active_emails([r.email for r in rows]),
                institutional_domains=self._domains,
                settings=await uow.settings.load(),
                now=now,
                default_access_expires_at=default_access_expires_at,
            )
            await uow.invitation_batches.add(batch)
            await uow.commit()
        return batch

    async def get(self, inviter: Inviter, batch_id: UUID) -> InvitationBatch:
        async with self._uow_factory() as uow:
            return _visible(await uow.invitation_batches.get(batch_id), inviter)

    async def confirm(self, inviter: Inviter, batch_id: UUID) -> InvitationBatch:
        now = self._clock.now()
        async with self._uow_factory() as uow:
            batch = _visible(await uow.invitation_batches.get_for_update(batch_id), inviter)
            batch.confirm(now)
            settings = await uow.settings.load()
            created = 0
            for row in batch.valid_rows():
                if row.access_expires_at is None:  # pragma: no cover - siempre se completa
                    continue
                try:
                    # El lote pudo esperar hasta 24 h: se vuelve a comprobar cada fila.
                    validate_access_expiry(
                        row.access_expires_at,
                        now=now,
                        is_admin=inviter.is_admin,
                        settings=settings,
                    )
                    if await uow.invitations.find_active_by_email(row.email) is not None:
                        raise InvitationAlreadyActiveError("ya invitada")
                except AccessExpiryOutOfRangeError as error:
                    batch.reject_row(row.line, RowResult.EXPIRY_OUT_OF_RANGE, error.message)
                    continue
                except InvitationAlreadyActiveError:
                    batch.reject_row(row.line, RowResult.ALREADY_INVITED)
                    continue
                invitation = await uow.invitations.add(
                    Invitation.create(
                        email=row.email,
                        invited_by=inviter.user_id,
                        access_expires_at=row.access_expires_at,
                        now=now,
                        invitee_name=row.name,
                        batch_id=batch_id,
                    )
                )
                if invitation.id is None:  # pragma: no cover - el repositorio asigna el id
                    raise ValueError("la invitación no se guardó")
                await record_audit(
                    uow,
                    AuditAction.INVITATION_CREATED,
                    target=AuditTarget.INVITATION,
                    target_id=invitation.id,
                    actor_id=inviter.user_id,
                    details={
                        "access_expires_at": row.access_expires_at.isoformat(),
                        "batch_id": str(batch_id),
                    },
                    now=now,
                )
                uow.record(InvitationCreated(invitation_id=invitation.id, occurred_at=now))
                created += 1
            await uow.invitation_batches.save(batch)
            await record_audit(
                uow,
                AuditAction.INVITATION_BATCH_CONFIRMED,
                target=AuditTarget.INVITATION,
                target_id=batch_id,
                actor_id=inviter.user_id,
                details={"created": created, "rejected": batch.invalid_count},
                now=now,
            )
            await uow.commit()
        return batch


def _visible(batch: InvitationBatch | None, inviter: Inviter) -> InvitationBatch:
    if batch is None or (not inviter.is_admin and batch.created_by != inviter.user_id):
        raise BatchNotFoundError("El lote no existe.")
    return batch
