"""T103: mantenimiento de la taxonomía (US9; FR-001, FR-040, FR-045; contrato:
`updateContentModule`, `createTaxonomyNode`, `updateTaxonomyNode`, `deleteTaxonomyNode`,
`createRubric`, `updateRubric`).

Categorías, pesos, metas y rúbricas son datos que mantiene el administrador. Lo que está en uso
solo se desactiva. Cada cambio queda en `content.taxonomy_changes`.
"""

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import httpx
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from saber_uli.content.domain.item_version import VersionState
from saber_uli.identity.domain.roles import Role
from tests.integration.content.conftest import LcTaxonomy, UowFactory
from tests.integration.content.imports import bank_file, importer, lc_item
from tests.integration.identity.staff import Staff, StaffFactory

NODES = "/api/v1/content/taxonomy-nodes"
RUBRICS = "/api/v1/content/rubrics"


@pytest.fixture
async def admin(staff: StaffFactory) -> Staff:
    return await staff(Role.ADMIN)


def evidence(parent: object, code: str = "LC-E1.9") -> dict[str, Any]:
    return {
        "module": "LC",
        "kind": "evidence",
        "code": code,
        "name": "Reconoce el sentido de una expresión",
        "parent_id": str(parent),
    }


def rubric(code: str = "RUB-CE-09", levels: int = 2) -> dict[str, Any]:
    return {
        "code": code,
        "name": "Texto argumentativo",
        "note": None,
        "active": True,
        "relevance_condition": {"name": "Pertinencia", "description": "Responde a la pregunta"},
        "dimensions": [
            {
                "code": "planteamiento",
                "name": "Planteamiento",
                "levels": [{"level": n, "description": f"Nivel {n}"} for n in range(1, levels + 1)],
            }
        ],
    }


async def changes(engine: AsyncEngine) -> list[tuple[str, str, bool, bool]]:
    async with engine.connect() as conn:
        rows = await conn.execute(
            text(
                "SELECT target, action, before IS NOT NULL AS b, after IS NOT NULL AS a"
                " FROM content.taxonomy_changes ORDER BY changed_at, id"
            )
        )
        return [(r.target, r.action, r.b, r.a) for r in rows]


async def test_crear_categorias_con_la_jerarquia_correcta(
    api_client: httpx.AsyncClient, admin: Staff, lc_taxonomy: LcTaxonomy
) -> None:
    created = await api_client.post(
        NODES, json=evidence(lc_taxonomy.assertion.id), headers=admin.headers
    )
    under_competence = await api_client.post(
        NODES, json=evidence(lc_taxonomy.competence.id, "LC-E1.8"), headers=admin.headers
    )
    orphan = await api_client.post(
        NODES,
        json={"module": "LC", "kind": "assertion", "code": "LC-A7", "name": "Sin padre"},
        headers=admin.headers,
    )
    repeated = await api_client.post(
        NODES, json=evidence(lc_taxonomy.assertion.id), headers=admin.headers
    )

    assert created.status_code == 201, created.text
    body = created.json()
    assert (body["kind"], body["code"], body["parent_id"]) == (
        "evidence",
        "LC-E1.9",
        str(lc_taxonomy.assertion.id),
    )
    assert (body["active"], body["in_use"]) == (True, False)
    assert under_competence.status_code == 422
    assert orphan.status_code == 422
    assert repeated.status_code == 409
    assert repeated.json()["type"].endswith("taxonomy-code-taken")


async def test_editar_el_peso_avisa_si_la_suma_no_da_uno(
    api_client: httpx.AsyncClient, admin: Staff, lc_taxonomy: LcTaxonomy
) -> None:
    url = f"{NODES}/{lc_taxonomy.assertion.id}"

    off = await api_client.patch(url, json={"target_weight": 0.3}, headers=admin.headers)
    renamed = await api_client.patch(
        url,
        json={"name": "Contenidos locales del texto", "description": None},
        headers=admin.headers,
    )
    fine = await api_client.patch(
        f"{NODES}/{lc_taxonomy.other_assertion.id}",
        json={"target_weight": 0.7},
        headers=admin.headers,
    )
    empty = await api_client.patch(url, json={}, headers=admin.headers)

    assert off.status_code == 200, off.text
    assert off.json()["target_weight"] == 0.3
    assert off.json()["warnings"] == [
        "Los pesos de las afirmaciones de LC suman 0,7; deberían sumar cerca de 1."
    ]
    assert renamed.json()["name"] == "Contenidos locales del texto"
    assert fine.json()["warnings"] == []
    assert empty.status_code == 422


