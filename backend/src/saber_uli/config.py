"""Configuración por entorno (12-factor; research R-11, R-14, R-20, R-32).

Compose inyecta las variables; no se lee ningún archivo `.env`. Los secretos son `SecretStr` y
nunca aparecen en `repr`, `str` ni en la serialización. Si la configuración es inválida,
`get_settings()` lanza `ConfigError`, que nombra cada variable fallida **sin** mostrar el valor
recibido (podría ser un secreto). El dominio no importa este módulo: la aplicación recibe los
valores por inyección.
"""

import re
from functools import lru_cache
from typing import Annotated, Any, Literal
from urllib.parse import urlsplit
from uuid import UUID

from pydantic import Field, SecretStr, ValidationError, ValidationInfo, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

# Hosts donde se admite HTTP: el equipo local y el proveedor OIDC simulado del perfil e2e.
_LOCAL_HOSTS = frozenset({"localhost", "127.0.0.1"})
_TEST_OIDC_HOSTS = _LOCAL_HOSTS | {"oidc"}
# Autoridades multiinquilino de Entra ID: nunca se usan (R-11).
_MULTITENANT_SEGMENTS = frozenset({"common", "organizations", "consumers"})
_DOMAIN = re.compile(r"^(?=.{1,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$")
_EMAIL = re.compile(r"^[^@\s<>]+@[^@\s<>]+\.[^@\s<>]+$")
_SENDER = re.compile(r"^(?:[^<>]*<(?P<bracketed>[^<>]+)>|(?P<plain>[^<>\s]+))$")
_MIN_SECRET_LENGTH = 32  # 256 bits (R-14)
# Contraseña de ejemplo de `.env.example`: se admite en localhost (desarrollo, e2e y CI) pero no
# en producción (ASVS 2.10.2, T178c).
_EXAMPLE_PASSWORD = "cambie-esta-contrasena"  # noqa: S105 - valor a rechazar, no una credencial


class ConfigError(Exception):
    """Configuración inválida o incompleta; el mensaje no incluye valores recibidos."""

    @classmethod
    def from_validation_error(cls, error: ValidationError) -> "ConfigError":
        lines = []
        for item in error.errors(include_input=False, include_url=False, include_context=False):
            variable = str(item["loc"][0]).upper() if item["loc"] else "CONFIGURACIÓN"
            if item["type"] == "missing":
                reason = "falta (es obligatoria)"
            else:
                reason = str(item["msg"]).removeprefix("Value error, ")
            lines.append(f"- {variable}: {reason}")
        return cls("Configuración inválida:\n" + "\n".join(lines))


def _http_allowed(url: str, hosts: frozenset[str]) -> bool:
    parts = urlsplit(url)
    if not parts.netloc:
        return False
    return parts.scheme == "https" or (parts.scheme == "http" and parts.hostname in hosts)


def _check_secret_length(value: SecretStr) -> SecretStr:
    if len(value.get_secret_value()) < _MIN_SECRET_LENGTH:
        raise ValueError(f"debe tener al menos {_MIN_SECRET_LENGTH} caracteres (256 bits)")
    return value


