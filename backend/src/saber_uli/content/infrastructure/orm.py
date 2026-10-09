"""Mapeos SQLAlchemy del esquema `content` (data-model.md §2).

Reflejan exactamente la migración 0008: `test_repositories.py` compara este modelo con el esquema
migrado. Son filas de persistencia, no el dominio: los repositorios traducen entre ellas y los
agregados de `content.domain`. Los `CHECK` viven en la migración y no se repiten aquí.
"""

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import (
    Boolean,
    Computed,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    Numeric,
    SmallInteger,
    Text,
    UniqueConstraint,
    Uuid,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column

from saber_uli.shared.infrastructure.db import Base

SCHEMA = "content"
_UUIDV7 = text("uuidv7()")
# Las columnas JSONB que admiten nulos usan `none_as_null`: sin él, un `None` de Python se guarda
# como el JSON `null` y no como NULL de SQL (los CHECK de data-model esperan NULL).
_NOW = text("now()")


def _fk(target: str, name: str, **kwargs: Any) -> ForeignKey:
    return ForeignKey(f"{SCHEMA}.{target}", name=name, **kwargs)


def _pk() -> Mapped[UUID]:
    return mapped_column(Uuid, primary_key=True, server_default=_UUIDV7)


def _ts(*, nullable: bool = False, default_now: bool = False) -> Any:
    return mapped_column(
        DateTime(timezone=True), nullable=nullable, server_default=_NOW if default_now else None
    )


# §2.1 ---------------------------------------------------------------------------------------
class ModuleRow(Base):
    __tablename__ = "modules"
    __table_args__ = ({"schema": SCHEMA},)

    code: Mapped[str] = mapped_column(Text, primary_key=True)
    name: Mapped[str] = mapped_column(Text)
    question_type: Mapped[str] = mapped_column(Text)
    options_per_item: Mapped[int | None] = mapped_column(SmallInteger)
    max_context_words: Mapped[int | None] = mapped_column(SmallInteger)
    exam_questions: Mapped[int] = mapped_column(SmallInteger)
    bank_target: Mapped[int] = mapped_column(Integer)
    position: Mapped[int] = mapped_column(SmallInteger)


# §2.2 ---------------------------------------------------------------------------------------
class TaxonomyNodeRow(Base):
    __tablename__ = "taxonomy_nodes"
    __table_args__ = (
        UniqueConstraint("code", name="uq_taxonomy_nodes_code"),
        Index("ix_taxonomy_nodes_module", "module_code", "kind", "position"),
        Index("ix_taxonomy_nodes_parent", "parent_id"),
        {"schema": SCHEMA},
    )

    id: Mapped[UUID] = _pk()
    module_code: Mapped[str] = mapped_column(
        Text, _fk("modules.code", "fk_taxonomy_nodes_module", ondelete="RESTRICT")
    )
    kind: Mapped[str] = mapped_column(Text)
    code: Mapped[str] = mapped_column(Text)
    name: Mapped[str] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    parent_id: Mapped[UUID | None] = mapped_column(
        Uuid, _fk("taxonomy_nodes.id", "fk_taxonomy_nodes_parent", ondelete="RESTRICT")
    )
    target_weight: Mapped[Decimal | None] = mapped_column(Numeric(4, 3))
    part_options: Mapped[int | None] = mapped_column(SmallInteger)
    part_format: Mapped[str | None] = mapped_column(Text)
    active: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))
    position: Mapped[int] = mapped_column(SmallInteger)


# §2.3 ---------------------------------------------------------------------------------------
class RubricRow(Base):
    __tablename__ = "rubrics"
    __table_args__ = (UniqueConstraint("code", name="uq_rubrics_code"), {"schema": SCHEMA})

    id: Mapped[UUID] = _pk()
    code: Mapped[str] = mapped_column(Text)
    name: Mapped[str] = mapped_column(Text)
    note: Mapped[str | None] = mapped_column(Text)
    relevance_condition: Mapped[dict[str, Any]] = mapped_column(JSONB)
    dimensions: Mapped[list[dict[str, Any]]] = mapped_column(JSONB)
    active: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))


