"""T042: API de revisión, consulta e historia (US2; contrato: `approveItem`, `returnItem`,
`rejectItem`, `retireItem`, `commentItem`, `listItems`, `getItem`, `getItemHistory`).
"""

from datetime import UTC, datetime
from uuid import UUID

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncEngine

from saber_uli.content.domain.context import Origin
from saber_uli.content.domain.item import Item
from saber_uli.content.domain.item_version import (
    Difficulty,
    ItemContent,
    ItemKind,
    Option,
    VersionState,
)
from saber_uli.content.domain.taxonomy import TaxonomyTags
from saber_uli.identity.application.directory import IdentityDirectory
from saber_uli.identity.domain.roles import Role
from saber_uli.identity.infrastructure.unit_of_work import SqlAlchemyIdentityUnitOfWork
from saber_uli.shared.application.event_bus import EventBus
from saber_uli.shared.infrastructure.db import create_session_factory
from tests.integration.content.conftest import LcTaxonomy, UowFactory
from tests.integration.identity.staff import Staff, StaffFactory

NOW = datetime(2026, 10, 9, 15, 0, tzinfo=UTC)
BASE = "/api/v1/content/items"


async def store(
    content_uow: UowFactory,
    tax: LcTaxonomy,
    code: str,
    *,
    author: UUID | None = None,
    stem: str = "¿Qué indica la expresión?",
    state: VersionState = VersionState.IN_REVIEW,
    origin: Origin = Origin.TEACHER,
    difficulty: Difficulty = Difficulty.LOW,
    assertion: str = "assertion",
    contributors: tuple[UUID, ...] = (),
    publish_by: UUID | None = None,
) -> None:
    node = getattr(tax, assertion)
    evidence = tax.evidence.id if assertion == "assertion" else None
    content = ItemContent(
        difficulty=difficulty,
        stem_md=stem,
        explanation_md="Se apoya en el texto.",
        taxonomy=TaxonomyTags(
            competence_id=tax.competence.id, assertion_id=node.id, evidence_id=evidence
        ),
        options=tuple(
            Option(key=k, text=f"Opción {k}", correct=k == "A", feedback=f"Porque {k}")
            for k in "ABCD"
        ),
    )
    item = Item.create(
        code=code,
        module_code="LC",
        kind=ItemKind.SELECTION,
        origin=origin,
        content=content,
        content_hash=b"h",
        fingerprint=code.encode(),
        context_version_id=None,
        actor=author,
        now=NOW,
        state=state,
    )
    for person in contributors:
        item.edit(content, b"h", code.encode(), None, person, NOW, keep_in_review=True)
    if publish_by is not None:
        item.approve(publish_by, NOW, confirms_alignment=True, confirms_originality=True)
    async with content_uow() as uow:
        await uow.items.add(item)
        await uow.commit()


def etag(response: httpx.Response) -> str:
    return response.headers["ETag"]


@pytest.fixture
async def people(staff: StaffFactory) -> dict[str, Staff]:
    return {
        "teacher": await staff(Role.TEACHER),
        "admin": await staff(Role.ADMIN),
        "other_admin": await staff(Role.ADMIN),
    }


async def test_aprobar_devolver_rechazar_y_retirar_con_if_match(
    api_client: httpx.AsyncClient,
    content_uow: UowFactory,
    lc_taxonomy: LcTaxonomy,
    people: dict[str, Staff],
) -> None:
    teacher, admin = people["teacher"], people["admin"]
    for code in ("LC-0001", "LC-0002", "LC-0003"):
        await store(content_uow, lc_taxonomy, code, author=teacher.id)

    item = await api_client.get(f"{BASE}/LC-0001", headers=admin.headers)
    assert item.status_code == 200
    assert etag(item) == '"0"'
    approved = await api_client.post(
        f"{BASE}/LC-0001/approval",
        json={"confirms_alignment": True, "confirms_originality": True},
        headers={**admin.headers, "If-Match": etag(item)},
    )
    assert approved.status_code == 200, approved.text
    assert approved.json()["published"]["state"] == "published"
    assert approved.json()["published"]["reviewer"]["id"] == str(admin.id)
    assert etag(approved) == '"1"'

    returned = await api_client.post(
        f"{BASE}/LC-0002/return",
        json={"comment": "Revisa la opción C."},
        headers={**admin.headers, "If-Match": '"0"'},
    )
    assert returned.status_code == 200
    assert returned.json()["open"]["state"] == "draft"
    assert returned.json()["last_review_comment"] == "Revisa la opción C."

    rejected = await api_client.post(
        f"{BASE}/LC-0003/rejection",
        json={"reason": "Ambiguo"},
        headers={**admin.headers, "If-Match": '"0"'},
    )
    assert rejected.status_code == 200
    assert rejected.json()["open"] is None and rejected.json()["published"] is None

    retired = await api_client.post(
        f"{BASE}/LC-0001/retirement",
        json={"reason": "Fin"},
        headers={**admin.headers, "If-Match": '"1"'},
    )
    assert retired.status_code == 200
    assert retired.json()["published"] is None


