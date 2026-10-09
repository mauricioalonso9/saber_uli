"""T007: infraestructura de contenedores (constitución IV y X; research R-07, R-32, R-33).

Usa la CLI de Docker por `subprocess` y `httpx` para las cabeceras. Levanta el stack con un
nombre de proyecto propio para no tocar el de desarrollo y lo destruye al terminar. Los secretos
se generan al vuelo. Se omite sin Docker, salvo con `REQUIRE_DOCKER=1`.

Verificación en dos tiempos (nota de Opus en tasks.md, T012): las pruebas marcadas con
`full_stack` necesitan `api`, `worker`, `beat` y `migrate` (T026, T034, T058); las demás corren
sobre `db`, `redis`, `proxy`, `mailpit` y `oidc`.
"""

import json
import os
import re
import secrets
import subprocess
from collections.abc import Iterator, Sequence
from pathlib import Path

import httpx
import pytest
import yaml

from tests._docker import docker_required, require_docker, skip_without_docker

pytestmark = [pytest.mark.infra, skip_without_docker()]

REPO = Path(__file__).resolve().parents[3]
PROJECT = "saber-uli-infra-test"
PROXY_URL = os.environ.get("SABER_PROXY_URL", "http://localhost")
INFRA_SERVICES = ["db", "redis", "proxy", "mailpit", "oidc"]
LONG_RUNNING = ["proxy", "api", "worker", "beat", "db", "redis", "mailpit", "oidc"]
CI_JOBS = {
    "infra",
    "backend-quality",
    "backend-tests",
    "contract",
    "frontend-quality",
    "e2e",
    "lighthouse",
    "build",
    "security",
}
TENANT = "11111111-1111-4111-8111-111111111111"


def run(args: Sequence[str], timeout: int = 900) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603 - argumentos en lista, sin shell
        list(args), capture_output=True, text=True, check=False, timeout=timeout, cwd=REPO
    )


def stack_env() -> dict[str, str]:
    """Entorno completo para Compose, con secretos aleatorios (nunca valores reales)."""
    app_pw, migrator_pw, bi_pw = (secrets.token_urlsafe(24) for _ in range(3))
    return {
        "POSTGRES_DB": "saber_uli",
        "POSTGRES_PASSWORD": secrets.token_urlsafe(24),
        "SABER_MIGRATOR_PASSWORD": migrator_pw,
        "SABER_APP_PASSWORD": app_pw,
        "SABER_BI_PASSWORD": bi_pw,
        "ENTRA_TENANT_ID": TENANT,
        "ENTRA_CLIENT_ID": "33333333-3333-4333-8333-333333333333",
        "ENTRA_CLIENT_SECRET": secrets.token_urlsafe(24),
        "ENTRA_AUTHORITY": f"http://oidc:8080/{TENANT}",
        "PUBLIC_BASE_URL": "http://localhost",
        "INSTITUTIONAL_EMAIL_DOMAINS": "unilibre.edu.co",
        "JWT_SIGNING_KEY": secrets.token_urlsafe(48),
        "JWT_KEY_ID": "infra-test",
        "SESSION_COOKIE_SECRET": secrets.token_urlsafe(48),
        "DATABASE_URL": f"postgresql+asyncpg://saber_app:{app_pw}@db:5432/saber_uli",
        "MIGRATION_DATABASE_URL": (
            f"postgresql+asyncpg://saber_migrator:{migrator_pw}@db:5432/saber_uli"
        ),
        "REDIS_URL": "redis://redis:6379/0",
        "REDIS_PASSWORD": secrets.token_urlsafe(24),
        "SMTP_HOST": "mailpit",
        "SMTP_PORT": "1025",
        "SMTP_USER": "",
        "SMTP_PASSWORD": "",
        "SMTP_FROM": "Saber Uli <no-responder@unilibre.edu.co>",
        "SMTP_STARTTLS": "false",
        "OTEL_ENABLED": "false",
        "LOG_LEVEL": "INFO",
        "VAPID_PUBLIC_KEY": "",
        "VAPID_PRIVATE_KEY": "",
        "E2E_EXTERNAL_TENANT_ID": "22222222-2222-4222-8222-222222222222",
    }


@pytest.fixture(scope="module")
def env_file(tmp_path_factory: pytest.TempPathFactory) -> Path:
    if docker_required():
        require_docker()
    path = tmp_path_factory.mktemp("compose") / "test.env"
    path.write_text(
        "".join(f"{key}={value}\n" for key, value in stack_env().items()), encoding="utf-8"
    )
    return path


