"""Fixtures comunes a las pruebas de unidad e integración.

Las fixtures de contenedores y base de datos viven en `tests/integration/conftest.py` (T024); la
fábrica de usuarios la agrega T044, el emisor de tokens T046 y el cliente ASGI T058.
"""

from datetime import UTC, datetime

import pytest

from saber_uli.shared.domain.clock import FixedClock


@pytest.fixture
def fixed_clock() -> FixedClock:
    return FixedClock(datetime(2026, 10, 6, 12, 0, tzinfo=UTC))
