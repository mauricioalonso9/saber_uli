"""T016: configuración por entorno (12-factor; research R-11, R-14, R-20)."""

from collections.abc import Iterator
from uuid import UUID

import pytest

from saber_uli.config import ConfigError, Settings, get_settings

TENANT = "11111111-1111-4111-8111-111111111111"
OTHER_TENANT = "22222222-2222-4222-8222-222222222222"
CLIENT = "33333333-3333-4333-8333-333333333333"

DB_PASSWORD = "contrasena-app-de-prueba-muy-larga"
REDIS_PASSWORD = "contrasena-redis-de-prueba"
JWT_KEY = "k" * 48
COOKIE_SECRET = "c" * 48
CLIENT_SECRET = "secreto-de-entra-id"

VALID_ENV = {
    "ENTRA_TENANT_ID": TENANT,
    "ENTRA_CLIENT_ID": CLIENT,
    "ENTRA_CLIENT_SECRET": CLIENT_SECRET,
    "PUBLIC_BASE_URL": "https://saber.unilibre.edu.co/",
    "INSTITUTIONAL_EMAIL_DOMAINS": "unilibre.edu.co",
    "JWT_SIGNING_KEY": JWT_KEY,
    "JWT_KEY_ID": "2026-10",
    "SESSION_COOKIE_SECRET": COOKIE_SECRET,
    "DATABASE_URL": f"postgresql+asyncpg://saber_app:{DB_PASSWORD}@db:5432/saber_uli",
    "REDIS_URL": f"redis://:{REDIS_PASSWORD}@redis:6379/0",
    "SMTP_HOST": "smtp.unilibre.edu.co",
    "SMTP_FROM": "Saber Uli <no-responder@unilibre.edu.co>",
}

ALL_VARS = [
    *VALID_ENV,
    "ENTRA_AUTHORITY",
    "MIGRATION_DATABASE_URL",
    "SMTP_PORT",
    "SMTP_USER",
    "SMTP_PASSWORD",
    "SMTP_STARTTLS",
    "OTEL_ENABLED",
    "LOG_LEVEL",
    "VAPID_PUBLIC_KEY",
    "VAPID_PRIVATE_KEY",
]


@pytest.fixture
def env(monkeypatch: pytest.MonkeyPatch) -> Iterator[pytest.MonkeyPatch]:
    for name in ALL_VARS:
        monkeypatch.delenv(name, raising=False)
    for name, value in VALID_ENV.items():
        monkeypatch.setenv(name, value)
    get_settings.cache_clear()
    yield monkeypatch
    get_settings.cache_clear()


def load(env: pytest.MonkeyPatch, **overrides: str) -> Settings:
    for name, value in overrides.items():
        env.setenv(name, value)
    return get_settings()


def config_error(env: pytest.MonkeyPatch, **overrides: str) -> str:
    with pytest.raises(ConfigError) as info:
        load(env, **overrides)
    return str(info.value)


def test_carga_un_entorno_valido_con_tipos_y_valores_por_defecto(env: pytest.MonkeyPatch) -> None:
    settings = load(env)

    assert settings.entra_tenant_id == UUID(TENANT)
    assert settings.entra_client_id == UUID(CLIENT)
    assert settings.institutional_email_domains == ["unilibre.edu.co"]
    assert settings.migration_database_url is None
    assert settings.smtp_port == 587
    assert settings.smtp_user is None
    assert settings.smtp_password is None
    assert settings.smtp_starttls is True
    assert settings.otel_enabled is False
    assert settings.log_level == "INFO"
    assert settings.vapid_public_key is None
    assert settings.vapid_private_key is None


def test_get_settings_se_cachea(env: pytest.MonkeyPatch) -> None:
    assert get_settings() is get_settings()


def test_tipos_de_valores_explicitos(env: pytest.MonkeyPatch) -> None:
    settings = load(
        env, SMTP_PORT="1025", SMTP_STARTTLS="false", OTEL_ENABLED="true", LOG_LEVEL="DEBUG"
    )

    assert settings.smtp_port == 1025
    assert settings.smtp_starttls is False
    assert settings.otel_enabled is True
    assert settings.log_level == "DEBUG"


@pytest.mark.parametrize("port", ["0", "65536", "abc"])
def test_smtp_port_fuera_de_rango(env: pytest.MonkeyPatch, port: str) -> None:
    assert "SMTP_PORT" in config_error(env, SMTP_PORT=port)


# --- Autoridad de Entra ID (R-11) --------------------------------------------------------------


def test_la_autoridad_por_defecto_es_la_del_inquilino(env: pytest.MonkeyPatch) -> None:
    assert load(env).entra_authority == f"https://login.microsoftonline.com/{TENANT}/v2.0"


@pytest.mark.parametrize(
    "authority",
    [
        "https://login.microsoftonline.com/common/v2.0",
        "https://login.microsoftonline.com/organizations/v2.0",
        "https://login.microsoftonline.com/consumers/v2.0",
        f"https://login.microsoftonline.com/{OTHER_TENANT}/v2.0",
        f"http://ejemplo.com/{TENANT}",
    ],
)
def test_autoridades_rechazadas(env: pytest.MonkeyPatch, authority: str) -> None:
    assert "ENTRA_AUTHORITY" in config_error(env, ENTRA_AUTHORITY=authority)


