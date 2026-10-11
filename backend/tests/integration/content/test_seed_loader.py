"""T036: carga del banco inicial en cada despliegue (US1; FR-021 a FR-023; research R-07).

La carga es idempotente: agrega lo nuevo (En revisión), versiona lo que cambió en el archivo y
nunca pisa el trabajo de los docentes. Un archivo con errores no aplica nada. Dos cargas a la vez
no se pisan (advisory lock).
"""

import asyncio
import json
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from saber_uli.content.application.seed_loader import SeedInvalidError, SeedLoader
from saber_uli.content.domain.context import Origin
from saber_uli.content.domain.item_version import VersionState
from saber_uli.content.domain.validation import ValidationRule
from saber_uli.content.infrastructure.interchange.json_format import read_bundle
from saber_uli.shared.domain.clock import FixedClock
from tests.integration.content.conftest import UowFactory

SEED = Path(__file__).parents[3] / "seeds" / "banco_inicial_saber_uli.json"
NOW = datetime(2026, 10, 9, 12, 0, tzinfo=UTC)
TEACHER = uuid4()
ADMIN = uuid4()


def seed() -> dict[str, Any]:
    data: dict[str, Any] = json.loads(SEED.read_text(encoding="utf-8"))
    return data


def encode(bank: dict[str, Any]) -> bytes:
    return json.dumps(bank, ensure_ascii=False).encode("utf-8")


def item(bank: dict[str, Any], code: str) -> dict[str, Any]:
    entry: dict[str, Any] = next(i for i in bank["items"] if i["id"] == code)
    return entry


@pytest.fixture
def loader(content_uow: UowFactory) -> SeedLoader:
    return SeedLoader(uow_factory=content_uow, clock=FixedClock(NOW), reader=read_bundle)


async def count(engine: AsyncEngine, sql: str) -> int:
    async with engine.connect() as conn:
        return int((await conn.execute(text(sql))).scalar_one())


async def test_la_primera_carga_trae_todo_el_banco_en_revision(
    loader: SeedLoader, content_uow: UowFactory, app_engine: AsyncEngine
) -> None:
    result = await loader.execute(SEED.read_bytes())

    assert (result.added_items, result.versioned_items, result.unchanged_items) == (46, 0, 0)
    assert result.added_contexts == 8
    assert result.added_modules == 5
    assert result.added_rubrics == 1
    assert result.pending_manual == []
    async with content_uow() as uow:
        modules = await uow.modules.list()
        lc0001 = await uow.items.get_by_code("LC-0001")
        prompt = await uow.items.get_by_code("CE-0001")
        lc_context = await uow.contexts.get_by_code("LC-CTX-001")
        history = await uow.items.history("LC-0001")
        weight = await uow.taxonomy.get_by_code("LC-A1")
    assert [module.code for module in modules] == ["LC", "RC", "CC", "ING", "CE"]
    assert lc0001 is not None and lc0001.open is not None
    assert lc0001.open.state is VersionState.IN_REVIEW
    assert lc0001.origin is Origin.AI
    assert lc0001.open.author_id is None and lc0001.open.contributor_ids == frozenset()
    assert lc0001.seed_hash is not None
    assert prompt is not None and prompt.open is not None and prompt.open.content.rubric_id
    assert lc_context is not None and lc_context.current.word_count
    assert [event.type.value for event in history] == ["seed_loaded"]
    assert weight is not None and str(weight.target_weight) == "0.260"
    assert await count(app_engine, "SELECT count(*) FROM content.items") == 46
    assert await count(app_engine, "SELECT count(*) FROM content.seed_loads") == 1


async def test_repetir_la_carga_no_crea_nada(loader: SeedLoader, app_engine: AsyncEngine) -> None:
    await loader.execute(SEED.read_bytes())

    again = await loader.execute(SEED.read_bytes())

    assert (again.added_items, again.versioned_items, again.unchanged_items) == (0, 0, 46)
    assert (again.added_contexts, again.versioned_contexts) == (0, 0)
    assert await count(app_engine, "SELECT count(*) FROM content.item_versions") == 46
    assert await count(app_engine, "SELECT count(*) FROM content.context_versions") == 8
    assert await count(app_engine, "SELECT count(*) FROM content.seed_loads") == 2


async def test_la_recarga_no_pisa_lo_que_edito_un_docente(
    loader: SeedLoader, content_uow: UowFactory
) -> None:
    await loader.execute(SEED.read_bytes())
    async with content_uow() as uow:
        lc = await uow.items.get_by_code("LC-0001", for_update=True)
        assert lc is not None and lc.open is not None
        edited = replace(lc.open.content, stem_md="Enunciado corregido por el docente")
        lc.edit(edited, b"docente", lc.open.fingerprint, lc.open.context_version_id, TEACHER, NOW)
        await uow.items.save(lc)
        await uow.commit()

    await loader.execute(SEED.read_bytes())

    async with content_uow() as uow:
        again = await uow.items.get_by_code("LC-0001")
    assert again is not None and again.open is not None
    assert again.open.content.stem_md == "Enunciado corregido por el docente"


