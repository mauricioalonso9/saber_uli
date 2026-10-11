"""T097: recálculo y consulta de las estadísticas por versión (US8; FR-041 a FR-044; R-13).

La tarea nocturna reemplaza `content.item_version_stats` con lo que entrega la fuente de
respuestas (de la práctica, 003). En 002 la fuente es nula: todo queda en "datos insuficientes".
"""

import json
import re
from collections.abc import Collection, Mapping, Sequence
from datetime import UTC, datetime
from uuid import UUID

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from saber_uli.content.application.statistics_refresh import StatisticsRefresh
from saber_uli.content.domain.item_version import VersionState
from saber_uli.content.domain.statistics import FirstResponse
from saber_uli.content.infrastructure.null_statistics_source import NullStatisticsSource
from saber_uli.identity.domain.roles import Role
from saber_uli.shared.domain.clock import FixedClock
from tests.integration.content.conftest import UowFactory
from tests.integration.content.imports import importer
from tests.integration.content.seed_bank import bank, publish, seed
from tests.integration.identity.staff import StaffFactory

__all__ = ["bank"]  # fixture

NOW = datetime(2026, 10, 10, 3, 0, tzinfo=UTC)
UUID_TEXT = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")


class FakeSource:
    def __init__(self, data: Mapping[UUID, Sequence[FirstResponse]]) -> None:
        self.data = data
        self.asked: set[UUID] = set()

    async def first_responses(
        self, version_ids: Collection[UUID]
    ) -> Mapping[UUID, Sequence[FirstResponse]]:
        self.asked = set(version_ids)
        return {v: self.data[v] for v in version_ids if v in self.data}


def answers(correct: int, wrong: int, wrong_option: str = "B") -> list[FirstResponse]:
    """`correct` aciertos con puntaje del resto alto y `wrong` errores con puntaje bajo."""
    return [FirstResponse(True, "A", 0.8 + i / 1000) for i in range(correct)] + [
        FirstResponse(False, wrong_option, 0.3 + i / 1000) for i in range(wrong)
    ]


async def published_id(uow: UowFactory, code: str) -> UUID:
    async with uow() as unit:
        item = await unit.items.get_by_code(code)
    assert item is not None and item.published is not None and item.published.id is not None
    return item.published.id


def key_of(code: str) -> str:
    entry = next(i for i in seed()["items"] if i["id"] == code)
    return str(next(o["clave"] for o in entry["opciones"] if o["correcta"]))


async def stats_rows(engine: AsyncEngine) -> dict[UUID, tuple[int, object, list[str]]]:
    async with engine.connect() as conn:
        rows = await conn.execute(
            text(
                "SELECT version_id, first_responses, correct_rate, signals, computed_at"
                " FROM content.item_version_stats"
            )
        )
        return {r.version_id: (r.first_responses, r.correct_rate, list(r.signals)) for r in rows}


async def test_el_recalculo_reemplaza_la_tabla_por_version(
    content_uow: UowFactory, bank: None, app_engine: AsyncEngine
) -> None:
    await publish(content_uow, "LC-0001", "LC-0002", "ING-0001")
    first = await published_id(content_uow, "LC-0001")
    second = await published_id(content_uow, "LC-0002")
    key = key_of("LC-0001")
    wrong = next(o for o in "ABCD" if o != key)
    source = FakeSource(
        {
            first: [
                FirstResponse(r.correct, key if r.correct else wrong, r.rest_score)
                for r in answers(5, 35)
            ]
        }
    )

    refreshed = await StatisticsRefresh(
        uow_factory=content_uow, source=source, clock=FixedClock(NOW)
    ).run()

    # Solo los ítems de selección; el emparejamiento (ING-0001) no tiene estas cifras.
    assert source.asked == {first, second}
    assert refreshed == 2
    rows = await stats_rows(app_engine)
    assert set(rows) == {first, second}
    assert rows[first][0] == 40
    assert float(str(rows[first][1])) == 0.125
    assert set(rows[first][2]) == {"too_hard", "distractor_beats_key"}
    assert rows[second] == (0, None, [])

    source.data = {}
    await StatisticsRefresh(uow_factory=content_uow, source=source, clock=FixedClock(NOW)).run()

    assert (await stats_rows(app_engine))[first] == (0, None, [])


