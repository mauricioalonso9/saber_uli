"""Fixtures compartidas por las pruebas de integración de `identity`."""

from tests.integration.identity.catalog import new_program
from tests.integration.identity.guests import guests
from tests.integration.identity.staff import staff

__all__ = ["guests", "new_program", "staff"]
