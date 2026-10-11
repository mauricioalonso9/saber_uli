"""T023: persistencia de `content` (data-model §2; research R-02, R-09, R-14).

Guardar y leer conserva cada campo; los repositorios rechazan cambiar el contenido de una versión
publicada o retirada; `revision` sube con cada cambio; la historia solo se inserta; y el ORM
coincide con el esquema migrado.
"""

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import Connection, NullPool, text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from saber_uli.content.application.ports import ImmutableVersionError
from saber_uli.content.domain.context import (
    Context,
    ContextContent,
    ContextKind,
    ContextVersion,
    Origin,
    SharedOption,
)
from saber_uli.content.domain.item import Item
from saber_uli.content.domain.item_version import (
    Difficulty,
    ItemContent,
    ItemKind,
    Option,
    VersionState,
)
from saber_uli.content.domain.media import Media
from saber_uli.content.domain.rubric import RelevanceCondition, Rubric, RubricDimension, RubricLevel
from saber_uli.content.domain.taxonomy import TaxonomyTags
from saber_uli.shared.infrastructure.db import Base
from tests.integration.content.conftest import LC_MODULE, LcTaxonomy, UowFactory

T0 = datetime(2026, 10, 9, 12, 0, tzinfo=UTC)
AUTHOR = uuid4()
EDITOR = uuid4()
ADMIN = uuid4()


def at(minutes: int) -> datetime:
    return T0 + timedelta(minutes=minutes)


def lc_context(code: str = "LC-CTX-001", body: str = "Texto de opinión.") -> Context:
    version = ContextVersion(
        id=None,
        number=1,
        content=ContextContent(kind=ContextKind.TEXT, title="Desconectar", body_md=body),
        word_count=3,
        origin=Origin.AI,
        content_hash=b"ctx-1",
        created_by=None,
        created_at=T0,
    )
    return Context(id=None, code=code, module_code="LC", current=version, seed_hash=b"seed")


def lc_item(tax: LcTaxonomy, context: Context | None = None, code: str = "LC-0001") -> Item:
    content = ItemContent(
        difficulty=Difficulty.MEDIUM,
        stem_md="¿Qué indica la expresión?",
        explanation_md="Se apoya en el segundo párrafo.",
        taxonomy=TaxonomyTags(
            competence_id=tax.competence.id,
            assertion_id=tax.assertion.id,
            evidence_id=tax.evidence.id,
        ),
        options=tuple(
            Option(key=k, text=f"Opción {k}", correct=k == "B", feedback=f"Porque {k}")
            for k in "ABCD"
        ),
        context_code=None if context is None else context.code,
    )
    return Item.create(
        code=code,
        module_code="LC",
        kind=ItemKind.SELECTION,
        origin=Origin.TEACHER,
        content=content,
        content_hash=b"h1",
        fingerprint=b"f1",
        context_version_id=None if context is None else context.current.id,
        actor=AUTHOR,
        now=T0,
    )


async def test_modulos_taxonomia_y_rubricas(
    content_uow: UowFactory, lc_taxonomy: LcTaxonomy
) -> None:
    rubric = Rubric(
        id=None,
        code="RUB-CE-01",
        name="Rúbrica de práctica",
        note="Propia",
        relevance_condition=RelevanceCondition(name="Pertinencia", description="Responde"),
        dimensions=(
            RubricDimension(
                code="planteamiento",
                name="Planteamiento",
                levels=(RubricLevel(1, "Confusa"), RubricLevel(2, "Clara")),
            ),
        ),
    )
    async with content_uow() as uow:
        stored = await uow.rubrics.add(rubric)
        await uow.commit()

    async with content_uow() as uow:
        modules = await uow.modules.list()
        nodes = await uow.taxonomy.list(module_code="LC")
        loaded = await uow.rubrics.get_by_code("RUB-CE-01")
        by_code = await uow.taxonomy.get_by_code("LC-A1")

    assert modules == [LC_MODULE]
    assert {node.code for node in nodes} == {
        "LC-C1",
        "LC-A1",
        "LC-E1.1",
        "LC-A2",
        "continuo_informativo",
    }
    assert by_code == lc_taxonomy.assertion
    assert loaded == replace(rubric, id=stored.id)


