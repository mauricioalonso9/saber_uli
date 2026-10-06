"""T018: los logs no contienen datos personales (principio V, FR-036, research R-23)."""

import json
import logging
from typing import Any

import pytest
import structlog

from saber_uli.shared.infrastructure.logging import (
    REDACTED,
    REDACTED_EMAIL,
    configure_logging,
    scrub_personal_data,
)


def scrub(**event: Any) -> dict[str, Any]:
    return scrub_personal_data(None, "info", event)


@pytest.mark.parametrize(
    "key",
    [
        "email",
        "name",
        "correo",
        "nombre",
        "token",
        "authorization",
        "cookie",
        "code",
        "display_name",
    ],
)
def test_enmascara_las_claves_sensibles(key: str) -> None:
    assert scrub(event="x", **{key: "valor-sensible"})[key] == REDACTED


@pytest.mark.parametrize(
    "key",
    ["Email", "AUTHORIZATION", "Set-Cookie", "access_token", "refresh_token", "user_email"],
)
def test_las_variantes_de_las_claves_sensibles_tambien_se_enmascaran(key: str) -> None:
    assert scrub(event="x", **{key: "valor-sensible"})[key] == REDACTED


@pytest.mark.parametrize("key", ["status_code", "program_name", "event_name", "user_id"])
def test_no_enmascara_claves_tecnicas_que_solo_se_parecen(key: str) -> None:
    assert scrub(event="x", **{key: 200})[key] == 200


def test_enmascara_valores_con_forma_de_correo_en_cualquier_clave() -> None:
    result = scrub(event="envío a Ana.Perez+x@unilibre.edu.co falló", destinatario="a@b.co")

    assert result["event"] == f"envío a {REDACTED_EMAIL} falló"
    assert result["destinatario"] == REDACTED_EMAIL


def test_revisa_estructuras_anidadas() -> None:
    result = scrub(
        event="x",
        details={"roles": ["student"], "user": {"email": "a@b.co", "id": "u1"}},
        destinos=["c@d.org", ("e@f.net", 3)],
    )

    assert result["details"] == {"roles": ["student"], "user": {"email": REDACTED, "id": "u1"}}
    assert result["destinos"] == [REDACTED_EMAIL, (REDACTED_EMAIL, 3)]


def test_conserva_los_datos_permitidos() -> None:
    event = {
        "event": "auth.login_rejected",
        "cause": "tenant_not_allowed",
        "user_id": "0192f3c4-0000-7000-8000-000000000000",
        "status_code": 302,
    }

    assert scrub(**event) == event


@pytest.fixture
def json_logs(capsys: pytest.CaptureFixture[str]) -> Any:
    configure_logging(level="INFO")

    def read() -> list[dict[str, Any]]:
        out = capsys.readouterr().out
        return [json.loads(line) for line in out.splitlines() if line.strip()]

    yield read
    structlog.reset_defaults()
    logging.getLogger().handlers.clear()


def test_structlog_emite_json_una_linea_por_evento_y_sin_datos_personales(json_logs: Any) -> None:
    structlog.get_logger("saber_uli.test").info(
        "auth.login", user_id="u1", email="ana@unilibre.edu.co", token="t0k3n"
    )

    [line] = json_logs()
    assert line["event"] == "auth.login"
    assert line["level"] == "info"
    assert line["user_id"] == "u1"
    assert line["email"] == REDACTED
    assert line["token"] == REDACTED
    assert "timestamp" in line


def test_los_logs_de_la_libreria_estandar_tambien_salen_en_json_y_limpios(
    json_logs: Any,
) -> None:
    logging.getLogger("uvicorn.error").warning("cliente ana@unilibre.edu.co desconectado")

    [line] = json_logs()
    assert line["event"] == f"cliente {REDACTED_EMAIL} desconectado"
    assert line["level"] == "warning"
    assert line["logger"] == "uvicorn.error"


def test_las_excepciones_se_limpian_despues_de_formatearse(json_logs: Any) -> None:
    try:
        raise ValueError("correo inválido: ana@unilibre.edu.co")
    except ValueError:
        structlog.get_logger().exception("fallo")

    [line] = json_logs()
    assert "ana@unilibre.edu.co" not in json.dumps(line)
    assert REDACTED_EMAIL in line["exception"]


def test_respeta_el_nivel_configurado(json_logs: Any) -> None:
    structlog.get_logger().debug("detalle")
    logging.getLogger("saber_uli").debug("detalle")

    assert json_logs() == []