def compose(env_file: Path, *files: str) -> list[str]:
    command = ["docker", "compose", "-p", PROJECT, "--env-file", str(env_file)]
    for name in files or ("compose.yaml", "compose.override.yaml"):
        command += ["-f", name]
    return [*command, "--profile", "e2e"]


@pytest.fixture(scope="module")
def infra_stack(env_file: Path) -> Iterator[list[str]]:
    base = compose(env_file)
    up = run([*base, "up", "-d", "--build", "--wait", *INFRA_SERVICES])
    try:
        assert up.returncode == 0, f"docker compose up falló:\n{(up.stdout + up.stderr)[-4000:]}"
        yield base
    finally:
        run([*base, "down", "-v", "--remove-orphans"])


def test_las_variables_de_la_prueba_cubren_env_example() -> None:
    example = (REPO / ".env.example").read_text(encoding="utf-8")
    documented = set(re.findall(r"^#?\s*([A-Z][A-Z0-9_]+)=", example, re.MULTILINE))

    assert documented, ".env.example no documenta variables"
    assert documented <= set(stack_env()), documented - set(stack_env())


@pytest.mark.parametrize(
    "files",
    [
        ("compose.yaml",),
        ("compose.yaml", "compose.override.yaml"),
        ("compose.yaml", "compose.prod.yaml"),
    ],
    ids=["base", "override", "prod"],
)
def test_compose_config_es_valido(env_file: Path, files: tuple[str, ...]) -> None:
    result = run([*compose(env_file, *files), "config", "-q"], timeout=120)

    assert result.returncode == 0, result.stderr


def test_redis_de_produccion_exige_contrasena(env_file: Path) -> None:
    """T070a: con compose.prod.yaml, `redis-cli ping` sin contraseña falla y con ella responde."""
    prod = [
        "docker",
        "compose",
        "-p",
        f"{PROJECT}-prod",
        "--env-file",
        str(env_file),
        "-f",
        "compose.yaml",
        "-f",
        "compose.prod.yaml",
    ]
    up = run([*prod, "up", "-d", "--wait", "redis"], timeout=300)
    try:
        assert up.returncode == 0, (up.stdout + up.stderr)[-4000:]
        anonymous = run([*prod, "exec", "-T", "redis", "redis-cli", "ping"], timeout=60)
        authenticated = run(
            [
                *prod,
                "exec",
                "-T",
                "redis",
                "sh",
                "-c",
                'REDISCLI_AUTH="$REDIS_PASSWORD" redis-cli ping',
            ],
            timeout=60,
        )
        argv = run([*prod, "exec", "-T", "redis", "cat", "/proc/1/cmdline"], timeout=60)
        config = run([*prod, "config", "--format", "json"], timeout=120)
    finally:
        run([*prod, "down", "-v", "--remove-orphans"])

    assert "NOAUTH" in anonymous.stdout + anonymous.stderr
    assert authenticated.stdout.strip() == "PONG"
    password = stack_env_value(env_file, "REDIS_PASSWORD")
    assert password not in argv.stdout  # la contraseña no queda en los argumentos del proceso
    services = json.loads(config.stdout)["services"]
    for name in ("api", "worker", "beat"):
        assert services[name]["environment"]["REDIS_URL"] == f"redis://:{password}@redis:6379/0"


def stack_env_value(env_file: Path, key: str) -> str:
    for line in env_file.read_text(encoding="utf-8").splitlines():
        if line.startswith(f"{key}="):
            return line.split("=", 1)[1]
    raise KeyError(key)


