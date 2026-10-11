"""T051: imágenes de los contextos (US3; FR-009, FR-046; research R-11).

Solo PNG, JPEG o WebP verificados por su contenido, hasta 1 MB y 4 000 px por lado; se
re-codifican sin metadatos (EXIF puede llevar la ubicación). La misma imagen se guarda una vez.
Quien tiene `content:author` descarga cualquiera; los demás, solo las de versiones publicadas o
retiradas (FR-046).
"""

import io
import os
from datetime import UTC, datetime

import httpx
import pytest
from PIL import Image

from saber_uli.content.api.media_router import MEDIA_UPLOAD_PER_USER
from saber_uli.content.application.authoring import Authoring
from saber_uli.content.application.contexts import Contexts
from saber_uli.content.application.review import Review
from saber_uli.content.domain.context import ContextContent, ContextKind
from saber_uli.content.domain.item_version import Difficulty, ItemContent, ItemKind, Option
from saber_uli.content.domain.taxonomy import TaxonomyTags
from saber_uli.identity.domain.roles import Role
from saber_uli.shared.domain.clock import FixedClock
from tests.integration.conftest import CommittedLogin
from tests.integration.content.conftest import LcTaxonomy, UowFactory
from tests.integration.identity.staff import StaffFactory, accept_current_policy

URL = "/api/v1/content/media"
NOW = datetime(2026, 10, 9, 18, 0, tzinfo=UTC)


def image(fmt: str, size: tuple[int, int] = (40, 30), *, exif: bool = False) -> bytes:
    picture = Image.new("RGB", size, (200, 30, 30))
    buffer = io.BytesIO()
    if exif:
        data = Image.Exif()
        data[0x010E] = "Foto tomada en casa"  # ImageDescription
        data[0x010F] = "Cámara"  # Make
        picture.save(buffer, fmt, exif=data.tobytes())
    else:
        picture.save(buffer, fmt)
    return buffer.getvalue()


def upload(content: bytes, name: str = "imagen.png") -> dict[str, tuple[str, bytes, str]]:
    return {"file": (name, content, "application/octet-stream")}


@pytest.fixture
async def teacher(staff: StaffFactory) -> dict[str, str]:
    return (await staff(Role.TEACHER)).headers


@pytest.mark.parametrize(
    ("fmt", "content_type"), [("PNG", "image/png"), ("JPEG", "image/jpeg"), ("WEBP", "image/webp")]
)
async def test_guarda_png_jpeg_y_webp(
    api_client: httpx.AsyncClient, teacher: dict[str, str], fmt: str, content_type: str
) -> None:
    response = await api_client.post(URL, files=upload(image(fmt)), headers=teacher)

    assert response.status_code == 201, response.text
    body = response.json()
    assert (body["content_type"], body["width"], body["height"]) == (content_type, 40, 30)
    assert body["url"] == f"{URL}/{body['id']}"


async def test_quita_los_metadatos_exif(
    api_client: httpx.AsyncClient, teacher: dict[str, str]
) -> None:
    original = image("JPEG", exif=True)
    assert len(Image.open(io.BytesIO(original)).getexif()) > 0

    created = await api_client.post(URL, files=upload(original, "foto.jpg"), headers=teacher)
    stored = await api_client.get(created.json()["url"], headers=teacher)

    assert stored.status_code == 200
    assert len(Image.open(io.BytesIO(stored.content)).getexif()) == 0


