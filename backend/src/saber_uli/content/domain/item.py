"""Agregado `Item`: código estable, versiones y revisión (FR-008, FR-010 a FR-016; ADR 0008).

El agregado carga la versión publicada y la abierta (y las que cambien en la operación). Toda
transición sube `revision` (el `ETag` de R-09) y deja un `HistoryEvent` pendiente que el
repositorio guarda en la misma transacción. Las huellas las calcula quien llama, porque la del
contenido normalizado depende del texto del contexto (research R-06).
"""

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID

from saber_uli.content.domain.context import Origin
from saber_uli.content.domain.errors import (
    ContentValidationError,
    InvalidTransitionError,
    SelfApprovalError,
)
from saber_uli.content.domain.events import HistoryEvent, HistoryEventType
from saber_uli.content.domain.item_version import ItemContent, ItemKind, ItemVersion, VersionState
from saber_uli.content.domain.lifecycle import Action, target_state
from saber_uli.content.domain.validation import ContentIssue
from saber_uli.shared.domain.errors import RuleViolationError

S = VersionState
H = HistoryEventType


class MissingConfirmationError(RuleViolationError):
    slug = "validation-error"


class MissingCommentError(RuleViolationError):
    slug = "validation-error"


def _required_text(value: str, what: str) -> str:
    if not value or not value.strip():
        raise MissingCommentError(f"Escribe {what}.")
    return value.strip()