async def test_la_fuente_nula_deja_todo_sin_datos_suficientes(
    content_uow: UowFactory, bank: None, app_engine: AsyncEngine
) -> None:
    await publish(content_uow, "RC-0001", "RC-0002")

    await StatisticsRefresh(
        uow_factory=content_uow, source=NullStatisticsSource(), clock=FixedClock(NOW)
    ).run()

    rows = await stats_rows(app_engine)
    assert len(rows) == 2
    assert all(row == (0, None, []) for row in rows.values())


async def test_api_filtra_por_senal_y_lista_las_versiones(
    api_client: httpx.AsyncClient, staff: StaffFactory, content_uow: UowFactory, bank: None
) -> None:
    teacher = await staff(Role.TEACHER)
    await publish(content_uow, "LC-0001", "LC-0002")
    first = await published_id(content_uow, "LC-0001")
    key = key_of("LC-0001")
    wrong = next(o for o in "ABCD" if o != key)
    source = FakeSource(
        {
            first: [
                FirstResponse(r.correct, key if r.correct else wrong, r.rest_score)
                for r in answers(5, 35)
            ]
        }
    )
    await StatisticsRefresh(uow_factory=content_uow, source=source, clock=FixedClock(NOW)).run()

    hard = await api_client.get(
        "/api/v1/content/items", params={"signal": "too_hard"}, headers=teacher.headers
    )
    assert hard.status_code == 200, hard.text
    assert [i["code"] for i in hard.json()["items"]] == ["LC-0001"]

    # Una versión nueva de LC-0001 empieza en cero; la anterior conserva sus cifras.
    async with content_uow() as uow:
        item = await uow.items.get_by_code("LC-0001")
        assert item is not None and item.published is not None
        stem = item.published.content.stem_md
    entry = next(i for i in seed()["items"] if i["id"] == "LC-0001")
    service = importer(content_uow, NOW)
    job = await service.preview(
        json.dumps(
            {"esquema_version": "1.0", "items": [{**entry, "enunciado": stem + " (v2)"}]}
        ).encode(),
        "v2.json",
        teacher.id,
    )
    assert job.id is not None
    await service.confirm(
        job.id, teacher.id, target_state=VersionState.IN_REVIEW, originality_declared=True
    )
    await publish(content_uow, "LC-0001")

    response = await api_client.get(
        "/api/v1/content/items/LC-0001/statistics", headers=teacher.headers
    )
    missing = await api_client.get(
        "/api/v1/content/items/LC-9999/statistics", headers=teacher.headers
    )
    student = await api_client.get(
        "/api/v1/content/items/LC-0001/statistics", headers=(await staff()).headers
    )

    assert response.status_code == 200, response.text
    items = response.json()["items"]
    assert [(v["version"], v["state"], v["first_responses"]) for v in items] == [
        (2, "published", 0),
        (1, "retired", 40),
    ]
    assert items[0]["sufficient_data"] is False
    assert items[0]["correct_rate"] is None
    assert items[1]["sufficient_data"] is True
    assert items[1]["correct_rate"] == 0.125
    assert items[1]["option_rates"][wrong] == 0.875
    assert set(items[1]["signals"]) == {"too_hard", "distractor_beats_key"}
    assert set(items[1]) == {
        "version",
        "state",
        "first_responses",
        "sufficient_data",
        "correct_rate",
        "option_rates",
        "discrimination",
        "signals",
        "computed_at",
    }
    # Agregadas: ningún identificador (de estudiantes ni de otra cosa) en la respuesta.
    assert not UUID_TEXT.search(response.text)
    assert missing.status_code == 404
    assert student.status_code == 403
