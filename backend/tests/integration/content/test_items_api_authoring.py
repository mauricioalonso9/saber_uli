"""T052: API de autoría (US3; FR-015, FR-016, FR-020, FR-024, FR-026, FR-027).

`createItem`, `saveItemDraft`, `submitItem`, `createContext`, `getContext`, `updateContext` y
`getItemVersion` según el contrato: `ETag` en las respuestas, 428 sin `If-Match` y 412 con otra
revisión, `keep_in_review` y las diferencias campo por campo frente a la versión anterior.
"""

from typing import Any

import httpx
import pytest

from saber_uli.identity.domain.roles import Role
from tests.integration.content.conftest import LcTaxonomy
from tests.integration.identity.staff import Staff, StaffFactory

ITEMS = "/api/v1/content/items"
CONTEXTS = "/api/v1/content/contexts"


@pytest.fixture
async def people(staff: StaffFactory) -> dict[str, Staff]:
    return {"teacher": await staff(Role.TEACHER), "admin": await staff(Role.ADMIN)}


def context_body(tax: LcTaxonomy, body: str = "Un texto breve de opinión.") -> dict[str, Any]:
    return {
        "kind": "text",
        "title": "Desconectar para aprender",
        "body_md": body,
        "text_type_node_id": str(tax.text_type.id),
    }


def content(tax: LcTaxonomy, stem: str = "¿Cuál es la tesis del autor?") -> dict[str, Any]:
    return {
        "difficulty": "medium",
        "context_code": "LC-CTX-301",
        "taxonomy": {
            "competence_id": str(tax.competence.id),
            "assertion_id": str(tax.assertion.id),
            "evidence_id": str(tax.evidence.id),
        },
        "stem_md": stem,
        "options": [
            {"key": k, "text": f"Opción {k}", "correct": k == "A", "feedback": f"Porque {k}."}
            for k in "ABCD"
        ],
        "explanation_md": "La tesis aparece en el primer párrafo.",
    }


def if_match(response: httpx.Response) -> dict[str, str]:
    return {"If-Match": response.headers["ETag"]}


async def create_context(
    client: httpx.AsyncClient, tax: LcTaxonomy, headers: dict[str, str]
) -> httpx.Response:
    response = await client.post(
        CONTEXTS, json={"code": "LC-CTX-301", "module": "LC", **context_body(tax)}, headers=headers
    )
    assert response.status_code == 201, response.text
    return response


