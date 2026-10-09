"""Detección de Docker compartida por las pruebas de infraestructura (T007) e integración (T024).

Sin Docker, esas pruebas se omiten; con `REQUIRE_DOCKER=1` (CI) se exige y fallan.
"""

import os
import shutil
import subprocess
from functools import cache

import pytest


@cache
def docker_available() -> bool:
    if shutil.which("docker") is None:
        return False
    result = subprocess.run(
        ["docker", "info", "--format", "{{.ServerVersion}}"],  # noqa: S607
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    return result.returncode == 0


def docker_required() -> bool:
    return os.environ.get("REQUIRE_DOCKER") == "1"


def skip_without_docker() -> pytest.MarkDecorator:
    """Marca que omite la prueba si no hay Docker, salvo con `REQUIRE_DOCKER=1`."""
    return pytest.mark.skipif(
        not docker_available() and not docker_required(),
        reason="Docker no está disponible (defina REQUIRE_DOCKER=1 para exigirlo)",
    )


def require_docker() -> None:
    """Falla con un mensaje claro si se exige Docker y no está disponible."""
    if not docker_available():
        pytest.fail("REQUIRE_DOCKER=1 pero Docker no está disponible", pytrace=False)
