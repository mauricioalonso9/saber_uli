"""Apoyo de las pruebas con el banco inicial real: cargarlo y publicar ítems."""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest

from saber_uli.content.application.review import Review
from saber_uli.content.application.seed_loader import SeedLoader
from saber_uli.content.infrastructure.interchange.json_format import read_bundle
from saber_uli.shared.domain.clock import FixedClock
from tests.integration.content.conftest import UowFactory

SEED = Path(__file__).parents[3] / "seeds" / "banco_inicial_saber_uli.json"
SEED_TIME = datetime(2026, 10, 9, 21, 0, tzinfo=UTC)
ADMIN = uuid4()


def seed() -> dict[str, Any]:
    data: dict[str, Any] = json.loads(SEED.read_text(encoding="utf-8"))
    return data


def seed_codes(module: str | None = None) -> list[str]:
    bank = seed()
    entries = bank["items"] + bank["consignas_escritura"]
    return sorted(e["id"] for e in entries if module is None or e["modulo"] == module)


@pytest.fixture
async def bank(content_uow: UowFactory) -> None:
    loader = SeedLoader(uow_factory=content_uow, clock=FixedClock(SEED_TIME), reader=read_bundle)
    await loader.execute(SEED.read_bytes())


def review(uow: UowFactory) -> Review:
    return Review(uow_factory=uow, clock=FixedClock(SEED_TIME))


async def revision(uow: UowFactory, code: str) -> int:
    async with uow() as unit:
        item = await unit.items.get_by_code(code)
    assert item is not None
    return item.revision


async def publish(uow: UowFactory, *codes: str) -> None:
    for code in codes:
        await review(uow).approve(
            code,
            ADMIN,
            expected_revision=await revision(uow, code),
            confirms_alignment=True,
            confirms_originality=True,
        )