# §2.4 ---------------------------------------------------------------------------------------
class MediaRow(Base):
    __tablename__ = "media"
    __table_args__ = (UniqueConstraint("sha256", name="uq_media_sha256"), {"schema": SCHEMA})

    id: Mapped[UUID] = _pk()
    sha256: Mapped[bytes] = mapped_column(LargeBinary)
    content_type: Mapped[str] = mapped_column(Text)
    width: Mapped[int] = mapped_column(Integer)
    height: Mapped[int] = mapped_column(Integer)
    size_bytes: Mapped[int] = mapped_column(Integer)
    data: Mapped[bytes] = mapped_column(LargeBinary)
    created_by: Mapped[UUID] = mapped_column(Uuid)
    created_at: Mapped[datetime] = _ts(default_now=True)


# §2.5 ---------------------------------------------------------------------------------------
class ContextRow(Base):
    __tablename__ = "contexts"
    __table_args__ = (UniqueConstraint("code", name="uq_contexts_code"), {"schema": SCHEMA})

    id: Mapped[UUID] = _pk()
    code: Mapped[str] = mapped_column(Text)
    module_code: Mapped[str] = mapped_column(
        Text, _fk("modules.code", "fk_contexts_module", ondelete="RESTRICT")
    )
    current_version_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        _fk(
            "context_versions.id",
            "fk_contexts_current_version",
            deferrable=True,
            initially="DEFERRED",
            use_alter=True,
        ),
    )
    seed_hash: Mapped[bytes | None] = mapped_column(LargeBinary)
    revision: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    created_at: Mapped[datetime] = _ts(default_now=True)


class ContextVersionRow(Base):
    __tablename__ = "context_versions"
    __table_args__ = (
        UniqueConstraint("context_id", "number", name="uq_context_versions_number"),
        Index("ix_context_versions_media", "media_id"),
        {"schema": SCHEMA},
    )

    id: Mapped[UUID] = _pk()
    context_id: Mapped[UUID] = mapped_column(
        Uuid, _fk("contexts.id", "fk_context_versions_context", ondelete="RESTRICT")
    )
    number: Mapped[int] = mapped_column(Integer)
    kind: Mapped[str] = mapped_column(Text)
    title: Mapped[str] = mapped_column(Text)
    body_md: Mapped[str | None] = mapped_column(Text)
    media_id: Mapped[UUID | None] = mapped_column(
        Uuid, _fk("media.id", "fk_context_versions_media", ondelete="RESTRICT")
    )
    alt_text: Mapped[str | None] = mapped_column(Text)
    text_type_node_id: Mapped[UUID | None] = mapped_column(
        Uuid, _fk("taxonomy_nodes.id", "fk_context_versions_text_type", ondelete="RESTRICT")
    )
    part_node_id: Mapped[UUID | None] = mapped_column(
        Uuid, _fk("taxonomy_nodes.id", "fk_context_versions_part", ondelete="RESTRICT")
    )
    subtype: Mapped[str | None] = mapped_column(Text)
    shared_options: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB(none_as_null=True))
    word_count: Mapped[int | None] = mapped_column(Integer)
    origin: Mapped[str] = mapped_column(Text)
    content_hash: Mapped[bytes] = mapped_column(LargeBinary)
    created_by: Mapped[UUID | None] = mapped_column(Uuid)
    created_at: Mapped[datetime] = _ts(default_now=True)


# §2.6 ---------------------------------------------------------------------------------------
class ItemRow(Base):
    __tablename__ = "items"
    __table_args__ = (
        UniqueConstraint("code", name="uq_items_code"),
        Index("ix_items_module", "module_code"),
        Index("ix_items_code_pattern", "code", postgresql_ops={"code": "text_pattern_ops"}),
        {"schema": SCHEMA},
    )

    id: Mapped[UUID] = _pk()
    code: Mapped[str] = mapped_column(Text)
    module_code: Mapped[str] = mapped_column(
        Text, _fk("modules.code", "fk_items_module", ondelete="RESTRICT")
    )
    kind: Mapped[str] = mapped_column(Text)
    origin: Mapped[str] = mapped_column(Text)
    seed_hash: Mapped[bytes | None] = mapped_column(LargeBinary)
    revision: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    created_at: Mapped[datetime] = _ts(default_now=True)


# §2.7 ---------------------------------------------------------------------------------------
_SEARCH = (
    "to_tsvector('spanish'::regconfig, ((COALESCE(stem_md, ''::text) || ' '::text)"
    " || COALESCE(explanation_md, ''::text)))"
)


def _taxonomy_fk(column: str) -> Any:
    return mapped_column(
        Uuid, _fk("taxonomy_nodes.id", f"fk_item_versions_{column}", ondelete="RESTRICT")
    )


