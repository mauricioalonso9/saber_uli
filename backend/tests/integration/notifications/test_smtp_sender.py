"""T037: envío real a Mailpit, verificado por su API (research R-30)."""

import time
from collections.abc import Iterator
from typing import Any

import httpx
import pytest
from structlog.testing import capture_logs
from testcontainers.core.container import DockerContainer

from saber_uli.notifications.application.public import EmailService
from saber_uli.notifications.infrastructure.smtp import SmtpEmailSender
from saber_uli.notifications.infrastructure.templates import JinjaTemplateRenderer

RECIPIENT = "ana.perez@unilibre.edu.co"


@pytest.fixture(scope="module")
def mailpit() -> Iterator[tuple[str, int, str]]:
    container = DockerContainer("axllent/mailpit:v1.31").with_exposed_ports(1025, 8025)
    with container:
        host = container.get_container_host_ip()
        api = f"http://{host}:{container.get_exposed_port(8025)}"
        deadline = time.monotonic() + 30
        while True:
            try:
                if httpx.get(f"{api}/readyz", timeout=2).status_code == 200:
                    break
            except httpx.HTTPError:
                pass
            if time.monotonic() > deadline:
                raise TimeoutError("Mailpit no arrancó")
            time.sleep(0.5)
        yield host, int(container.get_exposed_port(1025)), api


def latest(api: str) -> dict[str, Any]:
    messages = httpx.get(f"{api}/api/v1/messages", timeout=5).json()["messages"]
    assert messages, "Mailpit no recibió mensajes"
    detail: dict[str, Any] = httpx.get(
        f"{api}/api/v1/message/{messages[0]['ID']}", timeout=5
    ).json()
    return detail


async def test_envio_real_html_y_texto_sin_destinatario_en_los_logs(
    mailpit: tuple[str, int, str],
) -> None:
    host, port, api = mailpit
    service = EmailService(
        renderer=JinjaTemplateRenderer(public_base_url="https://saber.unilibre.edu.co"),
        sender=SmtpEmailSender(
            host=host,
            port=port,
            sender="Saber Uli <no-responder@unilibre.edu.co>",
            starttls=False,
        ),
    )

    with capture_logs() as logs:
        await service.send_email(
            "aviso",
            RECIPIENT,
            {
                "title": "Tu acceso a Saber Uli",
                "paragraphs": ["Ya puedes practicar."],
                "action_path": "/ingresar",
                "action_label": "Ingresar",
            },
        )

    message = latest(api)
    assert [to["Address"] for to in message["To"]] == [RECIPIENT]
    assert message["From"]["Address"] == "no-responder@unilibre.edu.co"
    assert message["Subject"] == "Tu acceso a Saber Uli"
    assert "https://saber.unilibre.edu.co/ingresar" in message["HTML"]
    assert "https://saber.unilibre.edu.co/ingresar" in message["Text"]

    assert [entry["event"] for entry in logs] == ["email_sent"]
    assert logs[0]["template"] == "aviso"
    assert RECIPIENT not in repr(logs)


async def test_un_destinatario_con_salto_de_linea_se_rechaza(
    mailpit: tuple[str, int, str],
) -> None:
    host, port, _ = mailpit
    sender = SmtpEmailSender(
        host=host, port=port, sender="no-responder@unilibre.edu.co", starttls=False
    )
    service = EmailService(
        renderer=JinjaTemplateRenderer(public_base_url="https://saber.unilibre.edu.co"),
        sender=sender,
    )

    with pytest.raises(ValueError):
        await service.send_email(
            "aviso",
            "ana@unilibre.edu.co\r\nBcc: x@evil.com",
            {"title": "x", "paragraphs": [], "action_path": "/", "action_label": "x"},
        )