@dataclass
class Item:
    id: UUID | None
    code: str
    module_code: str
    kind: ItemKind
    origin: Origin
    versions: list[ItemVersion]
    last_number: int
    revision: int = 0
    seed_hash: bytes | None = None
    created_at: datetime | None = None
    _events: list[HistoryEvent] = field(default_factory=list, repr=False)

    # ------------------------------------------------------------------------ creación

    @classmethod
    def create(
        cls,
        *,
        code: str,
        module_code: str,
        kind: ItemKind,
        origin: Origin,
        content: ItemContent,
        content_hash: bytes,
        fingerprint: bytes,
        context_version_id: UUID | None,
        actor: UUID | None,
        now: datetime,
        state: VersionState = S.DRAFT,
        event_type: HistoryEventType = H.CREATED,
        issues: Sequence[ContentIssue] = (),
        details: dict[str, Any] | None = None,
    ) -> "Item":
        if not state.is_open:
            raise InvalidTransitionError("Un ítem nuevo entra en Borrador o En revisión.")
        if state is S.IN_REVIEW and issues:
            raise ContentValidationError(issues)
        version = ItemVersion(
            id=None,
            number=1,
            state=state,
            content=content,
            content_hash=content_hash,
            fingerprint=fingerprint,
            context_version_id=context_version_id,
            author_id=actor,
            contributor_ids=frozenset() if actor is None else frozenset({actor}),
            created_at=now,
            updated_at=now,
            submitted_at=now if state is S.IN_REVIEW else None,
            submitted_by=actor if state is S.IN_REVIEW else None,
        )
        item = cls(
            id=None,
            code=code,
            module_code=module_code,
            kind=kind,
            origin=origin,
            versions=[version],
            last_number=1,
            created_at=now,
        )
        item._record(event_type, version, actor, now, details=details)
        return item

    # ------------------------------------------------------------------------ consultas

    @property
    def published(self) -> ItemVersion | None:
        return next((v for v in self.versions if v.state is S.PUBLISHED), None)

    @property
    def open(self) -> ItemVersion | None:
        return next((v for v in self.versions if v.state.is_open), None)

    def can_approve(self, person: UUID) -> bool:
        version = self.open
        return version is not None and version.state is S.IN_REVIEW and not version.involves(person)

    def pull_events(self) -> list[HistoryEvent]:
        events, self._events = self._events, []
        return events

    # ------------------------------------------------------------------------ transiciones

    def edit(
        self,
        content: ItemContent,
        content_hash: bytes,
        fingerprint: bytes,
        context_version_id: UUID | None,
        editor: UUID | None,
        now: datetime,
        *,
        keep_in_review: bool = False,
        start_state: VersionState = S.DRAFT,
        issues: Sequence[ContentIssue] = (),
        event_type: HistoryEventType = H.EDITED,
        details: dict[str, Any] | None = None,
    ) -> ItemVersion:
        """Guarda la versión abierta o, si no hay, crea la siguiente (FR-015, FR-016).

        Una versión abierta En revisión vuelve a Borrador salvo `keep_in_review`; una versión
        nueva nace en `start_state`. Quedar En revisión exige contenido sin problemas.
        """
        version = self.open
        if version is None:
            if not start_state.is_open:
                raise InvalidTransitionError("Una versión nueva entra en Borrador o En revisión.")
            if start_state is S.IN_REVIEW and issues:
                raise ContentValidationError(issues)
            self.last_number += 1
            version = ItemVersion(
                id=None,
                number=self.last_number,
                state=start_state,
                content=content,
                content_hash=content_hash,
                fingerprint=fingerprint,
                context_version_id=context_version_id,
                author_id=editor,
                contributor_ids=frozenset() if editor is None else frozenset({editor}),
                created_at=now,
                updated_at=now,
                submitted_at=now if start_state is S.IN_REVIEW else None,
                submitted_by=editor if start_state is S.IN_REVIEW else None,
            )
            self.versions.append(version)
        else:
            new_state = target_state(Action.EDIT, version.state)
            if version.state is S.IN_REVIEW and keep_in_review:
                if issues:
                    raise ContentValidationError(issues)
                new_state = S.IN_REVIEW
                version.submitted_at, version.submitted_by = now, editor
            version.state = new_state
            version.content = content
            version.content_hash = content_hash
            version.fingerprint = fingerprint
            version.context_version_id = context_version_id
            version.updated_at = now
            if editor is not None:
                version.contributor_ids = version.contributor_ids | {editor}
        self._record(event_type, version, editor, now, details=details)
        return version

    def submit(
        self, actor: UUID, now: datetime, *, issues: Sequence[ContentIssue] = ()
    ) -> ItemVersion:
        version = self._open_or_fail(Action.SUBMIT)
        new_state = target_state(Action.SUBMIT, version.state)
        if issues:
            raise ContentValidationError(issues)
        version.state = new_state
        version.submitted_at, version.submitted_by = now, actor
        version.updated_at = now
        self._record(H.SUBMITTED, version, actor, now)
        return version

    def approve(
        self,
        approver: UUID,
        now: datetime,
        *,
        confirms_alignment: bool,
        confirms_originality: bool,
    ) -> ItemVersion:
        version = self._open_or_fail(Action.APPROVE)
        new_state = target_state(Action.APPROVE, version.state)
        if version.involves(approver):
            raise SelfApprovalError(
                "No puedes aprobar una versión que creaste o modificaste: la debe aprobar otro "
                "administrador."
            )
        if not (confirms_alignment and confirms_originality):
            raise MissingConfirmationError(
                "Confirma que verificaste la alineación con la guía del ICFES y que el ítem no "
                "reproduce preguntas del ICFES."
            )
        previous = self.published
        if previous is not None:
            previous.state = S.RETIRED
            previous.retired_at, previous.retired_by = now, approver
            previous.retire_reason = f"Reemplazada por la versión {version.number}."
            previous.updated_at = now
            self._record(H.SUPERSEDED, previous, approver, now, bump=False)
        version.state = new_state
        version.reviewed_at, version.reviewed_by = now, approver
        version.published_at = now
        version.updated_at = now
        self._record(
            H.APPROVED,
            version,
            approver,
            now,
            details={"confirms_alignment": True, "confirms_originality": True},
        )
        return version

    def return_to_draft(self, reviewer: UUID, now: datetime, comment: str) -> ItemVersion:
        version = self._open_or_fail(Action.RETURN)
        new_state = target_state(Action.RETURN, version.state)
        text = _required_text(comment, "el comentario para el autor")
        version.state = new_state
        version.reviewed_at, version.reviewed_by = now, reviewer
        version.updated_at = now
        self._record(H.RETURNED, version, reviewer, now, comment=text)
        return version

    def reject(self, reviewer: UUID, now: datetime, reason: str) -> ItemVersion:
        version = self._open_or_fail(Action.REJECT)
        new_state = target_state(Action.REJECT, version.state)
        text = _required_text(reason, "el motivo del rechazo")
        version.state = new_state
        version.reviewed_at, version.reviewed_by = now, reviewer
        version.retired_at, version.retired_by, version.retire_reason = now, reviewer, text
        version.updated_at = now
        self._record(H.REJECTED, version, reviewer, now, reason=text)
        return version

    def retire(self, actor: UUID, now: datetime, reason: str) -> ItemVersion:
        version, new_state = self._transition(Action.RETIRE, self.published)
        text = _required_text(reason, "el motivo del retiro")
        version.state = new_state
        version.retired_at, version.retired_by, version.retire_reason = now, actor, text
        version.updated_at = now
        self._record(H.RETIRED, version, actor, now, reason=text)
        return version

    def comment(self, actor: UUID, now: datetime, text: str) -> None:
        """Comentario de docente o administrador; no cambia el estado ni la revisión."""
        body = _required_text(text, "el comentario")
        version = self.open or self.published
        self._record(H.COMMENTED, version, actor, now, comment=body, bump=False)

    # ------------------------------------------------------------------------ apoyo

    def _open_or_fail(self, action: Action) -> ItemVersion:
        version, _ = self._transition(action, self.open)
        return version

    @staticmethod
    def _transition(
        action: Action, version: ItemVersion | None
    ) -> tuple[ItemVersion, VersionState]:
        if version is None:
            target_state(action, None)  # lanza InvalidTransitionError
            raise InvalidTransitionError("No hay versión para esta acción.")  # pragma: no cover
        return version, target_state(action, version.state)

    def _record(
        self,
        event_type: HistoryEventType,
        version: ItemVersion | None,
        actor: UUID | None,
        now: datetime,
        *,
        comment: str | None = None,
        reason: str | None = None,
        details: dict[str, Any] | None = None,
        bump: bool = True,
    ) -> None:
        if bump and event_type is not H.CREATED:
            self.revision += 1
        self._events.append(
            HistoryEvent(
                type=event_type,
                version_number=None if version is None else version.number,
                actor_id=actor,
                occurred_at=now,
                comment=comment,
                reason=reason,
                details=details or {},
            )
        )
