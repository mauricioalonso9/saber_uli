"""Eventos de dominio (research R-08; data-model §6)."""

import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, ClassVar
from uuid import UUID, uuid4

_EVENT_TYPE = re.compile(r"^[a-z]+\.[A-Z][A-Za-z]+$")


@dataclass(frozen=True, kw_only=True)
class DomainEvent:
    """Base de los eventos de dominio.

    `occurred_at` es obligatorio y en UTC: quien crea el evento lo toma de un `Clock`. Cada
    subclase declara `event_type` con el formato `<contexto>.<NombreEnPascal>`. Los eventos llevan
    solo identificadores, nunca datos personales.
    """

    event_type: ClassVar[str]

    occurred_at: datetime
    event_id: UUID = field(default_factory=uuid4)

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        event_type = cls.__dict__.get("event_type")
        if not isinstance(event_type, str) or not _EVENT_TYPE.fullmatch(event_type):
            raise TypeError(
                f"{cls.__name__} debe declarar event_type con el formato "
                "'<contexto>.<NombreEnPascal>', por ejemplo 'identity.UserErased'"
            )

    def __post_init__(self) -> None:
        if self.occurred_at.tzinfo is None or self.occurred_at.utcoffset() != timedelta(0):
            raise ValueError("occurred_at debe ser una fecha en UTC con zona horaria")
