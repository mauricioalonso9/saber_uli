"""content: banco de ítems (spec 002; data-model.md §2; ADR 0008).

Las restricciones citan su sección de data-model.md. Los permisos de `saber_app` llegan en 0009.
Las referencias a personas (`*_by`, `author_id`…) son identificadores de `identity.users` sin
clave foránea entre esquemas (principio II; research R-14).

Revisión: 0008
Anterior: 0007
Creada: 2026-10-09
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0008"
down_revision: str | Sequence[str] | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ORIGINS = "('seed', 'teacher', 'ai')"

UPGRADE = [
    "CREATE SCHEMA content",
    # §2.1 modules ----------------------------------------------------------------------------
    """
    CREATE TABLE content.modules (
        code               text      NOT NULL,
        name               text      NOT NULL,
        question_type      text      NOT NULL,
        options_per_item   smallint,
        max_context_words  smallint,
        exam_questions     smallint  NOT NULL,
        bank_target        integer   NOT NULL,
        position           smallint  NOT NULL,
        CONSTRAINT pk_modules PRIMARY KEY (code),
        CONSTRAINT ck_modules_question_type CHECK (question_type IN ('selection', 'writing')),
        CONSTRAINT ck_modules_bank_target CHECK (bank_target BETWEEN 1 AND 10000)
    )
    """,
    # §2.2 taxonomy_nodes ---------------------------------------------------------------------
    """
    CREATE TABLE content.taxonomy_nodes (
        id             uuid          NOT NULL DEFAULT uuidv7(),
        module_code    text          NOT NULL,
        kind           text          NOT NULL,
        code           text          NOT NULL,
        name           text          NOT NULL,
        description    text,
        parent_id      uuid,
        target_weight  numeric(4,3),
        part_options   smallint,
        part_format    text,
        active         boolean       NOT NULL DEFAULT true,
        position       smallint      NOT NULL,
        CONSTRAINT pk_taxonomy_nodes PRIMARY KEY (id),
        CONSTRAINT uq_taxonomy_nodes_code UNIQUE (code),
        CONSTRAINT fk_taxonomy_nodes_module FOREIGN KEY (module_code)
            REFERENCES content.modules (code) ON DELETE RESTRICT,
        CONSTRAINT fk_taxonomy_nodes_parent FOREIGN KEY (parent_id)
            REFERENCES content.taxonomy_nodes (id) ON DELETE RESTRICT,
        CONSTRAINT ck_taxonomy_nodes_kind CHECK (kind IN ('competence', 'assertion', 'evidence',
            'component', 'situation', 'text_type', 'part')),
        CONSTRAINT ck_taxonomy_nodes_target_weight CHECK (target_weight BETWEEN 0 AND 1),
        CONSTRAINT ck_taxonomy_nodes_part_format
            CHECK (part_format IS NULL OR part_format IN ('matching', 'selection')),
        -- Solo una parte de Inglés tiene número y formato de opciones.
        CONSTRAINT ck_taxonomy_nodes_part_fields CHECK (
            kind = 'part' OR (part_options IS NULL AND part_format IS NULL)
        )
    )
    """,
    "CREATE INDEX ix_taxonomy_nodes_module ON content.taxonomy_nodes (module_code, kind, position)",
    "CREATE INDEX ix_taxonomy_nodes_parent ON content.taxonomy_nodes (parent_id)",
    # §2.3 rubrics ----------------------------------------------------------------------------
    """
    CREATE TABLE content.rubrics (
        id                   uuid     NOT NULL DEFAULT uuidv7(),
        code                 text     NOT NULL,
        name                 text     NOT NULL,
        note                 text,
        relevance_condition  jsonb    NOT NULL,
        dimensions           jsonb    NOT NULL,
        active               boolean  NOT NULL DEFAULT true,
        CONSTRAINT pk_rubrics PRIMARY KEY (id),
        CONSTRAINT uq_rubrics_code UNIQUE (code)
    )
    """,
    # §2.4 media ------------------------------------------------------------------------------
    """
    CREATE TABLE content.media (
        id            uuid         NOT NULL DEFAULT uuidv7(),
        sha256        bytea        NOT NULL,
        content_type  text         NOT NULL,
        width         integer      NOT NULL,
        height        integer      NOT NULL,
        size_bytes    integer      NOT NULL,
        data          bytea        NOT NULL,
        created_by    uuid         NOT NULL,
        created_at    timestamptz  NOT NULL DEFAULT now(),
        CONSTRAINT pk_media PRIMARY KEY (id),
        CONSTRAINT uq_media_sha256 UNIQUE (sha256),
        CONSTRAINT ck_media_content_type
            CHECK (content_type IN ('image/png', 'image/jpeg', 'image/webp')),
        CONSTRAINT ck_media_size_bytes CHECK (size_bytes BETWEEN 1 AND 1048576),
        CONSTRAINT ck_media_dimensions
            CHECK (width BETWEEN 1 AND 4000 AND height BETWEEN 1 AND 4000)
    )
    """,
    # §2.5 contexts y context_versions --------------------------------------------------------
    """
    CREATE TABLE content.contexts (
        id                  uuid         NOT NULL DEFAULT uuidv7(),
        code                text         NOT NULL,
        module_code         text         NOT NULL,
        current_version_id  uuid,
        seed_hash           bytea,
        revision            integer      NOT NULL DEFAULT 0,
        created_at          timestamptz  NOT NULL DEFAULT now(),
        CONSTRAINT pk_contexts PRIMARY KEY (id),
        CONSTRAINT uq_contexts_code UNIQUE (code),
        CONSTRAINT fk_contexts_module FOREIGN KEY (module_code)
            REFERENCES content.modules (code) ON DELETE RESTRICT,
        CONSTRAINT ck_contexts_revision CHECK (revision >= 0)
    )
    """,
    f"""
    CREATE TABLE content.context_versions (
        id                 uuid         NOT NULL DEFAULT uuidv7(),
        context_id         uuid         NOT NULL,
        number             integer      NOT NULL,
        kind               text         NOT NULL,
        title              text         NOT NULL,
        body_md            text,
        media_id           uuid,
        alt_text           text,
        text_type_node_id  uuid,
        part_node_id       uuid,
        subtype            text,
        shared_options     jsonb,
        word_count         integer,
        origin             text         NOT NULL,
        content_hash       bytea        NOT NULL,
        created_by         uuid,
        created_at         timestamptz  NOT NULL DEFAULT now(),
        CONSTRAINT pk_context_versions PRIMARY KEY (id),
        CONSTRAINT uq_context_versions_number UNIQUE (context_id, number),
        CONSTRAINT fk_context_versions_context FOREIGN KEY (context_id)
            REFERENCES content.contexts (id) ON DELETE RESTRICT,
        CONSTRAINT fk_context_versions_media FOREIGN KEY (media_id)
            REFERENCES content.media (id) ON DELETE RESTRICT,
        CONSTRAINT fk_context_versions_text_type FOREIGN KEY (text_type_node_id)
            REFERENCES content.taxonomy_nodes (id) ON DELETE RESTRICT,
        CONSTRAINT fk_context_versions_part FOREIGN KEY (part_node_id)
            REFERENCES content.taxonomy_nodes (id) ON DELETE RESTRICT,
        CONSTRAINT ck_context_versions_kind
            CHECK (kind IN ('text', 'table', 'image', 'shared_options')),
        CONSTRAINT ck_context_versions_origin CHECK (origin IN {ORIGINS}),
        CONSTRAINT ck_context_versions_number CHECK (number >= 1),
        -- FR-007: Lectura crítica hasta 500 palabras.
        CONSTRAINT ck_context_versions_word_count
            CHECK (word_count IS NULL OR word_count <= 500),
        -- FR-009: toda imagen con texto alternativo.
        CONSTRAINT ck_context_versions_alt_text
            CHECK (kind <> 'image' OR length(trim(alt_text)) > 0),
        CONSTRAINT ck_context_versions_image_media CHECK (kind <> 'image' OR media_id IS NOT NULL),
        CONSTRAINT ck_context_versions_shared_options
            CHECK (kind <> 'shared_options' OR jsonb_typeof(shared_options) = 'array')
    )
    """,
    """
    ALTER TABLE content.contexts ADD CONSTRAINT fk_contexts_current_version
        FOREIGN KEY (current_version_id) REFERENCES content.context_versions (id)
        DEFERRABLE INITIALLY DEFERRED
    """,
    "CREATE INDEX ix_context_versions_media ON content.context_versions (media_id)",
    # §2.6 items ------------------------------------------------------------------------------
    f"""
    CREATE TABLE content.items (
        id           uuid         NOT NULL DEFAULT uuidv7(),
        code         text         NOT NULL,
        module_code  text         NOT NULL,
        kind         text         NOT NULL,
        origin       text         NOT NULL,
        seed_hash    bytea,
        revision     integer      NOT NULL DEFAULT 0,
        created_at   timestamptz  NOT NULL DEFAULT now(),
        CONSTRAINT pk_items PRIMARY KEY (id),
        CONSTRAINT uq_items_code UNIQUE (code),
        CONSTRAINT fk_items_module FOREIGN KEY (module_code)
            REFERENCES content.modules (code) ON DELETE RESTRICT,
        CONSTRAINT ck_items_kind CHECK (kind IN ('selection', 'matching', 'writing_prompt')),
        CONSTRAINT ck_items_origin CHECK (origin IN {ORIGINS}),
        CONSTRAINT ck_items_revision CHECK (revision >= 0)
    )
    """,
    "CREATE INDEX ix_items_module ON content.items (module_code)",
    "CREATE INDEX ix_items_code_pattern ON content.items (code text_pattern_ops)",
    # §2.7 item_versions ----------------------------------------------------------------------
    """
    CREATE TABLE content.item_versions (
        id                  uuid         NOT NULL DEFAULT uuidv7(),
        item_id             uuid         NOT NULL,
        number              integer      NOT NULL,
        state               text         NOT NULL,
        context_version_id  uuid,
        difficulty          text         NOT NULL,
        competence_id       uuid,
        assertion_id        uuid,
        evidence_id         uuid,
        component_id        uuid,
        situation_id        uuid,
        part_id             uuid,
        stem_md             text         NOT NULL,
        options             jsonb,
        answer_key          text,
        explanation_md      text         NOT NULL,
        prompt_context_md   text,
        rubric_id           uuid,
        content_hash        bytea        NOT NULL,
        fingerprint         bytea        NOT NULL,
        search              tsvector     GENERATED ALWAYS AS (
            to_tsvector('spanish'::regconfig,
                coalesce(stem_md, '') || ' ' || coalesce(explanation_md, ''))
        ) STORED,
        author_id           uuid,
        contributor_ids     uuid[]       NOT NULL DEFAULT '{}',
        submitted_at        timestamptz,
        submitted_by        uuid,
        reviewed_at         timestamptz,
        reviewed_by         uuid,
        published_at        timestamptz,
        retired_at          timestamptz,
        retired_by          uuid,
        retire_reason       text,
        created_at          timestamptz  NOT NULL DEFAULT now(),
        updated_at          timestamptz  NOT NULL DEFAULT now(),
        CONSTRAINT pk_item_versions PRIMARY KEY (id),
        CONSTRAINT uq_item_versions_number UNIQUE (item_id, number),
        CONSTRAINT fk_item_versions_item FOREIGN KEY (item_id)
            REFERENCES content.items (id) ON DELETE RESTRICT,
        CONSTRAINT fk_item_versions_context_version FOREIGN KEY (context_version_id)
            REFERENCES content.context_versions (id) ON DELETE RESTRICT,
        CONSTRAINT fk_item_versions_competence FOREIGN KEY (competence_id)
            REFERENCES content.taxonomy_nodes (id) ON DELETE RESTRICT,
        CONSTRAINT fk_item_versions_assertion FOREIGN KEY (assertion_id)
            REFERENCES content.taxonomy_nodes (id) ON DELETE RESTRICT,
        CONSTRAINT fk_item_versions_evidence FOREIGN KEY (evidence_id)
            REFERENCES content.taxonomy_nodes (id) ON DELETE RESTRICT,
        CONSTRAINT fk_item_versions_component FOREIGN KEY (component_id)
            REFERENCES content.taxonomy_nodes (id) ON DELETE RESTRICT,
        CONSTRAINT fk_item_versions_situation FOREIGN KEY (situation_id)
            REFERENCES content.taxonomy_nodes (id) ON DELETE RESTRICT,
        CONSTRAINT fk_item_versions_part FOREIGN KEY (part_id)
            REFERENCES content.taxonomy_nodes (id) ON DELETE RESTRICT,
        CONSTRAINT fk_item_versions_rubric FOREIGN KEY (rubric_id)
            REFERENCES content.rubrics (id) ON DELETE RESTRICT,
        CONSTRAINT ck_item_versions_state
            CHECK (state IN ('draft', 'in_review', 'published', 'retired')),
        CONSTRAINT ck_item_versions_difficulty CHECK (difficulty IN ('low', 'medium', 'high')),
        CONSTRAINT ck_item_versions_number CHECK (number >= 1),
        CONSTRAINT ck_item_versions_options
            CHECK (options IS NULL OR jsonb_typeof(options) = 'array'),
        CONSTRAINT ck_item_versions_retire_reason
            CHECK (state <> 'retired' OR retire_reason IS NOT NULL)
    )
    """,
    # FR-011: a lo sumo una publicada; R-02: a lo sumo una abierta.
    """
    CREATE UNIQUE INDEX ux_item_versions_one_published ON content.item_versions (item_id)
        WHERE state = 'published'
    """,
    """
    CREATE UNIQUE INDEX ux_item_versions_one_open ON content.item_versions (item_id)
        WHERE state IN ('draft', 'in_review')
    """,
    "CREATE INDEX ix_item_versions_state ON content.item_versions (state)",
    "CREATE INDEX ix_item_versions_assertion ON content.item_versions (assertion_id)",
    "CREATE INDEX ix_item_versions_competence ON content.item_versions (competence_id)",
    "CREATE INDEX ix_item_versions_component ON content.item_versions (component_id)",
    "CREATE INDEX ix_item_versions_part ON content.item_versions (part_id)",
    "CREATE INDEX ix_item_versions_difficulty ON content.item_versions (difficulty)",
    "CREATE INDEX ix_item_versions_fingerprint ON content.item_versions (fingerprint)",
    "CREATE INDEX ix_item_versions_context_version ON content.item_versions (context_version_id)",
    "CREATE INDEX ix_item_versions_search ON content.item_versions USING gin (search)",
    # §2.8 item_events (solo inserción, 0009) -------------------------------------------------
    """
    CREATE TABLE content.item_events (
        id           uuid         NOT NULL DEFAULT uuidv7(),
        item_id      uuid         NOT NULL,
        version_id   uuid,
        type         text         NOT NULL,
        actor_id     uuid,
        occurred_at  timestamptz  NOT NULL,
        comment      text,
        reason       text,
        details      jsonb        NOT NULL DEFAULT '{}',
        CONSTRAINT pk_item_events PRIMARY KEY (id),
        CONSTRAINT fk_item_events_item FOREIGN KEY (item_id)
            REFERENCES content.items (id) ON DELETE RESTRICT,
        CONSTRAINT fk_item_events_version FOREIGN KEY (version_id)
            REFERENCES content.item_versions (id) ON DELETE RESTRICT,
        CONSTRAINT ck_item_events_type CHECK (type IN ('created', 'edited', 'submitted',
            'approved', 'returned', 'rejected', 'retired', 'superseded', 'commented', 'imported',
            'seed_loaded', 'seed_versioned', 'context_changed', 'rebased_on_context'))
    )
    """,
    "CREATE INDEX ix_item_events_item ON content.item_events (item_id, occurred_at)",
    # §2.9 imports ----------------------------------------------------------------------------
    """
    CREATE TABLE content.imports (
        id                    uuid         NOT NULL DEFAULT uuidv7(),
        created_by            uuid         NOT NULL,
        created_at            timestamptz  NOT NULL,
        source_name           text         NOT NULL,
        format                text         NOT NULL,
        file_sha256           bytea        NOT NULL,
        status                text         NOT NULL DEFAULT 'pending',
        expires_at            timestamptz  NOT NULL,
        summary               jsonb        NOT NULL,
        rows                  jsonb        NOT NULL,
        payload               jsonb,
        target_state          text,
        originality_declared  boolean,
        confirmed_at          timestamptz,
        result                jsonb,
        CONSTRAINT pk_imports PRIMARY KEY (id),
        CONSTRAINT ck_imports_format CHECK (format IN ('json', 'xlsx')),
        CONSTRAINT ck_imports_status CHECK (status IN ('pending', 'confirmed', 'expired')),
        CONSTRAINT ck_imports_target_state
            CHECK (target_state IS NULL OR target_state IN ('draft', 'in_review')),
        -- FR-036: no hay confirmación sin la declaración de originalidad.
        CONSTRAINT ck_imports_confirmed
            CHECK (status <> 'confirmed' OR (originality_declared AND confirmed_at IS NOT NULL))
    )
    """,
    "CREATE INDEX ix_imports_created_by ON content.imports (created_by, created_at DESC)",
    "CREATE INDEX ix_imports_pending ON content.imports (expires_at) WHERE status = 'pending'",
    # §2.10 exports (solo inserción) ----------------------------------------------------------
    """
    CREATE TABLE content.exports (
        id              uuid         NOT NULL DEFAULT uuidv7(),
        created_by      uuid         NOT NULL,
        created_at      timestamptz  NOT NULL,
        format          text         NOT NULL,
        filter          jsonb        NOT NULL,
        version_choice  text         NOT NULL,
        item_count      integer      NOT NULL,
        skipped_count   integer      NOT NULL DEFAULT 0,
        CONSTRAINT pk_exports PRIMARY KEY (id),
        CONSTRAINT ck_exports_format CHECK (format IN ('json', 'xlsx')),
        CONSTRAINT ck_exports_version_choice CHECK (version_choice IN ('published', 'latest'))
    )
    """,
    # §2.11 taxonomy_changes (solo inserción) -------------------------------------------------
    """
    CREATE TABLE content.taxonomy_changes (
        id          uuid         NOT NULL DEFAULT uuidv7(),
        changed_by  uuid         NOT NULL,
        changed_at  timestamptz  NOT NULL,
        target      text         NOT NULL,
        target_id   text         NOT NULL,
        action      text         NOT NULL,
        before      jsonb,
        after       jsonb,
        CONSTRAINT pk_taxonomy_changes PRIMARY KEY (id),
        CONSTRAINT ck_taxonomy_changes_target CHECK (target IN ('node', 'rubric', 'module')),
        CONSTRAINT ck_taxonomy_changes_action CHECK (action IN ('created', 'updated',
            'deactivated', 'reactivated', 'deleted'))
    )
    """,
    # §2.12 seed_loads (solo inserción) -------------------------------------------------------
    """
    CREATE TABLE content.seed_loads (
        id              uuid         NOT NULL DEFAULT uuidv7(),
        loaded_at       timestamptz  NOT NULL,
        file_sha256     bytea        NOT NULL,
        schema_version  text         NOT NULL,
        summary         jsonb        NOT NULL,
        pending_manual  jsonb        NOT NULL DEFAULT '[]',
        CONSTRAINT pk_seed_loads PRIMARY KEY (id)
    )
    """,
    # §2.13 item_version_stats ----------------------------------------------------------------
    """
    CREATE TABLE content.item_version_stats (
        version_id       uuid          NOT NULL,
        first_responses  integer       NOT NULL,
        correct_rate     numeric(5,4),
        option_rates     jsonb,
        discrimination   numeric(5,4),
        signals          text[]        NOT NULL DEFAULT '{}',
        computed_at      timestamptz   NOT NULL,
        CONSTRAINT pk_item_version_stats PRIMARY KEY (version_id),
        CONSTRAINT fk_item_version_stats_version FOREIGN KEY (version_id)
            REFERENCES content.item_versions (id) ON DELETE RESTRICT,
        CONSTRAINT ck_item_version_stats_first_responses CHECK (first_responses >= 0),
        CONSTRAINT ck_item_version_stats_correct_rate CHECK (correct_rate BETWEEN 0 AND 1),
        CONSTRAINT ck_item_version_stats_discrimination CHECK (discrimination BETWEEN -1 AND 1)
    )
    """,
    "CREATE INDEX ix_item_version_stats_signals ON content.item_version_stats USING gin (signals)",
]

DOWNGRADE = ["DROP SCHEMA content CASCADE"]


def upgrade() -> None:
    for statement in UPGRADE:
        op.execute(statement)


def downgrade() -> None:
    for statement in DOWNGRADE:
        op.execute(statement)