async def test_desactivar_reactivar_y_borrar(
    api_client: httpx.AsyncClient,
    admin: Staff,
    lc_taxonomy: LcTaxonomy,
    content_uow: UowFactory,
    app_engine: AsyncEngine,
) -> None:
    new = await api_client.post(
        NODES, json=evidence(lc_taxonomy.assertion.id), headers=admin.headers
    )
    new_id = new.json()["id"]
    service = importer(content_uow, datetime(2026, 10, 10, 12, 0, tzinfo=UTC))
    job = await service.preview(bank_file([lc_item(1)]), "b.json", uuid4())
    assert job.id is not None
    await service.confirm(
        job.id, job.created_by, target_state=VersionState.DRAFT, originality_declared=True
    )

    with_children = await api_client.delete(
        f"{NODES}/{lc_taxonomy.competence.id}", headers=admin.headers
    )
    used = await api_client.delete(f"{NODES}/{lc_taxonomy.evidence.id}", headers=admin.headers)
    off = await api_client.patch(
        f"{NODES}/{lc_taxonomy.evidence.id}", json={"active": False}, headers=admin.headers
    )
    listed = await api_client.get("/api/v1/content/modules", headers=admin.headers)
    everything = await api_client.get(
        "/api/v1/content/modules", params={"include_inactive": True}, headers=admin.headers
    )
    on = await api_client.patch(
        f"{NODES}/{lc_taxonomy.evidence.id}", json={"active": True}, headers=admin.headers
    )
    deleted = await api_client.delete(f"{NODES}/{new_id}", headers=admin.headers)
    missing = await api_client.delete(f"{NODES}/{new_id}", headers=admin.headers)

    assert with_children.status_code == 409
    assert with_children.json()["type"].endswith("taxonomy-node-in-use")
    assert used.status_code == 409
    assert (off.json()["active"], off.json()["in_use"]) == (False, True)

    def codes(response: httpx.Response) -> set[str]:
        lc = next(m for m in response.json()["items"] if m["code"] == "LC")
        return {node["code"] for node in lc["nodes"]}

    assert "LC-E1.1" not in codes(listed)
    assert "LC-E1.1" in codes(everything)
    assert on.json()["active"] is True
    assert deleted.status_code == 204
    assert missing.status_code == 404
    assert await changes(app_engine) == [
        ("node", "created", False, True),
        ("node", "deactivated", True, True),
        ("node", "reactivated", True, True),
        ("node", "deleted", True, False),
    ]


async def test_la_meta_del_modulo(
    api_client: httpx.AsyncClient, admin: Staff, lc_taxonomy: LcTaxonomy, app_engine: AsyncEngine
) -> None:
    url = "/api/v1/content/modules/LC"

    updated = await api_client.patch(url, json={"bank_target": 200}, headers=admin.headers)
    invalid = await api_client.patch(url, json={"bank_target": 0}, headers=admin.headers)

    assert updated.status_code == 200, updated.text
    assert (updated.json()["code"], updated.json()["bank_target"]) == ("LC", 200)
    assert len(updated.json()["nodes"]) == 5
    assert invalid.status_code == 422
    assert await changes(app_engine) == [("module", "updated", True, True)]


async def test_crear_y_editar_una_rubrica(
    api_client: httpx.AsyncClient, admin: Staff, app_engine: AsyncEngine
) -> None:
    created = await api_client.post(RUBRICS, json=rubric(), headers=admin.headers)
    repeated = await api_client.post(RUBRICS, json=rubric(), headers=admin.headers)
    one_level = await api_client.post(
        RUBRICS, json=rubric("RUB-CE-10", levels=1), headers=admin.headers
    )
    rubric_id = created.json()["id"]
    edited = await api_client.put(
        f"{RUBRICS}/{rubric_id}",
        json={**rubric(), "name": "Texto argumentativo (2026)", "active": False},
        headers=admin.headers,
    )
    missing = await api_client.put(f"{RUBRICS}/{uuid4()}", json=rubric(), headers=admin.headers)

    assert created.status_code == 201, created.text
    assert created.json()["code"] == "RUB-CE-09"
    assert repeated.status_code == 409
    assert repeated.json()["type"].endswith("rubric-code-taken")
    assert one_level.status_code == 422
    assert edited.status_code == 200, edited.text
    assert (edited.json()["name"], edited.json()["active"]) == ("Texto argumentativo (2026)", False)
    assert missing.status_code == 404
    assert await changes(app_engine) == [
        ("rubric", "created", False, True),
        ("rubric", "updated", True, True),
    ]


async def test_un_docente_no_cambia_la_taxonomia(
    api_client: httpx.AsyncClient, staff: StaffFactory, lc_taxonomy: LcTaxonomy
) -> None:
    teacher = (await staff(Role.TEACHER)).headers
    node = f"{NODES}/{lc_taxonomy.evidence.id}"

    responses = [
        await api_client.post(NODES, json=evidence(lc_taxonomy.assertion.id), headers=teacher),
        await api_client.patch(node, json={"name": "Otro"}, headers=teacher),
        await api_client.delete(node, headers=teacher),
        await api_client.patch(
            "/api/v1/content/modules/LC", json={"bank_target": 10}, headers=teacher
        ),
        await api_client.post(RUBRICS, json=rubric(), headers=teacher),
        await api_client.put(f"{RUBRICS}/{uuid4()}", json=rubric(), headers=teacher),
    ]

    assert [r.status_code for r in responses] == [403] * 6
