"""T112: `listContexts` (contrato; FR-026): los contextos con su versión vigente y cuántos ítems
los usan, filtrables por módulo y por texto en el código o el título, paginados.
"""

import httpx

from saber_uli.identity.domain.roles import Role
from tests.integration.content.conftest import UowFactory
from tests.integration.content.seed_bank import bank, publish
from tests.integration.identity.staff import StaffFactory

__all__ = ["bank"]  # fixture

URL = "/api/v1/content/contexts"


async def test_lista_los_contextos_con_su_uso(
    api_client: httpx.AsyncClient, staff: StaffFactory, content_uow: UowFactory, bank: None
) -> None:
    teacher = (await staff(Role.TEACHER)).headers
    await publish(content_uow, "LC-0001")

    everything = await api_client.get(URL, headers=teacher)
    lc = await api_client.get(URL, params={"module": "LC"}, headers=teacher)
    found = await api_client.get(URL, params={"q": "laboratorio"}, headers=teacher)
    by_code = await api_client.get(URL, params={"q": "ctx-p4"}, headers=teacher)
    page = await api_client.get(URL, params={"page": 2, "page_size": 3}, headers=teacher)
    student = await api_client.get(URL, headers=(await staff()).headers)

    assert everything.status_code == 200, everything.text
    assert everything.json()["meta"] == {"page": 1, "page_size": 25, "total": 8}
    [first] = [c for c in lc.json()["items"] if c["code"] == "LC-CTX-001"]
    assert first["module"] == "LC"
    assert (first["kind"], first["version"]) == ("text", 1)
    assert first["word_count"] is not None
    assert (first["item_count"], first["published_item_count"]) == (3, 1)
    assert [c["code"] for c in lc.json()["items"]] == ["LC-CTX-001", "LC-CTX-002", "LC-CTX-003"]
    assert [c["code"] for c in found.json()["items"]] == ["LC-CTX-003"]
    assert [c["code"] for c in by_code.json()["items"]] == ["ING-CTX-P4-001"]
    assert page.json()["meta"]["total"] == 8
    assert len(page.json()["items"]) == 3
    assert student.status_code == 403
