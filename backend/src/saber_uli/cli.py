"""Comando `saber-uli` (plan.md: migrate, grant-admin, seed…).

Subcomandos actuales:

- `migrate`: aplica las migraciones con `MIGRATION_DATABASE_URL` (rol saber_migrator). No usa
  la configuración completa de la aplicación: el servicio `migrate` no recibe los secretos de
  Entra ID ni de JWT (mínimo privilegio, R-07).

- `identity import-programs --csv <archivo>`: carga o actualiza el catálogo de programas desde
  un CSV UTF-8 con encabezado `codigo,nombre,seccional` (quickstart §3). Usa `DATABASE_URL`
  (rol saber_app). Sale con 0 si todas las filas son válidas, 1 si alguna se rechazó (las
  válidas sí se cargan) o si falla la base de datos, y 2 si el archivo o la configuración no
  sirven (no se carga nada).

- `identity invite-guest --email <correo> [--days N] [--name <nombre>]`: invita a una persona
  externa con actor `system` (quickstart V5). Usa `DATABASE_URL` e
  `INSTITUTIONAL_EMAIL_DOMAINS`; el worker envía el correo. Sale con 0 si creó la invitación, 1
  si una regla la impidió (correo institucional, invitación vigente) y 2 si los datos no sirven.

T147 agregará `grant-admin`. Ningún mensaje muestra URL, contraseñas ni el correo invitado.
"""

import argparse
import asyncio
import csv
import os
import re
import sys
from collections.abc import Sequence
from pathlib import Path

from sqlalchemy.engine import make_url

from saber_uli.identity.application.import_programs import (
    ImportPrograms,
    ImportReport,
    ProgramLine,
    RejectedLine,
)
from saber_uli.identity.application.invitations import InvitationService
from saber_uli.identity.infrastructure.outbox_events import register_identity_outbox
from saber_uli.identity.infrastructure.unit_of_work import SqlAlchemyIdentityUnitOfWork
from saber_uli.shared.application.event_bus import EventBus
from saber_uli.shared.domain.clock import SystemClock
from saber_uli.shared.domain.errors import DomainError
from saber_uli.shared.infrastructure.db import create_engine, create_session_factory
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


PROGRAMS_HEADER = ["codigo", "nombre", "seccional"]


class UsageError(Exception):
    """El archivo o la configuración no permiten ejecutar el comando."""


def _read_programs(path: Path) -> tuple[list[ProgramLine], list[RejectedLine]]:
    try:
        # utf-8-sig: Excel guarda los CSV UTF-8 con BOM.
        with path.open(encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.reader(handle))
    except FileNotFoundError as error:
        raise UsageError(f"no existe el archivo {path}") from error
    except UnicodeDecodeError as error:
        raise UsageError(f"el archivo {path} no está en UTF-8") from error
    if not rows or [cell.strip().lower() for cell in rows[0]] != PROGRAMS_HEADER:
        raise UsageError(f"el encabezado debe ser exactamente: {','.join(PROGRAMS_HEADER)}")
    lines: list[ProgramLine] = []
    rejected: list[RejectedLine] = []
    for number, row in enumerate(rows[1:], start=2):
        if not any(cell.strip() for cell in row):
            continue  # filas vacías al final del archivo
        if len(row) != len(PROGRAMS_HEADER):
            rejected.append(RejectedLine(number, f"se esperaban {len(PROGRAMS_HEADER)} columnas"))
            continue
        code, name, campus = row
        lines.append(ProgramLine(number, code, name, campus))
    return lines, rejected


async def _run_import(
    url: str, lines: list[ProgramLine], rejected: list[RejectedLine]
) -> ImportReport:
    engine = create_engine(url)
    try:
        session_factory = create_session_factory(engine)
        bus = EventBus()
        use_case = ImportPrograms(
            uow_factory=lambda: SqlAlchemyIdentityUnitOfWork(session_factory, bus),
            clock=SystemClock(),
        )
        return await use_case.execute(lines, rejected)
    finally:
        await engine.dispose()


