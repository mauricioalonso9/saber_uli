"""Puertos del contexto `notifications` (research R-30)."""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class RenderedEmail:
    subject: str
    html: str
    text: str


@dataclass(frozen=True)
class OutgoingEmail:
    to: str
    subject: str
    html: str
    text: str


class TemplateRenderer(Protocol):
    def render(self, template: str, context: Mapping[str, Any]) -> RenderedEmail:
        """Lanza `LookupError` si la plantilla no existe."""
        ...


class EmailSender(Protocol):
    async def send(self, email: OutgoingEmail) -> None: ...