async def test_un_docente_no_revisa_pero_comenta(
    api_client: httpx.AsyncClient,
    content_uow: UowFactory,
    lc_taxonomy: LcTaxonomy,
    people: dict[str, Staff],
) -> None:
    teacher = people["teacher"]
    await store(content_uow, lc_taxonomy, "LC-0001")
    headers = {**teacher.headers, "If-Match": '"0"'}

    for action, body in (
        ("approval", {"confirms_alignment": True, "confirms_originality": True}),
        ("return", {"comment": "x"}),
        ("rejection", {"reason": "x"}),
        ("retirement", {"reason": "x"}),
    ):
        response = await api_client.post(f"{BASE}/LC-0001/{action}", json=body, headers=headers)
        assert response.status_code == 403, action

    comment = await api_client.post(
        f"{BASE}/LC-0001/comments", json={"comment": "¿La B es ambigua?"}, headers=teacher.headers
    )
    assert comment.status_code == 201
    assert comment.json()["type"] == "commented"
    assert comment.json()["actor"]["id"] == str(teacher.id)


async def test_sin_if_match_o_con_otra_revision(
    api_client: httpx.AsyncClient,
    content_uow: UowFactory,
    lc_taxonomy: LcTaxonomy,
    people: dict[str, Staff],
) -> None:
    await store(content_uow, lc_taxonomy, "LC-0001")
    admin = people["admin"]
    body = {"confirms_alignment": True, "confirms_originality": True}

    missing = await api_client.post(f"{BASE}/LC-0001/approval", json=body, headers=admin.headers)
    stale = await api_client.post(
        f"{BASE}/LC-0001/approval", json=body, headers={**admin.headers, "If-Match": '"5"'}
    )

    assert missing.status_code == 428
    assert stale.status_code == 412
    assert stale.json()["etag"] == '"0"'
    assert stale.json()["current"]["code"] == "LC-0001"


async def test_la_autoaprobacion_se_ve_en_can_y_se_rechaza(
    api_client: httpx.AsyncClient,
    content_uow: UowFactory,
    lc_taxonomy: LcTaxonomy,
    people: dict[str, Staff],
) -> None:
    admin = people["admin"]
    await store(content_uow, lc_taxonomy, "LC-0001", author=admin.id)

    seen = await api_client.get(f"{BASE}/LC-0001", headers=admin.headers)
    response = await api_client.post(
        f"{BASE}/LC-0001/approval",
        json={"confirms_alignment": True, "confirms_originality": True},
        headers={**admin.headers, "If-Match": '"0"'},
    )
    other = await api_client.get(f"{BASE}/LC-0001", headers=people["other_admin"].headers)

    assert seen.json()["can"]["approve"] is False
    assert seen.json()["can"]["approve_blocked_reason"] == "self_approval"
    assert response.status_code == 403
    assert response.json()["type"].endswith("self-approval-forbidden")
    assert other.json()["can"]["approve"] is True


