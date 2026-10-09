"""Máquina de estados de una versión de ítem (data-model §4; FR-010).

```text
draft ──enviar──▶ in_review ──aprobar──▶ published ──retirar──▶ retired
  ▲                │   │                                         ▲
  └──devolver──────┘   └──────────────rechazar───────────────────┘
```

Editar lo publicado o lo retirado no es una transición de esa versión: crea otra (FR-015). La
tabla solo dice qué acción se permite desde qué estado; las demás reglas (autoaprobación,
confirmaciones, comentario o motivo) las aplica `Item`.
"""

from enum import StrEnum

from saber_uli.content.domain.errors import InvalidTransitionError
from saber_uli.content.domain.item_version import VersionState

S = VersionState


class Action(StrEnum):
    EDIT = "edit"
    SUBMIT = "submit"
    APPROVE = "approve"
    RETURN = "return"
    REJECT = "reject"
    RETIRE = "retire"


TRANSITIONS: dict[tuple[Action, VersionState], VersionState] = {
    (Action.EDIT, S.DRAFT): S.DRAFT,
    (Action.EDIT, S.IN_REVIEW): S.DRAFT,  # o sigue en revisión si el docente lo elige (FR-016)
    (Action.SUBMIT, S.DRAFT): S.IN_REVIEW,
    (Action.APPROVE, S.IN_REVIEW): S.PUBLISHED,
    (Action.RETURN, S.IN_REVIEW): S.DRAFT,
    (Action.REJECT, S.IN_REVIEW): S.RETIRED,
    (Action.RETIRE, S.PUBLISHED): S.RETIRED,
}

_NAMES = {
    Action.EDIT: "editar",
    Action.SUBMIT: "enviar a revisión",
    Action.APPROVE: "aprobar",
    Action.RETURN: "devolver",
    Action.REJECT: "rechazar",
    Action.RETIRE: "retirar",
}


def target_state(action: Action, current: VersionState | None) -> VersionState:
    """Estado al que lleva la acción, o `InvalidTransitionError` si no aplica."""
    if current is None or (action, current) not in TRANSITIONS:
        raise InvalidTransitionError(f"No se puede {_NAMES[action]} un ítem en su estado actual.")
    return TRANSITIONS[(action, current)]
