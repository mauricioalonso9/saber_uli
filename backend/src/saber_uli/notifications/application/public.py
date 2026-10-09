"""Fachada pública del contexto `notifications` (research R-04, R-30).

Es lo único que otros contextos pueden importar de `notifications`. `EmailService` lo arma la
raíz de composición (el worker) con el renderizador de plantillas y el adaptador SMTP; los
manejadores del outbox de `identity` (US4, US7) lo usan para enviar invitaciones, enlaces y
avisos. El correo destino nunca aparece en los logs.
"""

import re
from collections.abc import Mapping
from typing import Any

import structlog

from saber_uli.notifications.application.ports import (
    EmailSender,
    OutgoingEmail,
    TemplateRenderer,
)

_log = structlog.get_logger(__name__)
_ADDRESS = re.compile(r"^[^@\s<>,;]+@[^@\s<>,;]+\.[^@\s<>,;]+$")


class EmailService:
    def __init__(self, *, renderer: TemplateRenderer, sender: EmailSender) -> None:
        self._renderer = renderer
        self._sender = sender

    async def send_email(self, template: str, to: str, context: Mapping[str, Any]) -> None:
        """Renderiza `template` con `context` y lo envía a `to` (una sola dirección)."""
        address = to.strip()
        if not _ADDRESS.fullmatch(address):
            raise ValueError("dirección de correo inválida")
        rendered = self._renderer.render(template, context)
        await self._sender.send(
            OutgoingEmail(
                to=address, subject=rendered.subject, html=rendered.html, text=rendered.text
            )
        )
        _log.info("email_sent", template=template)