async def test_listar_filtrar_y_buscar(
    api_client: httpx.AsyncClient,
    content_uow: UowFactory,
    lc_taxonomy: LcTaxonomy,
    people: dict[str, Staff],
) -> None:
    admin = people["admin"]
    await store(content_uow, lc_taxonomy, "LC-0001", stem="Los estudiantes leyeron columnas")
    await store(
        content_uow,
        lc_taxonomy,
        "LC-0002",
        origin=Origin.AI,
        difficulty=Difficulty.HIGH,
        assertion="other_assertion",
    )
    await store(content_uow, lc_taxonomy, "LC-0003", publish_by=people["other_admin"].id)

    async def codes(**params: str) -> list[str]:
        response = await api_client.get(BASE, params=params, headers=admin.headers)
        assert response.status_code == 200, response.text
        return [item["code"] for item in response.json()["items"]]

    assert await codes() == ["LC-0001", "LC-0002", "LC-0003"]
    assert await codes(state="published") == ["LC-0003"]
    assert await codes(state="in_review") == ["LC-0001", "LC-0002"]
    assert await codes(origin="ai") == ["LC-0002"]
    assert await codes(difficulty="high") == ["LC-0002"]
    assert await codes(module="RC") == []
    # La competencia incluye a sus descendientes (las dos afirmaciones).
    assert await codes(taxonomy_node=str(lc_taxonomy.competence.id)) == [
        "LC-0001",
        "LC-0002",
        "LC-0003",
    ]
    assert await codes(taxonomy_node=str(lc_taxonomy.other_assertion.id)) == ["LC-0002"]
    assert await codes(q="columna estudiante") == ["LC-0001"]
    assert await codes(q="LC-0002") == ["LC-0002"]
    page = await api_client.get(BASE, params={"page": "2", "page_size": "2"}, headers=admin.headers)
    assert page.json()["meta"] == {"page": 2, "page_size": 2, "total": 3}
    assert [item["code"] for item in page.json()["items"]] == ["LC-0003"]


async def test_la_cola_de_revision_y_quien_puede_aprobar(
    api_client: httpx.AsyncClient,
    content_uow: UowFactory,
    lc_taxonomy: LcTaxonomy,
    people: dict[str, Staff],
    app_engine: AsyncEngine,
) -> None:
    admin = people["admin"]
    directory = IdentityDirectory(
        uow_factory=lambda: SqlAlchemyIdentityUnitOfWork(
            create_session_factory(app_engine), EventBus()
        )
    )
    admins = sorted(await directory.active_admin_ids())
    await store(content_uow, lc_taxonomy, "LC-0001", author=admin.id)
    await store(content_uow, lc_taxonomy, "LC-0002", contributors=tuple(admins))
    await store(content_uow, lc_taxonomy, "LC-0003")

    queue = await api_client.get(BASE, params={"awaiting_my_review": "true"}, headers=admin.headers)
    everything = await api_client.get(BASE, headers=admin.headers)

    assert [item["code"] for item in queue.json()["items"]] == ["LC-0003"]
    flags = {i["code"]: i["needs_another_reviewer"] for i in everything.json()["items"]}
    assert flags == {"LC-0001": False, "LC-0002": True, "LC-0003": False}
    summary = everything.json()["items"][0]
    assert summary["open_version"] == {"number": 1, "state": "in_review"}
    assert summary["published_version"] is None


async def test_historia_con_nombres(
    api_client: httpx.AsyncClient,
    content_uow: UowFactory,
    lc_taxonomy: LcTaxonomy,
    people: dict[str, Staff],
) -> None:
    teacher, admin = people["teacher"], people["admin"]
    await store(content_uow, lc_taxonomy, "LC-0001", author=teacher.id, publish_by=admin.id)

    response = await api_client.get(f"{BASE}/LC-0001/history", headers=teacher.headers)

    assert response.status_code == 200
    body = response.json()
    [version] = body["versions"]
    assert version["number"] == 1 and version["state"] == "published"
    assert version["author"] == {"id": str(teacher.id), "display_name": teacher.display_name}
    assert version["reviewer"]["id"] == str(admin.id)
    assert [event["type"] for event in body["events"]] == ["created", "approved"]
    assert body["events"][1]["actor"]["display_name"] == admin.display_name


async def test_la_busqueda_resiste_nul_y_paginas_enormes(
    api_client: httpx.AsyncClient, people: dict[str, Staff]
) -> None:
    # Hallazgos de Schemathesis: el carácter NUL y un desplazamiento mayor que BIGINT daban 500.
    headers = people["teacher"].headers

    nul = await api_client.get(BASE, params={"q": "\x00"}, headers=headers)
    huge = await api_client.get(BASE, params={"page": 368934881474191034}, headers=headers)

    assert nul.status_code == 200
    assert (huge.status_code, huge.json()["items"]) == (200, [])