def _import_programs(csv_path: str) -> int:
    url = os.environ.get("DATABASE_URL")
    if not url:
        print("Error: falta la variable de entorno DATABASE_URL (rol saber_app).", file=sys.stderr)
        return EXIT_USAGE
    try:
        lines, rejected = _read_programs(Path(csv_path))
    except UsageError as error:
        print(f"Error: {error}. No se cargó nada.", file=sys.stderr)
        return EXIT_USAGE
    configure_logging(os.environ.get("LOG_LEVEL", "WARNING"))
    try:
        report = asyncio.run(_run_import(url, lines, rejected))
    except Exception as error:
        detail = _redact(str(error), url).splitlines()[0] if str(error) else ""
        print(f"Error: la carga falló ({type(error).__name__}): {detail}", file=sys.stderr)
        return EXIT_FAILURE
    for item in report.rejected:
        print(f"Fila {item.line}: {item.reason}")
    print(
        f"Programas creados: {report.created}, actualizados: {report.updated}, "
        f"sin cambios: {report.unchanged}, filas inválidas: {len(report.rejected)}."
    )
    return EXIT_FAILURE if report.rejected else EXIT_OK


EMAIL_PATTERN = re.compile(r"^[^@\s<>,;]+@[^@\s<>,;]+\.[^@\s<>,;]+$")


async def _run_invite(
    url: str, domains: list[str], email: str, days: int | None, name: str | None
) -> None:
    engine = create_engine(url)
    try:
        session_factory = create_session_factory(engine)
        bus = EventBus()
        register_identity_outbox(bus)
        service = InvitationService(
            uow_factory=lambda: SqlAlchemyIdentityUnitOfWork(session_factory, bus),
            clock=SystemClock(),
            institutional_domains=domains,
        )
        await service.create(None, email=email, access_days=days, invitee_name=name)
    finally:
        await engine.dispose()


def _invite_guest(email: str, days: int | None, name: str | None) -> int:
    url = os.environ.get("DATABASE_URL")
    domains = [d for d in os.environ.get("INSTITUTIONAL_EMAIL_DOMAINS", "").split(",") if d.strip()]
    if not url or not domains:
        print(
            "Error: faltan las variables de entorno DATABASE_URL o INSTITUTIONAL_EMAIL_DOMAINS.",
            file=sys.stderr,
        )
        return EXIT_USAGE
    if len(email) > 254 or not EMAIL_PATTERN.fullmatch(email.strip()):
        print("Error: el correo no es válido.", file=sys.stderr)
        return EXIT_USAGE
    if days is not None and not 1 <= days <= 730:
        print("Error: --days debe estar entre 1 y 730.", file=sys.stderr)
        return EXIT_USAGE
    configure_logging(os.environ.get("LOG_LEVEL", "WARNING"))
    try:
        asyncio.run(_run_invite(url, domains, email.strip(), days, name))
    except DomainError as error:
        print(f"No se creó la invitación: {error.message}", file=sys.stderr)
        return EXIT_FAILURE
    except Exception as error:
        detail = _redact(str(error), url).splitlines()[0] if str(error) else ""
        print(f"Error: la invitación falló ({type(error).__name__}): {detail}", file=sys.stderr)
        return EXIT_FAILURE
    print("Invitación creada. El correo con el enlace se enviará en unos segundos.")
    return EXIT_OK


def _utf8_output() -> None:
    """Mensajes en español también en consolas de Windows con otra página de códigos."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8")


def app(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="saber-uli", description="Tareas de operación de Saber Uli."
    )
    commands = parser.add_subparsers(dest="command", required=True, metavar="comando")
    commands.add_parser("migrate", help="aplica las migraciones de la base de datos")
    identity = commands.add_parser("identity", help="usuarios, programas y accesos")
    identity_commands = identity.add_subparsers(dest="action", required=True, metavar="acción")
    import_programs = identity_commands.add_parser(
        "import-programs", help="carga el catálogo de programas desde un CSV"
    )
    import_programs.add_argument(
        "--csv", required=True, help="archivo CSV UTF-8 con encabezado codigo,nombre,seccional"
    )

    invite_guest = identity_commands.add_parser(
        "invite-guest", help="invita a una persona externa (actor: sistema)"
    )
    invite_guest.add_argument("--email", required=True, help="correo de la persona invitada")
    invite_guest.add_argument(
        "--days", type=int, default=None, help="días de acceso (por defecto, el parámetro)"
    )
    invite_guest.add_argument("--name", default=None, help="nombre de la persona (opcional)")

    _utf8_output()
    args = parser.parse_args(argv)
    if args.command == "migrate":
        sys.exit(_migrate())
    if args.command == "identity" and args.action == "import-programs":
        sys.exit(_import_programs(args.csv))
    if args.command == "identity" and args.action == "invite-guest":
        sys.exit(_invite_guest(args.email, args.days, args.name))


if __name__ == "__main__":
    app()