async def test_contexto_con_versiones_y_opciones_compartidas(content_uow: UowFactory) -> None:
    async with content_uow() as uow:
        await uow.modules.add(replace(LC_MODULE, code="ING", name="Inglés", max_context_words=None))
        options = tuple(SharedOption(k, f"word {k}", f"«{k}»…") for k in "ABCDEFGH")
        context = Context(
            id=None,
            code="ING-CTX-P1-001",
            module_code="ING",
            current=ContextVersion(
                id=None,
                number=1,
                content=ContextContent(
                    kind=ContextKind.SHARED_OPTIONS,
                    title="Part 1",
                    body_md="Match",
                    shared_options=options,
                ),
                word_count=None,
                origin=Origin.AI,
                content_hash=b"c1",
                created_by=None,
                created_at=T0,
            ),
        )
        await uow.contexts.add(context)
        await uow.commit()

    async with content_uow() as uow:
        loaded = await uow.contexts.get_by_code("ING-CTX-P1-001", for_update=True)
        assert loaded is not None
        new_version = replace(
            loaded.current,
            id=None,
            number=2,
            content=replace(loaded.current.content, title="Part 1 (v2)"),
            content_hash=b"c2",
            created_by=EDITOR,
            created_at=at(1),
        )
        await uow.contexts.add_version(loaded, new_version)
        await uow.commit()

    async with content_uow() as uow:
        again = await uow.contexts.get_by_code("ING-CTX-P1-001")

    assert again is not None
    assert again.current.number == 2
    assert again.current.content.title == "Part 1 (v2)"
    assert again.current.content.shared_options == options
    assert again.current.created_by == EDITOR
    assert again.revision == 1


async def test_item_con_su_version_abierta_e_historia(
    content_uow: UowFactory, lc_taxonomy: LcTaxonomy
) -> None:
    async with content_uow() as uow:
        context = await uow.contexts.add(lc_context())
        item = await uow.items.add(lc_item(lc_taxonomy, context))
        await uow.commit()

    async with content_uow() as uow:
        loaded = await uow.items.get_by_code("LC-0001")

    assert loaded is not None
    assert loaded.id == item.id
    assert loaded.revision == 0
    version = loaded.open
    assert version is not None
    expected = item.versions[0]
    assert version.content == expected.content
    assert version.contributor_ids == {AUTHOR}
    assert version.context_version_id == context.current.id
    assert (version.content_hash, version.fingerprint) == (b"h1", b"f1")
    assert await _event_types(content_uow, "LC-0001") == ["created"]


async def test_publicar_y_crear_una_version_nueva(
    content_uow: UowFactory, lc_taxonomy: LcTaxonomy
) -> None:
    async with content_uow() as uow:
        await uow.items.add(lc_item(lc_taxonomy))
        await uow.commit()
    async with content_uow() as uow:
        item = await uow.items.get_by_code("LC-0001", for_update=True)
        assert item is not None
        item.submit(AUTHOR, at(1))
        item.approve(ADMIN, at(2), confirms_alignment=True, confirms_originality=True)
        await uow.items.save(item)
        await uow.commit()
    async with content_uow() as uow:
        item = await uow.items.get_by_code("LC-0001", for_update=True)
        assert item is not None
        assert item.published is not None and item.open is None
        open_content = replace(item.published.content, stem_md="Versión 2")
        item.edit(open_content, b"h2", b"f2", None, EDITOR, at(3))
        await uow.items.save(item)
        await uow.commit()

    async with content_uow() as uow:
        loaded = await uow.items.get_by_code("LC-0001")

    assert loaded is not None
    assert loaded.revision == 3
    assert loaded.last_number == 2
    assert loaded.published is not None and loaded.published.number == 1
    assert loaded.published.reviewed_by == ADMIN
    assert loaded.published.published_at == at(2)
    assert loaded.open is not None and loaded.open.number == 2
    assert loaded.open.content.stem_md == "Versión 2"
    assert loaded.open.state is VersionState.DRAFT
    assert await _event_types(content_uow, "LC-0001") == [
        "created",
        "submitted",
        "approved",
        "edited",
    ]