async def test_un_banco_actualizado_agrega_y_versiona_sin_pisar_al_docente(
    loader: SeedLoader, content_uow: UowFactory
) -> None:
    await loader.execute(SEED.read_bytes())
    async with content_uow() as uow:
        # LC-0003 publicado por un administrador; LC-0001 con un borrador de un docente.
        published = await uow.items.get_by_code("LC-0003", for_update=True)
        assert published is not None
        published.approve(ADMIN, NOW, confirms_alignment=True, confirms_originality=True)
        await uow.items.save(published)
        lc1 = await uow.items.get_by_code("LC-0001", for_update=True)
        assert lc1 is not None and lc1.open is not None
        lc1.edit(lc1.open.content, b"docente", lc1.open.fingerprint, None, TEACHER, NOW)
        await uow.items.save(lc1)
        await uow.commit()
    bank = seed()
    new = dict(item(bank, "LC-0001"), id="LC-9001", enunciado="Un enunciado nuevo del banco.")
    bank["items"].append(new)
    item(bank, "LC-0002")["enunciado"] = "Enunciado de LC-0002 corregido en el archivo."
    item(bank, "LC-0003")["enunciado"] = "Enunciado de LC-0003 corregido en el archivo."
    item(bank, "LC-0001")["enunciado"] = "Cambio del archivo que no debe aplicarse."

    result = await loader.execute(encode(bank))

    assert result.added_items == 1
    assert result.versioned_items == 2
    assert result.pending_manual == ["LC-0001"]
    async with content_uow() as uow:
        lc9001 = await uow.items.get_by_code("LC-9001")
        lc2 = await uow.items.get_by_code("LC-0002")
        lc3 = await uow.items.get_by_code("LC-0003")
        lc1_after = await uow.items.get_by_code("LC-0001")
        history = await uow.items.history("LC-0003")
    assert lc9001 is not None and lc9001.open is not None
    assert lc9001.open.state is VersionState.IN_REVIEW
    # LC-0002 seguía En revisión sin intervención humana: se actualiza su versión abierta.
    assert lc2 is not None and lc2.open is not None
    assert lc2.open.content.stem_md == "Enunciado de LC-0002 corregido en el archivo."
    # LC-0003 estaba publicado: versión 2 En revisión; la 1 sigue publicada.
    assert lc3 is not None and lc3.published is not None and lc3.published.number == 1
    assert lc3.open is not None and lc3.open.number == 2
    assert lc3.open.state is VersionState.IN_REVIEW
    assert history[-1].type.value == "seed_versioned"
    assert lc1_after is not None and lc1_after.open is not None
    assert lc1_after.open.content.stem_md != "Cambio del archivo que no debe aplicarse."


async def test_la_taxonomia_existente_no_cambia_y_la_nueva_se_agrega(
    loader: SeedLoader, content_uow: UowFactory
) -> None:
    await loader.execute(SEED.read_bytes())
    bank = seed()
    lc = next(module for module in bank["modulos"] if module["codigo"] == "LC")
    assertion = lc["competencias"][0]["afirmaciones"][0]
    assertion["descripcion"] = "Nombre cambiado en el archivo"
    assertion["evidencias"].append({"codigo": "LC-E1.9", "descripcion": "Evidencia nueva"})

    await loader.execute(encode(bank))

    async with content_uow() as uow:
        kept = await uow.taxonomy.get_by_code("LC-A1")
        added = await uow.taxonomy.get_by_code("LC-E1.9")
    assert kept is not None and kept.name != "Nombre cambiado en el archivo"
    assert added is not None and kept.id is not None and added.parent_id == kept.id


async def test_un_archivo_con_errores_no_aplica_nada(
    loader: SeedLoader, app_engine: AsyncEngine
) -> None:
    bank = seed()
    for option in item(bank, "LC-0004")["opciones"]:
        option["correcta"] = True

    with pytest.raises(SeedInvalidError) as error:
        await loader.execute(encode(bank))

    assert ("LC-0004", ValidationRule.SINGLE_CORRECT_OPTION) in {
        (problem.code, problem.rule) for problem in error.value.problems
    }
    assert await count(app_engine, "SELECT count(*) FROM content.items") == 0
    assert await count(app_engine, "SELECT count(*) FROM content.modules") == 0
    assert await count(app_engine, "SELECT count(*) FROM content.seed_loads") == 0


async def test_un_archivo_ilegible_tampoco_aplica_nada(
    loader: SeedLoader, app_engine: AsyncEngine
) -> None:
    bank = seed()
    del item(bank, "LC-0005")["enunciado"]

    with pytest.raises(SeedInvalidError) as error:
        await loader.execute(encode(bank))

    assert ("LC-0005", ValidationRule.REQUIRED) in {
        (problem.code, problem.rule) for problem in error.value.problems
    }
    assert await count(app_engine, "SELECT count(*) FROM content.items") == 0


async def test_dos_cargas_simultaneas_no_se_pisan(
    loader: SeedLoader, content_uow: UowFactory, app_engine: AsyncEngine
) -> None:
    other = SeedLoader(uow_factory=content_uow, clock=FixedClock(NOW), reader=read_bundle)

    first, second = await asyncio.gather(
        loader.execute(SEED.read_bytes()), other.execute(SEED.read_bytes())
    )

    assert sorted([first.added_items, second.added_items]) == [0, 46]
    assert await count(app_engine, "SELECT count(*) FROM content.items") == 46
