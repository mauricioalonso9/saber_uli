"""Autorización de datos y versiones de la política (FR-014 a FR-018; escenarios 2.1 a 2.5).

- Decidir: la persona acepta o no acepta la versión vigente; queda el usuario, la fecha, la
  versión, la decisión y el canal (FR-015).
- Revocar: registra la revocación e invalida todas sus sesiones (`auth_epoch` + 1): la siguiente
  petición responde 401 (escenario 2.5).
- Publicar: un administrador con sesión privilegiada publica una versión nueva; al empezar a
  regir, todos deben volver a autorizar (FR-017).

Todo queda en la auditoría (`consent.accepted|rejected|revoked`, `policy.published`), solo con
identificadores y el número de versión.
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from saber_uli.identity.application.audit import AuditAction, AuditTarget, record_audit
from saber_uli.identity.application.ports import ConsentEntry
from saber_uli.identity.application.unit_of_work import IdentityUnitOfWork
from saber_uli.identity.domain.consent import (
    ConsentDecision,
    decide_consent,
    revoke_consent,
)
from saber_uli.identity.domain.events import UserAccessChanged
from saber_uli.identity.domain.policy import PolicyVersion
from saber_uli.shared.domain.clock import Clock
from saber_uli.shared.domain.errors import NotFoundError, UnauthenticatedError

_AUDIT_ACTION = {
    ConsentDecision.ACCEPTED: AuditAction.CONSENT_ACCEPTED,
    ConsentDecision.REJECTED: AuditAction.CONSENT_REJECTED,
    ConsentDecision.REVOKED: AuditAction.CONSENT_REVOKED,
}


class PolicyVersionNotFoundError(NotFoundError):
    slug = "not-found"


@dataclass(frozen=True)
class ConsentHistory:
    current: ConsentEntry | None
    items: list[ConsentEntry]


class ConsentService:
    def __init__(self, *, uow_factory: Callable[[], IdentityUnitOfWork], clock: Clock) -> None:
        self._uow_factory = uow_factory
        self._clock = clock

    async def history(self, user_id: UUID) -> ConsentHistory:
        async with self._uow_factory() as uow:
            current_version = await uow.consents.current_policy_version_id(now=self._clock.now())
            items = await uow.consents.history_for_user(user_id)
        latest = items[0] if items else None
        current = (
            latest
            if latest is not None
            and latest.decision is ConsentDecision.ACCEPTED
            and latest.policy_version_id == current_version
            else None
        )
        return ConsentHistory(current=current, items=items)

    async def decide(
        self, user_id: UUID, *, policy_version_id: UUID, decision: ConsentDecision
    ) -> ConsentEntry:
        now = self._clock.now()
        async with self._uow_factory() as uow:
            record = decide_consent(
                decision,
                policy_version_id=policy_version_id,
                current_policy_version_id=await uow.consents.current_policy_version_id(now=now),
                now=now,
            )
            entry = await uow.consents.add(user_id, record)
            await self._audit(uow, entry, user_id, now)
            await uow.commit()
        return entry

    async def revoke(self, user_id: UUID) -> ConsentEntry:
        now = self._clock.now()
        async with self._uow_factory() as uow:
            user = await uow.users.get(user_id)
            if user is None:
                raise UnauthenticatedError("La sesión no es válida.")
            record = revoke_consent(
                await uow.consents.latest_for_user(user_id),
                current_policy_version_id=await uow.consents.current_policy_version_id(now=now),
                now=now,
            )
            entry = await uow.consents.add(user_id, record)
            # Sin autorización no hay acceso: se cierran todas las sesiones (R-16).
            user.invalidate_sessions()
            await uow.users.save(user)
            await uow.sessions.revoke_all_for_user(user_id, now=now, reason="access_changed")
            uow.record(UserAccessChanged(user_id=user_id, occurred_at=now))
            await self._audit(uow, entry, user_id, now)
            await uow.commit()
        return entry

    @staticmethod
    async def _audit(
        uow: IdentityUnitOfWork, entry: ConsentEntry, user_id: UUID, now: datetime
    ) -> None:
        await record_audit(
            uow,
            _AUDIT_ACTION[entry.decision],
            target=AuditTarget.POLICY,
            target_id=entry.policy_version_id,
            subject_user_id=user_id,
            actor_id=user_id,
            details={"policy_version": entry.policy_version},
            now=now,
        )


class PrivacyPolicyService:
    def __init__(self, *, uow_factory: Callable[[], IdentityUnitOfWork], clock: Clock) -> None:
        self._uow_factory = uow_factory
        self._clock = clock

    async def current(self) -> PolicyVersion:
        async with self._uow_factory() as uow:
            version = await uow.policies.current(now=self._clock.now())
        if version is None:
            raise PolicyVersionNotFoundError("Todavía no hay una política publicada.")
        return version

    async def get(self, version_id: UUID) -> PolicyVersion:
        async with self._uow_factory() as uow:
            version = await uow.policies.get(version_id)
        if version is None:
            raise PolicyVersionNotFoundError("La versión de la política no existe.")
        return version

    async def publish(
        self,
        actor_id: UUID,
        *,
        version: str,
        title: str,
        body_markdown: str,
        effective_from: datetime,
    ) -> PolicyVersion:
        now = self._clock.now()
        async with self._uow_factory() as uow:
            published = await uow.policies.add(
                PolicyVersion.publish(
                    version=version,
                    title=title,
                    body_markdown=body_markdown,
                    effective_from=effective_from,
                    published_by=actor_id,
                    existing_versions=await uow.policies.versions(),
                )
            )
            await record_audit(
                uow,
                AuditAction.POLICY_PUBLISHED,
                target=AuditTarget.POLICY,
                target_id=published.id,
                actor_id=actor_id,
                details={"version": published.version},
                now=now,
            )
            await uow.commit()
        return published