@pytest.mark.parametrize(
    ("content", "name"),
    [
        (b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>', "x.svg"),
        (image("GIF"), "x.gif"),
        (image("PNG")[:60], "truncada.png"),
        (b"no es una imagen", "x.png"),
    ],
)
async def test_rechaza_lo_que_no_es_png_jpeg_ni_webp(
    api_client: httpx.AsyncClient, teacher: dict[str, str], content: bytes, name: str
) -> None:
    response = await api_client.post(URL, files=upload(content, name), headers=teacher)

    assert response.status_code == 415
    assert response.json()["type"].endswith("unsupported-media-type")


async def test_mas_de_un_mega_es_413(
    api_client: httpx.AsyncClient, teacher: dict[str, str]
) -> None:
    noise = Image.frombytes("RGB", (700, 700), os.urandom(700 * 700 * 3))
    buffer = io.BytesIO()
    noise.save(buffer, "PNG")
    assert len(buffer.getvalue()) > 1_048_576

    response = await api_client.post(URL, files=upload(buffer.getvalue()), headers=teacher)

    assert response.status_code == 413
    assert response.json()["type"].endswith("file-too-large")


async def test_mas_de_4000_px_por_lado_es_415(
    api_client: httpx.AsyncClient, teacher: dict[str, str]
) -> None:
    response = await api_client.post(URL, files=upload(image("PNG", (4001, 1))), headers=teacher)

    assert response.status_code == 415


async def test_la_misma_imagen_se_guarda_una_vez(
    api_client: httpx.AsyncClient, teacher: dict[str, str]
) -> None:
    content = image("PNG")

    first = await api_client.post(URL, files=upload(content), headers=teacher)
    second = await api_client.post(URL, files=upload(content), headers=teacher)

    assert first.json()["id"] == second.json()["id"]


async def test_un_estudiante_solo_ve_imagenes_de_contenido_publicado(
    api_client: httpx.AsyncClient,
    teacher: dict[str, str],
    committed_login: CommittedLogin,
    app_engine: object,
    content_uow: UowFactory,
    lc_taxonomy: LcTaxonomy,
    staff: StaffFactory,
) -> None:
    published_media = (
        await api_client.post(URL, files=upload(image("PNG", (41, 30))), headers=teacher)
    ).json()
    draft_media = (
        await api_client.post(URL, files=upload(image("PNG", (42, 30))), headers=teacher)
    ).json()
    clock = FixedClock(NOW)
    contexts = Contexts(uow_factory=content_uow, clock=clock)
    authoring = Authoring(uow_factory=content_uow, clock=clock)
    review = Review(uow_factory=content_uow, clock=clock)
    author = (await staff(Role.TEACHER)).id
    admin = (await staff(Role.ADMIN)).id
    for code, media in (("LC-CTX-501", published_media), ("LC-CTX-502", draft_media)):
        await contexts.create(
            code=code,
            module="LC",
            content=ContextContent(
                kind=ContextKind.IMAGE,
                title="Infografía",
                media_id=media["id"],
                alt_text="Infografía de préstamos",
                text_type_node_id=lc_taxonomy.text_type.id,
            ),
            actor=author,
        )
    for code, context in (("LC-0501", "LC-CTX-501"), ("LC-0502", "LC-CTX-502")):
        await authoring.create(
            code=code,
            module="LC",
            kind=ItemKind.SELECTION,
            content=ItemContent(
                difficulty=Difficulty.LOW,
                stem_md=f"¿Qué muestra la infografía? {code}",
                explanation_md="La imagen lo indica.",
                taxonomy=TaxonomyTags(
                    competence_id=lc_taxonomy.competence.id,
                    assertion_id=lc_taxonomy.assertion.id,
                    evidence_id=lc_taxonomy.evidence.id,
                ),
                options=tuple(
                    Option(key=k, text=f"{code} {k}", correct=k == "A", feedback=f"Por {k}")
                    for k in "ABCD"
                ),
                context_code=context,
            ),
            actor=author,
        )
    await authoring.submit("LC-0501", author, expected_revision=0)
    await review.approve(
        "LC-0501", admin, expected_revision=1, confirms_alignment=True, confirms_originality=True
    )
    student, token = await committed_login(Role.STUDENT)
    assert student.id is not None
    await accept_current_policy(app_engine, student.id)  # type: ignore[arg-type]
    headers = {"Authorization": f"Bearer {token}"}

    public = await api_client.get(published_media["url"], headers=headers)
    hidden = await api_client.get(draft_media["url"], headers=headers)
    by_teacher = await api_client.get(draft_media["url"], headers=teacher)

    assert public.status_code == 200
    assert public.headers["Cache-Control"] == "private, max-age=31536000, immutable"
    assert public.headers["Content-Type"] == "image/png"
    assert hidden.status_code == 404
    assert by_teacher.status_code == 200


async def test_limite_de_60_subidas_por_hora_por_usuario(
    api_client: httpx.AsyncClient, teacher: dict[str, str], staff: StaffFactory
) -> None:
    assert MEDIA_UPLOAD_PER_USER.limit == "60/hour"
    content = image("PNG", (8, 8))

    statuses = [
        (await api_client.post(URL, files=upload(content), headers=teacher)).status_code
        for _ in range(61)
    ]
    other = await api_client.post(
        URL, files=upload(content), headers=(await staff(Role.TEACHER)).headers
    )

    assert statuses == [201] * 60 + [429]
    assert other.status_code == 201  # el límite es por persona