async def create_item(
    client: httpx.AsyncClient, tax: LcTaxonomy, headers: dict[str, str], code: str = "LC-0301"
) -> httpx.Response:
    response = await client.post(
        ITEMS,
        json={"code": code, "module": "LC", "kind": "selection", "content": content(tax, code)},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response


async def publish(
    client: httpx.AsyncClient, people: dict[str, Staff], created: httpx.Response
) -> httpx.Response:
    code = created.json()["code"]
    teacher, admin = people["teacher"].headers, people["admin"].headers
    sent = await client.post(f"{ITEMS}/{code}/submission", headers={**teacher, **if_match(created)})
    assert sent.status_code == 200, sent.text
    approved = await client.post(
        f"{ITEMS}/{code}/approval",
        json={"confirms_alignment": True, "confirms_originality": True},
        headers={**admin, **if_match(sent)},
    )
    assert approved.status_code == 200, approved.text
    return approved


async def test_crear_contexto_e_item_con_etag(
    api_client: httpx.AsyncClient, people: dict[str, Staff], lc_taxonomy: LcTaxonomy
) -> None:
    teacher = people["teacher"].headers

    context = await create_context(api_client, lc_taxonomy, teacher)
    item = await create_item(api_client, lc_taxonomy, teacher)
    repeated = await api_client.post(
        ITEMS,
        json={
            "code": "LC-0301",
            "module": "LC",
            "kind": "selection",
            "content": content(lc_taxonomy, "Otro"),
        },
        headers=teacher,
    )
    usage = await api_client.get(f"{CONTEXTS}/LC-CTX-301", headers=teacher)

    assert context.headers["ETag"] == '"0"'
    assert context.json()["version"] == 1
    assert context.json()["word_count"] == 5
    assert item.headers["ETag"] == f'"{item.json()["revision"]}"'
    assert item.json()["open"]["state"] == "draft"
    assert item.json()["open"]["author"]["id"] == str(people["teacher"].id)
    assert repeated.status_code == 409
    assert repeated.json()["type"].endswith("code-taken")
    assert usage.status_code == 200
    assert (usage.json()["item_count"], usage.json()["published_item_count"]) == (1, 0)
    assert usage.json()["items"] == [{"code": "LC-0301", "state": "draft"}]


async def test_el_contexto_invalido_responde_422_con_regla(
    api_client: httpx.AsyncClient, people: dict[str, Staff], lc_taxonomy: LcTaxonomy
) -> None:
    response = await api_client.post(
        CONTEXTS,
        json={
            "code": "LC-CTX-302",
            "module": "LC",
            **context_body(lc_taxonomy, " ".join(["palabra"] * 501)),
        },
        headers=people["teacher"].headers,
    )

    assert response.status_code == 422
    [error] = response.json()["errors"]
    assert error["rule"] == "context_word_limit"
    assert error["field"]


async def test_guardar_y_enviar_exigen_if_match(
    api_client: httpx.AsyncClient, people: dict[str, Staff], lc_taxonomy: LcTaxonomy
) -> None:
    teacher = people["teacher"].headers
    await create_context(api_client, lc_taxonomy, teacher)
    item = await create_item(api_client, lc_taxonomy, teacher)
    draft = f"{ITEMS}/LC-0301/draft"

    missing = await api_client.put(draft, json=content(lc_taxonomy, "Nuevo"), headers=teacher)
    stale = await api_client.put(
        draft, json=content(lc_taxonomy, "Nuevo"), headers={**teacher, "If-Match": '"9"'}
    )
    saved = await api_client.put(
        draft, json=content(lc_taxonomy, "Nuevo"), headers={**teacher, **if_match(item)}
    )
    submit_without = await api_client.post(f"{ITEMS}/LC-0301/submission", headers=teacher)

    assert missing.status_code == 428
    assert stale.status_code == 412
    assert stale.json()["type"].endswith("edit-conflict")
    assert stale.json()["current"]["code"] == "LC-0301"
    assert saved.status_code == 200
    assert saved.json()["open"]["content"]["stem_md"] == "Nuevo"
    assert saved.headers["ETag"] != item.headers["ETag"]
    assert submit_without.status_code == 428


async def test_enviar_con_problemas_responde_422_con_campo_y_regla(
    api_client: httpx.AsyncClient, people: dict[str, Staff], lc_taxonomy: LcTaxonomy
) -> None:
    teacher = people["teacher"].headers
    await create_context(api_client, lc_taxonomy, teacher)
    incomplete = content(lc_taxonomy)
    incomplete["options"][1]["feedback"] = ""
    created = await api_client.post(
        ITEMS,
        json={"code": "LC-0301", "module": "LC", "kind": "selection", "content": incomplete},
        headers=teacher,
    )
    assert created.status_code == 201, created.text

    sent = await api_client.post(
        f"{ITEMS}/LC-0301/submission", headers={**teacher, **if_match(created)}
    )

    assert sent.status_code == 422
    assert sent.json()["type"].endswith("validation-error")
    errors = {(error["field"], error["rule"]) for error in sent.json()["errors"]}
    assert ("options[B].feedback", "option_feedback_required") in errors


async def test_keep_in_review(
    api_client: httpx.AsyncClient, people: dict[str, Staff], lc_taxonomy: LcTaxonomy
) -> None:
    teacher = people["teacher"].headers
    await create_context(api_client, lc_taxonomy, teacher)
    item = await create_item(api_client, lc_taxonomy, teacher)
    sent = await api_client.post(
        f"{ITEMS}/LC-0301/submission", headers={**teacher, **if_match(item)}
    )
    draft = f"{ITEMS}/LC-0301/draft"

    kept = await api_client.put(
        draft,
        params={"keep_in_review": "true"},
        json=content(lc_taxonomy, "Ajuste menor"),
        headers={**teacher, **if_match(sent)},
    )
    returned = await api_client.put(
        draft, json=content(lc_taxonomy, "Cambio mayor"), headers={**teacher, **if_match(kept)}
    )

    assert kept.status_code == 200, kept.text
    assert kept.json()["open"]["state"] == "in_review"
    assert returned.status_code == 200
    assert returned.json()["open"]["state"] == "draft"


async def test_editar_lo_publicado_crea_version_con_diferencias(
    api_client: httpx.AsyncClient, people: dict[str, Staff], lc_taxonomy: LcTaxonomy
) -> None:
    teacher = people["teacher"].headers
    await create_context(api_client, lc_taxonomy, teacher)
    published = await publish(
        api_client, people, await create_item(api_client, lc_taxonomy, teacher)
    )
    changed = content(lc_taxonomy, "Enunciado corregido")
    changed["options"][1]["feedback"] = "Confunde la tesis con un ejemplo."
    changed["taxonomy"]["assertion_id"] = str(lc_taxonomy.other_assertion.id)

    saved = await api_client.put(
        f"{ITEMS}/LC-0301/draft", json=changed, headers={**teacher, **if_match(published)}
    )
    version = await api_client.get(f"{ITEMS}/LC-0301/versions/2", headers=teacher)

    assert saved.status_code == 200, saved.text
    assert saved.json()["published"]["number"] == 1
    assert saved.json()["open"]["number"] == 2
    changes = {change["field"]: change for change in version.json()["changes"]}
    assert set(changes) == {"stem_md", "options[B].feedback", "taxonomy.assertion_id"}
    assert changes["stem_md"]["after"] == "Enunciado corregido"
    assert changes["taxonomy.assertion_id"]["before"] == str(lc_taxonomy.assertion.id)


async def test_actualizar_contexto_propaga_y_exige_if_match(
    api_client: httpx.AsyncClient, people: dict[str, Staff], lc_taxonomy: LcTaxonomy
) -> None:
    teacher = people["teacher"].headers
    context = await create_context(api_client, lc_taxonomy, teacher)
    await publish(api_client, people, await create_item(api_client, lc_taxonomy, teacher))
    await create_item(api_client, lc_taxonomy, teacher, code="LC-0302")
    url = f"{CONTEXTS}/LC-CTX-301"
    body = context_body(lc_taxonomy, "Texto corregido por el docente.")

    missing = await api_client.put(url, json=body, headers=teacher)
    updated = await api_client.put(url, json=body, headers={**teacher, **if_match(context)})
    stale = await api_client.put(url, json=body, headers={**teacher, **if_match(context)})

    assert missing.status_code == 428
    assert updated.status_code == 200, updated.text
    assert updated.headers["ETag"] == '"1"'
    result = updated.json()
    assert result["context"]["version"] == 2
    assert result["new_review_versions"] == ["LC-0301"]
    assert result["rebased_open_versions"] == ["LC-0302"]
    assert stale.status_code == 412
    assert stale.json()["current"]["revision"] == 1


async def test_un_estudiante_no_crea_items(
    api_client: httpx.AsyncClient, staff: StaffFactory, lc_taxonomy: LcTaxonomy
) -> None:
    student = await staff(Role.STUDENT)

    response = await api_client.post(
        ITEMS,
        json={
            "code": "LC-0301",
            "module": "LC",
            "kind": "selection",
            "content": content(lc_taxonomy),
        },
        headers=student.headers,
    )

    assert response.status_code == 403
