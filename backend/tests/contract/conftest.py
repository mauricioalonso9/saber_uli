"""Fixtures del arnés de contrato: reutiliza las de integración (contenedores, usuarios, tokens)."""

from pathlib import Path

import pytest

from tests._docker import skip_without_docker
from tests.integration.conftest import (  # noqa: F401 - registra las fixtures
    api_client,
    app_engine,
    committed_login,
    database_urls,
    db_session,
    migrated_database,
    postgres_container,
    redis_client,
    redis_container,
    redis_url,
    role_passwords,
    token_codec,
)


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    here = Path(__file__).parent
    skip = skip_without_docker()
    for item in items:
        if here in Path(str(item.path)).parents:
            item.add_marker(pytest.mark.integration)
            item.add_marker(skip)
