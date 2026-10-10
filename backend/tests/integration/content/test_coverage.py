"""T091: cobertura del banco frente a la distribución del examen (US7; FR-039, FR-040; R-16).

Se agrupa por el tipo de categoría que tiene pesos: LC por afirmación, RC y CC por competencia e
Inglés por parte. Cuentan los ítems Publicados y En revisión (no los Borradores ni los
retirados); el faltante es `max(0, ceil(meta x peso) - publicados)`.
"""

import httpx
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from saber_uli.content.application.coverage import Coverage, ModuleCoverage
from saber_uli.content.domain.errors import ModuleNotFoundError
from saber_uli.identity.domain.roles import Role
from tests.integration.content.conftest import UowFactory
from tests.integration.content.seed_bank import ADMIN, bank, publish, review, revision, seed_codes
from tests.integration.identity.staff import StaffFactory

__all__ = ["bank"]  # fixture


def by_code(coverage: ModuleCoverage) -> dict[str, tuple[int, int, float, int, bool]]:
    return {
        c.code: (c.published, c.in_review, c.published_share, c.missing, c.below_target)
        for c in coverage.categories
    }


async def test_lc_por_afirmacion_sin_borradores_ni_retirados(
    content_uow: UowFactory, bank: None
) -> None:
    await publish(content_uow, "LC-0001", "LC-0002", "LC-0004")
    await review(content_uow).retire(
        "LC-0004",
        ADMIN,
        expected_revision=await revision(content_uow, "LC-0004"),
        reason="Desactualizado",
    )
    await review(content_uow).return_to_draft(
        "LC-0003",
        ADMIN,
        expected_revision=await revision(content_uow, "LC-0003"),
        comment="Revisa la clave.",
    )

    coverage = await Coverage(uow_factory=content_uow).module("LC")

    assert coverage.grouped_by == "assertion"
    assert (coverage.bank_target, coverage.published_total, coverage.in_review_total) == (150, 2, 4)
    assert by_code(coverage) == {
        # ceil(150 x 0,26) = 39; ceil(150 x 0,40) = 60; ceil(150 x 0,34) = 51
        "LC-A1": (1, 1, 0.5, 38, True),
        "LC-A2": (1, 3, 0.5, 59, True),
        "LC-A3": (0, 0, 0.0, 51, True),
    }
    assert [c.target_weight for c in coverage.categories] == [0.26, 0.4, 0.34]


async def test_rc_y_cc_por_competencia(content_uow: UowFactory, bank: None) -> None:
    await publish(content_uow, "RC-0001", "CC-0004")

    rc = await Coverage(uow_factory=content_uow).module("RC")
    cc = await Coverage(uow_factory=content_uow).module("CC")

    assert rc.grouped_by == cc.grouped_by == "competence"
    assert by_code(rc)["RC-C1"] == (1, 1, 1.0, 49, True)  # ceil(150 x 0,33) = 50
    assert by_code(rc)["RC-C2"] == (0, 3, 0.0, 50, True)
    assert list(by_code(cc)) == ["CC-C1", "CC-C2", "CC-C3", "CC-C4"]
    assert by_code(cc)["CC-C2"] == (1, 1, 1.0, 29, True)  # ceil(150 x 0,20) = 30


async def test_ingles_por_parte_y_el_objetivo_cumplido(
    content_uow: UowFactory, bank: None, migrated_database: dict[str, str]
) -> None:
    await publish(content_uow, *seed_codes("ING"))
    engine = create_async_engine(migrated_database["migrator"])
    async with engine.begin() as conn:
        await conn.execute(text("UPDATE content.modules SET bank_target = 20 WHERE code = 'ING'"))
    await engine.dispose()

    coverage = await Coverage(uow_factory=content_uow).module("ING")

    assert coverage.grouped_by == "part"
    assert (coverage.bank_target, coverage.published_total, coverage.in_review_total) == (20, 19, 0)
    parts = by_code(coverage)
    assert len(parts) == 7
    first = next(code for code in parts if code.endswith("1"))
    last = next(code for code in parts if code.endswith("7"))
    assert parts[first] == (5, 0, pytest.approx(5 / 19), 0, False)  # ceil(20 x 0,11) = 3
    assert parts[last] == (3, 0, pytest.approx(3 / 19), 2, True)  # ceil(20 x 0,22) = 5


async def test_ce_sin_pesos_informa_solo_los_totales(content_uow: UowFactory, bank: None) -> None:
    await publish(content_uow, "CE-0001")

    coverage = await Coverage(uow_factory=content_uow).module("CE")

    assert coverage.categories == []
    assert (coverage.bank_target, coverage.published_total, coverage.in_review_total) == (20, 1, 2)


async def test_un_modulo_inexistente(content_uow: UowFactory, bank: None) -> None:
    with pytest.raises(ModuleNotFoundError):
        await Coverage(uow_factory=content_uow).module("XX")


async def test_api_de_cobertura(
    api_client: httpx.AsyncClient, staff: StaffFactory, content_uow: UowFactory, bank: None
) -> None:
    teacher = await staff(Role.TEACHER)
    await publish(content_uow, "LC-0001")

    response = await api_client.get("/api/v1/content/coverage/LC", headers=teacher.headers)
    student = await api_client.get("/api/v1/content/coverage/LC", headers=(await staff()).headers)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["module"] == "LC"
    assert body["grouped_by"] == "assertion"
    assert (body["published_total"], body["in_review_total"]) == (1, 7)
    first = body["categories"][0]
    assert set(first) == {
        "node_id",
        "code",
        "name",
        "target_weight",
        "published",
        "in_review",
        "published_share",
        "missing",
        "below_target",
    }
    assert (first["code"], first["published"], first["missing"]) == ("LC-A1", 1, 38)
    assert student.status_code == 403
