"""Envío de correo por SMTP con `smtplib` (research R-30).

`smtplib` es síncrono: el envío corre en un hilo para no bloquear el bucle de eventos del
despachador del outbox. El mensaje es `multipart/alternative` (texto y HTML).
"""

import asyncio
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import make_msgid

from saber_uli.notifications.application.ports import OutgoingEmail


class SmtpEmailSender:
    def __init__(
        self,
        *,
        host: str,
        port: int,
        sender: str,
        user: str | None = None,
        password: str | None = None,
        starttls: bool = True,
        timeout: float = 10.0,
    ) -> None:
        self._host = host
        self._port = port
        self._sender = sender
        self._user = user or None
        self._password = password or None
        self._starttls = starttls
        self._timeout = timeout

    def _build(self, email: OutgoingEmail) -> EmailMessage:
        message = EmailMessage()
        message["From"] = self._sender
        message["To"] = email.to
        message["Subject"] = email.subject
        message["Message-ID"] = make_msgid(domain=self._sender.rsplit("@", 1)[-1].strip("> "))
        message.set_content(email.text)
        message.add_alternative(email.html, subtype="html")
        return message

    def _send_blocking(self, email: OutgoingEmail) -> None:
        message = self._build(email)
        with smtplib.SMTP(self._host, self._port, timeout=self._timeout) as smtp:
            if self._starttls:
                smtp.starttls(context=ssl.create_default_context())
            if self._user and self._password:
                smtp.login(self._user, self._password)
            smtp.send_message(message)

    async def send(self, email: OutgoingEmail) -> None:
        await asyncio.to_thread(self._send_blocking, email)
