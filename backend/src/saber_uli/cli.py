"""Comando `saber-uli` (plan.md: migrate, grant-admin, seed…).

Subcomandos actuales:

- `migrate`: aplica las migraciones con `MIGRATION_DATABASE_URL` (rol saber_migrator). No usa
  la configuración completa de la aplicación: el servicio `migrate` no recibe los secretos de
  Entra ID ni de JWT (mínimo privilegio, R-07).

T102, T118 y T147 agregarán `import-programs`, `invite-guest` y `grant-admin`. Ningún mensaje
muestra URL ni contraseñas.
"""

import argparse
import os
import sys
from collections.abc import Sequence

from sqlalchemy.engine import make_url

from saber_uli.shared.infrastructure.logging import configure_logging
from saber_uli.shared.infrastructure.migrations import run_migrations

EXIT_OK = 0
EXIT_FAILURE = 1
EXIT_USAGE = 2


def _redact(message: str, url: str) -> str:
    try:
        secret = make_url(url).password
    except Exception:
        secret = None
    return message.replace(secret, "***") if secret else message


def _migrate() -> int:
    url = os.environ.get("MIGRATION_DATABASE_URL")
    if not url:
        print(
            "Error: falta la variable de entorno MIGRATION_DATABASE_URL (rol saber_migrator).",
            file=sys.stderr,
        )
        return EXIT_USAGE
    configure_logging(os.environ.get("LOG_LEVEL", "INFO"))
    try:
        run_migrations(url)
    except Exception as error:
        detail = _redact(str(error), url).splitlines()[0] if str(error) else ""
        print(
            f"Error: las migraciones fallaron ({type(error).__name__}): {detail}",
            file=sys.stderr,
        )
        return EXIT_FAILURE
    return EXIT_OK


def app(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="saber-uli", description="Tareas de operación de Saber Uli."
    )
    commands = parser.add_subparsers(dest="command", required=True, metavar="comando")
    commands.add_parser("migrate", help="aplica las migraciones de la base de datos")

    args = parser.parse_args(argv)
    if args.command == "migrate":
        sys.exit(_migrate())


if __name__ == "__main__":
    app()