def test_imagen_backend_corre_con_uid_10001(env_file: Path) -> None:
    base = compose(env_file)
    build = run([*base, "build", "api"])
    assert build.returncode == 0, build.stderr[-4000:]

    result = run(
        [*base, "run", "--rm", "--no-deps", "--entrypoint", "id", "api", "-u"], timeout=120
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "10001"


def test_cabeceras_de_seguridad_del_proxy(infra_stack: list[str]) -> None:
    headers = httpx.get(f"{PROXY_URL}/", timeout=10).headers

    csp = headers["Content-Security-Policy"]
    script_src = next(
        (d for d in csp.split(";") if d.strip().startswith("script-src")),
        next(d for d in csp.split(";") if d.strip().startswith("default-src")),
    )
    assert "'unsafe-inline'" not in script_src
    assert headers["X-Content-Type-Options"] == "nosniff"
    assert headers["Referrer-Policy"] == "no-referrer"
    assert headers["X-Frame-Options"] == "DENY"


def test_el_proxy_no_registra_consultas_ni_ip(infra_stack: list[str]) -> None:
    # Las búsquedas de los listados (`?q=`) pueden llevar correos o nombres (T178).
    marker = f"t178-{secrets.token_hex(4)}"
    httpx.get(f"{PROXY_URL}/api/v1/invitations", params={"q": f"{marker}@correo.co"}, timeout=10)
    httpx.get(f"{PROXY_URL}/ingresar", params={"q": marker}, timeout=10)

    result = run([*infra_stack, "logs", "--no-log-prefix", "proxy"], timeout=60)

    assert result.returncode == 0, result.stderr
    assert marker not in result.stdout + result.stderr
    lines = [json.loads(line) for line in result.stdout.splitlines() if "proxy_request" in line]
    assert any(line["path"] == "/api/v1/invitations" for line in lines)
    fields = {"time", "event", "method", "path", "status", "bytes", "duration_s"}
    assert all(set(line) == fields for line in lines)


def test_service_worker_allowed(infra_stack: list[str]) -> None:
    # Hasta T068 no existe sw.js (404), pero las cabeceras se envían con `always`.
    headers = httpx.get(f"{PROXY_URL}/sw.js", timeout=10).headers

    assert headers["Service-Worker-Allowed"] == "/"
    assert headers["Cache-Control"] == "no-cache"


def test_ningun_proceso_principal_con_uid_0(infra_stack: list[str]) -> None:
    result = run([*infra_stack, "top"], timeout=60)
    assert result.returncode == 0, result.stderr

    # Compose v5: una tabla con columnas SERVICE, #, UID, PID, PPID… El proceso principal de
    # cada contenedor es el que no tiene como padre otro proceso del mismo contenedor.
    lines = [line.split() for line in result.stdout.splitlines() if line.strip()]
    header, rows = lines[0], lines[1:]
    col = {name: header.index(name) for name in ("SERVICE", "#", "UID", "PID", "PPID")}
    by_container: dict[tuple[str, str], list[list[str]]] = {}
    for row in rows:
        by_container.setdefault((row[col["SERVICE"]], row[col["#"]]), []).append(row)

    main_users: dict[str, str] = {}
    for (service, index), procs in by_container.items():
        pids = {p[col["PID"]] for p in procs}
        main = next(p for p in procs if p[col["PPID"]] not in pids)
        main_users[f"{service}-{index}"] = main[col["UID"]]

    assert main_users, result.stdout
    root = {name: uid for name, uid in main_users.items() if uid in {"0", "root"}}
    assert not root, f"procesos principales como root: {root}"


def test_roles_y_extensiones_de_postgres(infra_stack: list[str]) -> None:
    def psql(sql: str) -> set[str]:
        result = run(
            [
                *infra_stack,
                "exec",
                "-T",
                "db",
                "psql",
                "-U",
                "postgres",
                "-d",
                "saber_uli",
                "-tAc",
                sql,
            ],
            timeout=60,
        )
        assert result.returncode == 0, result.stderr
        return {line.strip() for line in result.stdout.splitlines() if line.strip()}

    roles = psql("SELECT rolname FROM pg_roles WHERE rolname LIKE 'saber\\_%'")
    extensions = psql("SELECT extname FROM pg_extension")

    assert {"saber_migrator", "saber_app", "saber_bi"} <= roles
    assert {"citext", "pg_stat_statements"} <= extensions


@pytest.mark.full_stack
def test_servicios_healthy_y_migrate_exitoso(infra_stack: list[str]) -> None:
    up = run([*infra_stack, "up", "-d", "--build", "--wait"])
    assert up.returncode == 0, (up.stdout + up.stderr)[-4000:]

    result = run([*infra_stack, "ps", "-a", "--format", "json"], timeout=60)
    rows = [json.loads(line) for line in result.stdout.splitlines() if line.strip()]
    by_service = {row["Service"]: row for row in rows}

    for service in LONG_RUNNING:
        assert by_service[service]["Health"] == "healthy", (service, by_service[service])
    assert by_service["migrate"]["State"] == "exited"
    assert by_service["migrate"]["ExitCode"] == 0


@pytest.mark.full_stack
def test_flujo_de_ci() -> None:
    workflow = REPO / ".github" / "workflows" / "ci.yml"
    assert workflow.exists(), "falta .github/workflows/ci.yml (T014)"

    lint = run(
        [
            "docker",
            "run",
            "--rm",
            "-v",
            f"{REPO}:/repo",
            "-w",
            "/repo",
            "rhysd/actionlint:latest",
            "-no-color",
        ],
        timeout=300,
    )
    assert lint.returncode == 0, lint.stdout + lint.stderr

    jobs = set(yaml.safe_load(workflow.read_text(encoding="utf-8"))["jobs"])
    assert jobs >= CI_JOBS, CI_JOBS - jobs
