"""Logs JSON sin datos personales (principio V, FR-036, research R-23).

Todos los registros, los de structlog y los de la librería estándar (uvicorn, SQLAlchemy,
Celery), salen por un único manejador en formato JSON, una línea por evento. El último procesador
antes de renderizar es `scrub_personal_data`: enmascara las claves sensibles, los valores con
forma de correo y los parámetros sensibles de las URL, en cualquier nivel de anidación y también
en el texto de las excepciones ya formateadas.
"""

import logging
import re
import sys
from collections.abc import MutableMapping
from typing import Any, TextIO

import structlog
from structlog.typing import EventDict, Processor, WrappedLogger

REDACTED = "[REDACTED]"
REDACTED_EMAIL = "[REDACTED_EMAIL]"

# Claves que se enmascaran si coinciden exactamente (tras normalizar mayúsculas y guiones).
_EXACT_KEYS = frozenset(
    {
        "email",
        "name",
        "correo",
        "nombre",
        "token",
        "authorization",
        "cookie",
        "code",
        "display_name",
        "given_name",
        "family_name",
        "first_name",
        "last_name",
        "full_name",
        "preferred_username",
        "password",
        "secret",
        "state",
        "nonce",
        "code_verifier",
    }
)
# Fragmentos que delatan un dato sensible dentro de una clave compuesta (`user_email`,
# `refresh_token`, `set_cookie`). `name` y `code` no van aquí: `status_code` o `program_name`
# son datos técnicos.
_KEY_FRAGMENTS = ("email", "correo", "token", "cookie", "authorization", "password", "secret")

_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9\-]+(?:\.[A-Za-z0-9\-]+)*\.[A-Za-z]{2,}")
_QUERY_PARAM_RE = re.compile(r"(?P<prefix>[?&;](?P<key>[A-Za-z0-9_\-]+)=)(?P<value>[^&;#\s\"']*)")


def _is_sensitive_key(key: object) -> bool:
    if not isinstance(key, str):
        return False
    normalized = key.lower().replace("-", "_")
    return normalized in _EXACT_KEYS or any(f in normalized for f in _KEY_FRAGMENTS)


def _scrub_text(text: str) -> str:
    def mask_param(match: re.Match[str]) -> str:
        if _is_sensitive_key(match["key"]):
            return f"{match['prefix']}{REDACTED}"
        return match[0]

    return _EMAIL_RE.sub(REDACTED_EMAIL, _QUERY_PARAM_RE.sub(mask_param, text))


def _scrub_value(value: Any) -> Any:
    if isinstance(value, str):
        return _scrub_text(value)
    if isinstance(value, MutableMapping):
        return {k: REDACTED if _is_sensitive_key(k) else _scrub_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_scrub_value(v) for v in value]
    if isinstance(value, tuple):
        return tuple(_scrub_value(v) for v in value)
    if isinstance(value, (set, frozenset)):
        return {_scrub_value(v) for v in value}
    return value


def scrub_personal_data(
    _logger: WrappedLogger, _method_name: str, event_dict: EventDict
) -> EventDict:
    """Procesador de structlog: devuelve el evento sin datos personales ni secretos."""
    return {
        key: REDACTED if _is_sensitive_key(key) else _scrub_value(value)
        for key, value in event_dict.items()
    }


# Procesadores comunes a structlog y a la librería estándar (antes de formatear).
_SHARED_PROCESSORS: list[Processor] = [
    structlog.contextvars.merge_contextvars,
    structlog.stdlib.add_log_level,
    structlog.stdlib.add_logger_name,
    structlog.processors.TimeStamper(fmt="iso", utc=True),
    structlog.processors.StackInfoRenderer(),
]

# Loggers de uvicorn: traen sus propios manejadores; se redirigen al manejador JSON.
_THIRD_PARTY_LOGGERS = ("uvicorn", "uvicorn.error", "uvicorn.access")


def configure_logging(level: str = "INFO", stream: TextIO | None = None) -> None:
    """Configura structlog y la librería estándar para emitir JSON limpio.

    Por defecto escribe en la salida estándar (la recogen Docker y el colector de logs).
    """
    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=_SHARED_PROCESSORS,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.processors.format_exc_info,
            scrub_personal_data,  # siempre el último antes de renderizar
            structlog.processors.JSONRenderer(ensure_ascii=False),
        ],
    )
    handler = logging.StreamHandler(stream or sys.stdout)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level.upper())

    for name in _THIRD_PARTY_LOGGERS:
        third_party = logging.getLogger(name)
        third_party.handlers.clear()
        third_party.propagate = True

    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            *_SHARED_PROCESSORS,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