@pytest.mark.parametrize(
    "authority",
    [f"http://oidc:8080/{TENANT}", f"http://localhost:8080/{TENANT}"],
)
def test_autoridad_http_solo_para_el_proveedor_de_prueba(
    env: pytest.MonkeyPatch, authority: str
) -> None:
    assert load(env, ENTRA_AUTHORITY=authority).entra_authority == authority


# --- URL pública -----------------------------------------------------------------------------


def test_public_base_url_sin_barra_final(env: pytest.MonkeyPatch) -> None:
    assert load(env).public_base_url == "https://saber.unilibre.edu.co"


@pytest.mark.parametrize("url", ["http://localhost", "http://127.0.0.1:8080"])
def test_public_base_url_http_en_localhost(env: pytest.MonkeyPatch, url: str) -> None:
    assert load(env, PUBLIC_BASE_URL=url).public_base_url == url


@pytest.mark.parametrize("url", ["http://saber.unilibre.edu.co", "ftp://localhost", "saber"])
def test_public_base_url_rechazada(env: pytest.MonkeyPatch, url: str) -> None:
    assert "PUBLIC_BASE_URL" in config_error(env, PUBLIC_BASE_URL=url)


# --- Dominios institucionales (R-20) -----------------------------------------------------------


def test_dominios_separados_por_comas_normalizados(env: pytest.MonkeyPatch) -> None:
    settings = load(
        env, INSTITUTIONAL_EMAIL_DOMAINS=" Unilibre.edu.co, @unilibre.edu.co ,otra.edu.co"
    )

    assert settings.institutional_email_domains == ["unilibre.edu.co", "otra.edu.co"]


@pytest.mark.parametrize("value", ["", " , ", "uni libre.edu.co", "unilibre"])
def test_dominios_invalidos(env: pytest.MonkeyPatch, value: str) -> None:
    assert "INSTITUTIONAL_EMAIL_DOMAINS" in config_error(env, INSTITUTIONAL_EMAIL_DOMAINS=value)


# --- Secretos ----------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "name",
    [
        "ENTRA_CLIENT_SECRET",
        "JWT_SIGNING_KEY",
        "SESSION_COOKIE_SECRET",
        "DATABASE_URL",
        "REDIS_URL",
        "ENTRA_TENANT_ID",
        "PUBLIC_BASE_URL",
    ],
)
def test_falta_una_variable_obligatoria(env: pytest.MonkeyPatch, name: str) -> None:
    env.delenv(name)

    assert name in config_error(env)


def test_clave_jwt_corta_no_se_filtra_en_el_error(env: pytest.MonkeyPatch) -> None:
    short = "clave-corta-secreta-de-31-chars"
    assert len(short) == 31

    message = config_error(env, JWT_SIGNING_KEY=short)

    assert "JWT_SIGNING_KEY" in message
    assert short not in message


def test_secreto_de_cookie_corto(env: pytest.MonkeyPatch) -> None:
    assert "SESSION_COOKIE_SECRET" in config_error(env, SESSION_COOKIE_SECRET="x" * 31)


@pytest.mark.parametrize("key_id", ["", "con espacio", "x" * 65])
def test_jwt_key_id_invalido(env: pytest.MonkeyPatch, key_id: str) -> None:
    assert "JWT_KEY_ID" in config_error(env, JWT_KEY_ID=key_id)


def test_database_url_exige_asyncpg(env: pytest.MonkeyPatch) -> None:
    url = f"postgresql://saber_app:{DB_PASSWORD}@db/saber_uli"
    message = config_error(env, DATABASE_URL=url)

    assert "DATABASE_URL" in message
    assert DB_PASSWORD not in message


def test_migration_database_url_exige_asyncpg(env: pytest.MonkeyPatch) -> None:
    assert "MIGRATION_DATABASE_URL" in config_error(
        env, MIGRATION_DATABASE_URL="mysql://x:y@db/saber_uli"
    )


def test_redis_url_exige_esquema_redis(env: pytest.MonkeyPatch) -> None:
    assert "REDIS_URL" in config_error(env, REDIS_URL="http://redis:6379")
    assert (
        load(env, REDIS_URL="rediss://redis:6380/0")
        .redis_url.get_secret_value()
        .startswith("rediss://")
    )


@pytest.mark.parametrize("sender", ["no-responder", "Saber Uli <sin-arroba>"])
def test_smtp_from_invalido(env: pytest.MonkeyPatch, sender: str) -> None:
    assert "SMTP_FROM" in config_error(env, SMTP_FROM=sender)


def test_ningun_secreto_aparece_en_repr_str_ni_json(env: pytest.MonkeyPatch) -> None:
    settings = load(
        env,
        SMTP_PASSWORD="contrasena-smtp-de-prueba",
        VAPID_PRIVATE_KEY="vapid-privada-de-prueba",
        MIGRATION_DATABASE_URL="postgresql+asyncpg://saber_migrator:migrador-secreto@db/saber_uli",
    )
    secrets = [
        CLIENT_SECRET,
        JWT_KEY,
        COOKIE_SECRET,
        DB_PASSWORD,
        REDIS_PASSWORD,
        "contrasena-smtp-de-prueba",
        "vapid-privada-de-prueba",
        "migrador-secreto",
    ]

    for rendered in (repr(settings), str(settings), settings.model_dump_json()):
        for secret in secrets:
            assert secret not in rendered