def _check_dsn(
    value: SecretStr | None, prefixes: tuple[str, ...], info: ValidationInfo
) -> SecretStr | None:
    if value is None:
        return value
    if not value.get_secret_value().startswith(prefixes):
        raise ValueError(f"debe empezar con {' o '.join(prefixes)}")
    public_url = info.data.get("public_base_url", "")
    production = isinstance(public_url, str) and public_url.startswith("https://")
    if production and urlsplit(value.get_secret_value()).password == _EXAMPLE_PASSWORD:
        raise ValueError("usa la contraseña de ejemplo de .env.example; genere una propia")
    return value


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=None, extra="ignore", case_sensitive=False)

    # Microsoft Entra ID (R-10 a R-13)
    entra_tenant_id: UUID
    entra_client_id: UUID
    entra_client_secret: SecretStr
    entra_authority: str = Field(default="", validate_default=True)

    # Aplicación
    public_base_url: str
    institutional_email_domains: Annotated[list[str], NoDecode]

    # Sesiones (R-14)
    jwt_signing_key: SecretStr
    jwt_key_id: str = Field(pattern=r"^[A-Za-z0-9._-]{1,64}$")
    session_cookie_secret: SecretStr

    # Datos (R-07): `saber_app` para api/worker/beat; `saber_migrator` solo para migrate.
    database_url: SecretStr
    migration_database_url: SecretStr | None = None
    redis_url: SecretStr

    # Correo (R-30)
    smtp_host: str = Field(min_length=1)
    smtp_port: int = Field(default=587, ge=1, le=65535)
    smtp_user: str | None = None
    smtp_password: SecretStr | None = None
    smtp_from: str
    smtp_starttls: bool = True

    # Observabilidad (R-32)
    otel_enabled: bool = False
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    # Reservadas para la spec 009 (notificaciones push)
    vapid_public_key: str | None = None
    vapid_private_key: SecretStr | None = None

    @field_validator("entra_client_secret")
    @classmethod
    def _client_secret_not_empty(cls, value: SecretStr) -> SecretStr:
        if not value.get_secret_value().strip():
            raise ValueError("no puede estar vacío")
        return value

    @field_validator("entra_authority")
    @classmethod
    def _tenant_authority(cls, value: str, info: ValidationInfo) -> str:
        tenant = info.data.get("entra_tenant_id")
        if tenant is None:
            return value  # el error de ENTRA_TENANT_ID ya se reporta aparte
        if not value:
            return f"https://login.microsoftonline.com/{tenant}/v2.0"
        segments = {s.lower() for s in urlsplit(value).path.split("/") if s}
        if segments & _MULTITENANT_SEGMENTS:
            raise ValueError("no puede ser una autoridad multiinquilino (common, organizations)")
        if str(tenant).lower() not in segments:
            raise ValueError("debe ser la autoridad del inquilino de ENTRA_TENANT_ID")
        if not _http_allowed(value, _TEST_OIDC_HOSTS):
            raise ValueError("debe usar https")
        return value

    @field_validator("public_base_url")
    @classmethod
    def _public_url(cls, value: str) -> str:
        if not _http_allowed(value, _LOCAL_HOSTS):
            raise ValueError("debe ser una URL https (http solo en localhost)")
        return value.rstrip("/")

    @field_validator("institutional_email_domains", mode="before")
    @classmethod
    def _domains(cls, value: Any) -> list[str]:
        raw = value.split(",") if isinstance(value, str) else list(value)
        domains: list[str] = []
        for item in raw:
            domain = str(item).strip().lower().removeprefix("@")
            if not domain:
                continue
            if not _DOMAIN.fullmatch(domain):
                raise ValueError("contiene un dominio inválido")
            if domain not in domains:
                domains.append(domain)
        if not domains:
            raise ValueError("debe tener al menos un dominio")
        return domains

    @field_validator("jwt_signing_key", "session_cookie_secret")
    @classmethod
    def _long_secret(cls, value: SecretStr) -> SecretStr:
        return _check_secret_length(value)

    @field_validator("database_url", "migration_database_url")
    @classmethod
    def _postgres_dsn(cls, value: SecretStr | None, info: ValidationInfo) -> SecretStr | None:
        return _check_dsn(value, ("postgresql+asyncpg://",), info)

    @field_validator("redis_url")
    @classmethod
    def _redis_dsn(cls, value: SecretStr, info: ValidationInfo) -> SecretStr:
        _check_dsn(value, ("redis://", "rediss://"), info)
        return value

    @field_validator("smtp_from")
    @classmethod
    def _sender(cls, value: str) -> str:
        match = _SENDER.fullmatch(value.strip())
        address = match and (match["bracketed"] or match["plain"])
        if not address or not _EMAIL.fullmatch(address.strip()):
            raise ValueError("debe ser un correo, opcionalmente con nombre: 'Nombre <correo>'")
        return value.strip()


@lru_cache
def get_settings() -> Settings:
    """Configuración del proceso. Lanza `ConfigError` sin encadenar el error original de
    pydantic, cuyo texto incluye los valores recibidos."""
    try:
        return Settings()  # type: ignore[call-arg]  # los valores llegan del entorno
    except ValidationError as error:
        raise ConfigError.from_validation_error(error) from None