class ItemVersionRow(Base):
    __tablename__ = "item_versions"
    __table_args__ = (
        UniqueConstraint("item_id", "number", name="uq_item_versions_number"),
        Index(
            "ux_item_versions_one_published",
            "item_id",
            unique=True,
            postgresql_where=text("state = 'published'"),
        ),
        Index(
            "ux_item_versions_one_open",
            "item_id",
            unique=True,
            postgresql_where=text("state IN ('draft', 'in_review')"),
        ),
        Index("ix_item_versions_state", "state"),
        Index("ix_item_versions_assertion", "assertion_id"),
        Index("ix_item_versions_competence", "competence_id"),
        Index("ix_item_versions_component", "component_id"),
        Index("ix_item_versions_part", "part_id"),
        Index("ix_item_versions_difficulty", "difficulty"),
        Index("ix_item_versions_fingerprint", "fingerprint"),
        Index("ix_item_versions_context_version", "context_version_id"),
        Index("ix_item_versions_search", "search", postgresql_using="gin"),
        {"schema": SCHEMA},
    )

    id: Mapped[UUID] = _pk()
    item_id: Mapped[UUID] = mapped_column(
        Uuid, _fk("items.id", "fk_item_versions_item", ondelete="RESTRICT")
    )
    number: Mapped[int] = mapped_column(Integer)
    state: Mapped[str] = mapped_column(Text)
    context_version_id: Mapped[UUID | None] = mapped_column(
        Uuid, _fk("context_versions.id", "fk_item_versions_context_version", ondelete="RESTRICT")
    )
    difficulty: Mapped[str] = mapped_column(Text)
    competence_id: Mapped[UUID | None] = _taxonomy_fk("competence")
    assertion_id: Mapped[UUID | None] = _taxonomy_fk("assertion")
    evidence_id: Mapped[UUID | None] = _taxonomy_fk("evidence")
    component_id: Mapped[UUID | None] = _taxonomy_fk("component")
    situation_id: Mapped[UUID | None] = _taxonomy_fk("situation")
    part_id: Mapped[UUID | None] = _taxonomy_fk("part")
    stem_md: Mapped[str] = mapped_column(Text)
    options: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB(none_as_null=True))
    answer_key: Mapped[str | None] = mapped_column(Text)
    explanation_md: Mapped[str] = mapped_column(Text)
    prompt_context_md: Mapped[str | None] = mapped_column(Text)
    rubric_id: Mapped[UUID | None] = mapped_column(
        Uuid, _fk("rubrics.id", "fk_item_versions_rubric", ondelete="RESTRICT")
    )
    content_hash: Mapped[bytes] = mapped_column(LargeBinary)
    fingerprint: Mapped[bytes] = mapped_column(LargeBinary)
    search: Mapped[Any] = mapped_column(TSVECTOR, Computed(_SEARCH, persisted=True))
    author_id: Mapped[UUID | None] = mapped_column(Uuid)
    contributor_ids: Mapped[list[UUID]] = mapped_column(
        ARRAY(Uuid), server_default=text("'{}'::uuid[]")
    )
    submitted_at: Mapped[datetime | None] = _ts(nullable=True)
    submitted_by: Mapped[UUID | None] = mapped_column(Uuid)
    reviewed_at: Mapped[datetime | None] = _ts(nullable=True)
    reviewed_by: Mapped[UUID | None] = mapped_column(Uuid)
    published_at: Mapped[datetime | None] = _ts(nullable=True)
    retired_at: Mapped[datetime | None] = _ts(nullable=True)
    retired_by: Mapped[UUID | None] = mapped_column(Uuid)
    retire_reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = _ts(default_now=True)
    updated_at: Mapped[datetime] = _ts(default_now=True)


# §2.8 ---------------------------------------------------------------------------------------
class ItemEventRow(Base):
    __tablename__ = "item_events"
    __table_args__ = (
        Index("ix_item_events_item", "item_id", "occurred_at"),
        {"schema": SCHEMA},
    )

    id: Mapped[UUID] = _pk()
    item_id: Mapped[UUID] = mapped_column(
        Uuid, _fk("items.id", "fk_item_events_item", ondelete="RESTRICT")
    )
    version_id: Mapped[UUID | None] = mapped_column(
        Uuid, _fk("item_versions.id", "fk_item_events_version", ondelete="RESTRICT")
    )
    type: Mapped[str] = mapped_column(Text)
    actor_id: Mapped[UUID | None] = mapped_column(Uuid)
    occurred_at: Mapped[datetime] = _ts()
    comment: Mapped[str | None] = mapped_column(Text)
    reason: Mapped[str | None] = mapped_column(Text)
    details: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))