async def test_no_se_puede_cambiar_el_contenido_de_una_version_publicada(
    content_uow: UowFactory, lc_taxonomy: LcTaxonomy
) -> None:
    async with content_uow() as uow:
        item = lc_item(lc_taxonomy)
        item.submit(AUTHOR, at(1))
        item.approve(ADMIN, at(2), confirms_alignment=True, confirms_originality=True)
        await uow.items.add(item)
        await uow.commit()
    async with content_uow() as uow:
        item = await uow.items.get_by_code("LC-0001", for_update=True)
        assert item is not None and item.published is not None
        item.published.content = replace(item.published.content, stem_md="Cambiado a escondidas")
        item.published.content_hash = b"otro"

        with pytest.raises(ImmutableVersionError):
            await uow.items.save(item)


async def test_buscar_por_huella_excluye_el_mismo_item(
    content_uow: UowFactory, lc_taxonomy: LcTaxonomy
) -> None:
    async with content_uow() as uow:
        first = await uow.items.add(lc_item(lc_taxonomy))
        await uow.commit()

    async with content_uow() as uow:
        assert await uow.items.code_with_fingerprint(b"f1") == "LC-0001"
        assert await uow.items.code_with_fingerprint(b"f1", excluding=first.id) is None
        assert await uow.items.code_with_fingerprint(b"otra") is None


async def test_imagenes_por_identificador_y_por_huella(content_uow: UowFactory) -> None:
    media = Media(
        id=None,
        sha256=b"\x01" * 32,
        content_type="image/png",
        width=10,
        height=20,
        size_bytes=3,
        data=b"\x89PN",
        created_by=AUTHOR,
        created_at=T0,
    )
    async with content_uow() as uow:
        stored = await uow.media.add(media)
        await uow.commit()

    async with content_uow() as uow:
        assert stored.id is not None
        assert await uow.media.get(stored.id) == stored
        assert await uow.media.get_by_sha256(b"\x01" * 32) == stored


async def _event_types(content_uow: UowFactory, code: str) -> list[str]:
    async with content_uow() as uow:
        return [event.type.value for event in await uow.items.history(code)]


# --- El ORM coincide con las migraciones ----------------------------------------------------


def _diffs(connection: Connection) -> list[object]:
    def include_object(obj: object, name: str | None, type_: str, *_: object) -> bool:
        schema = getattr(obj, "schema", None) or getattr(
            getattr(obj, "table", None), "schema", None
        )
        return schema == "content"

    context = MigrationContext.configure(
        connection,
        opts={"include_schemas": True, "include_object": include_object, "compare_type": True},
    )
    return list(compare_metadata(context, Base.metadata))


async def test_el_orm_coincide_con_el_esquema_migrado(migrated_database: dict[str, str]) -> None:
    import saber_uli.content.infrastructure.orm  # noqa: F401 - registra las tablas

    engine = create_async_engine(migrated_database["migrator"], poolclass=NullPool)
    async with engine.connect() as conn:
        diffs = await conn.run_sync(_diffs)
    await engine.dispose()

    assert diffs == []


async def test_la_historia_solo_se_inserta(app_engine: AsyncEngine) -> None:
    async with app_engine.connect() as conn:
        privileges = (
            await conn.execute(
                text(
                    """SELECT privilege_type FROM information_schema.role_table_grants
                       WHERE table_schema = 'content' AND table_name = 'item_events'
                         AND grantee = 'saber_app'"""
                )
            )
        ).scalars()
        assert set(privileges) == {"SELECT", "INSERT"}
