"""`listRubrics` (adelantada de T105 porque el editor de consignas de US3 la necesita; FR-004).

Lectura con `content:author`: el docente elige la rúbrica de una consigna de Comunicación escrita.
"""

import httpx

from saber_uli.content.domain.rubric import (
    RelevanceCondition,
    Rubric,
    RubricDimension,
    RubricLevel,
)
from saber_uli.identity.domain.roles import Role
from tests.integration.content.conftest import UowFactory
from tests.integration.identity.staff import StaffFactory

URL = "/api/v1/content/rubrics"


async def test_lista_las_rubricas_para_quien_crea_items(
    api_client: httpx.AsyncClient, staff: StaffFactory, content_uow: UowFactory
) -> None:
    async with content_uow() as uow:
        await uow.rubrics.add(
            Rubric(
                id=None,
                code="RUB-PRUEBA",
                name="Texto argumentativo",
                relevance_condition=RelevanceCondition(name="Pertinencia", description="Responde"),
                dimensions=(
                    RubricDimension(
                        code="planteamiento",
                        name="Planteamiento",
                        levels=(RubricLevel(1, "Confusa"), RubricLevel(2, "Clara")),
                    ),
                ),
            )
        )
        await uow.commit()
    teacher = await staff(Role.TEACHER)
    student = await staff(Role.STUDENT)

    response = await api_client.get(URL, headers=teacher.headers)
    forbidden = await api_client.get(URL, headers=student.headers)

    assert response.status_code == 200
    rubric = next(r for r in response.json()["items"] if r["code"] == "RUB-PRUEBA")
    assert rubric["name"] == "Texto argumentativo"
    assert rubric["dimensions"][0]["levels"][1] == {"level": 2, "description": "Clara"}
    assert forbidden.status_code == 403