# §2.9 ---------------------------------------------------------------------------------------
class ImportRow(Base):
    __tablename__ = "imports"
    __table_args__ = (
        Index("ix_imports_created_by", "created_by", text("created_at DESC")),
        Index("ix_imports_pending", "expires_at", postgresql_where=text("status = 'pending'")),
        {"schema": SCHEMA},
    )

    id: Mapped[UUID] = _pk()
    created_by: Mapped[UUID] = mapped_column(Uuid)
    created_at: Mapped[datetime] = _ts()
    source_name: Mapped[str] = mapped_column(Text)
    format: Mapped[str] = mapped_column(Text)
    file_sha256: Mapped[bytes] = mapped_column(LargeBinary)
    status: Mapped[str] = mapped_column(Text, server_default=text("'pending'::text"))
    expires_at: Mapped[datetime] = _ts()
    summary: Mapped[dict[str, Any]] = mapped_column(JSONB)
    rows: Mapped[list[dict[str, Any]]] = mapped_column(JSONB)
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB(none_as_null=True))
    target_state: Mapped[str | None] = mapped_column(Text)
    originality_declared: Mapped[bool | None] = mapped_column(Boolean)
    confirmed_at: Mapped[datetime | None] = _ts(nullable=True)
    result: Mapped[dict[str, Any] | None] = mapped_column(JSONB(none_as_null=True))


# §2.10 --------------------------------------------------------------------------------------
class ExportRow(Base):
    __tablename__ = "exports"
    __table_args__ = ({"schema": SCHEMA},)

    id: Mapped[UUID] = _pk()
    created_by: Mapped[UUID] = mapped_column(Uuid)
    created_at: Mapped[datetime] = _ts()
    format: Mapped[str] = mapped_column(Text)
    filter: Mapped[dict[str, Any]] = mapped_column(JSONB)
    version_choice: Mapped[str] = mapped_column(Text)
    item_count: Mapped[int] = mapped_column(Integer)
    skipped_count: Mapped[int] = mapped_column(Integer, server_default=text("0"))


# §2.11 --------------------------------------------------------------------------------------
class TaxonomyChangeRow(Base):
    __tablename__ = "taxonomy_changes"
    __table_args__ = ({"schema": SCHEMA},)

    id: Mapped[UUID] = _pk()
    changed_by: Mapped[UUID] = mapped_column(Uuid)
    changed_at: Mapped[datetime] = _ts()
    target: Mapped[str] = mapped_column(Text)
    target_id: Mapped[str] = mapped_column(Text)
    action: Mapped[str] = mapped_column(Text)
    before: Mapped[dict[str, Any] | None] = mapped_column(JSONB(none_as_null=True))
    after: Mapped[dict[str, Any] | None] = mapped_column(JSONB(none_as_null=True))


# §2.12 --------------------------------------------------------------------------------------
class SeedLoadRow(Base):
    __tablename__ = "seed_loads"
    __table_args__ = ({"schema": SCHEMA},)

    id: Mapped[UUID] = _pk()
    loaded_at: Mapped[datetime] = _ts()
    file_sha256: Mapped[bytes] = mapped_column(LargeBinary)
    schema_version: Mapped[str] = mapped_column(Text)
    summary: Mapped[dict[str, Any]] = mapped_column(JSONB)
    pending_manual: Mapped[list[str]] = mapped_column(JSONB, server_default=text("'[]'::jsonb"))


# §2.13 --------------------------------------------------------------------------------------
class ItemVersionStatsRow(Base):
    __tablename__ = "item_version_stats"
    __table_args__ = (
        Index("ix_item_version_stats_signals", "signals", postgresql_using="gin"),
        {"schema": SCHEMA},
    )

    version_id: Mapped[UUID] = mapped_column(
        Uuid,
        _fk("item_versions.id", "fk_item_version_stats_version", ondelete="RESTRICT"),
        primary_key=True,
    )
    first_responses: Mapped[int] = mapped_column(Integer)
    correct_rate: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))
    option_rates: Mapped[dict[str, Any] | None] = mapped_column(JSONB(none_as_null=True))
    discrimination: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))
    signals: Mapped[list[str]] = mapped_column(ARRAY(Text), server_default=text("'{}'::text[]"))
    computed_at: Mapped[datetime] = _ts()
