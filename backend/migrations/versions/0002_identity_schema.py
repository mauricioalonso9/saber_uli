"""identity: tablas del contexto de identidad (data-model.md §2).

Las restricciones citan su sección de data-model.md. Los permisos por rol llegan en 0003
(T030) y la semilla de parámetros en 0004 (T056).

Revisión: 0002
Anterior: 0001
Creada: 2026-10-06
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0002"
down_revision: str | Sequence[str] | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UPGRADE = [
    "CREATE SCHEMA identity",
    # §2.5 programs ---------------------------------------------------------------------------
    """
    CREATE TABLE identity.programs (
        id          uuid        NOT NULL DEFAULT uuidv7(),
        code        text        NOT NULL,
        name        text        NOT NULL,
        campus      text        NOT NULL,
        active      boolean     NOT NULL DEFAULT true,
        created_at  timestamptz NOT NULL DEFAULT now(),
        updated_at  timestamptz NOT NULL DEFAULT now(),
        CONSTRAINT pk_programs PRIMARY KEY (id),
        CONSTRAINT uq_programs_code UNIQUE (code)
    )
    """,
    # §2.1 users ------------------------------------------------------------------------------
    """
    CREATE TABLE identity.users (
        id                        uuid        NOT NULL DEFAULT uuidv7(),
        kind                      text        NOT NULL,
        status                    text        NOT NULL DEFAULT 'active',
        entra_tenant_id           uuid,
        entra_object_id           uuid,
        email                     citext,
        display_name              text,
        auth_epoch                integer     NOT NULL DEFAULT 0,
        last_login_at             timestamptz,
        retention_notice_sent_at  timestamptz,
        onboarding_completed_at   timestamptz,
        created_at                timestamptz NOT NULL DEFAULT now(),
        updated_at                timestamptz NOT NULL DEFAULT now(),
        CONSTRAINT pk_users PRIMARY KEY (id),
        CONSTRAINT ck_users_kind CHECK (kind IN ('institutional', 'guest')),
        CONSTRAINT ck_users_status
            CHECK (status IN ('active', 'disabled', 'deletion_pending', 'deleted')),
        CONSTRAINT ck_users_auth_epoch_non_negative CHECK (auth_epoch >= 0),
        -- FR-005: una cuenta por persona institucional.
        CONSTRAINT uq_users_entra_identity UNIQUE (entra_tenant_id, entra_object_id),
        CONSTRAINT ck_users_institutional_identity CHECK (
            kind <> 'institutional' OR status = 'deleted'
            OR (entra_tenant_id IS NOT NULL AND entra_object_id IS NOT NULL)
        ),
        -- Solo los institucionales tienen identidad de Entra ID.
        CONSTRAINT ck_users_guest_without_entra_identity CHECK (
            kind <> 'guest' OR (entra_tenant_id IS NULL AND entra_object_id IS NULL)
        ),
        -- FR-033: una lápida no contiene datos personales.
        CONSTRAINT ck_users_tombstone_without_personal_data CHECK (
            status <> 'deleted'
            OR (email IS NULL AND display_name IS NULL AND entra_object_id IS NULL)
        )
    )
    """,
    """
    CREATE UNIQUE INDEX ux_users_active_guest_email
        ON identity.users (lower(email))
        WHERE kind = 'guest' AND status <> 'deleted'
    """,
    """
    CREATE INDEX ix_users_retention
        ON identity.users (kind, last_login_at)
        WHERE status = 'active'
    """,
    # §2.2 profiles ---------------------------------------------------------------------------
    """
    CREATE TABLE identity.profiles (
        user_id             uuid        NOT NULL,
        program_id          uuid,
        semester            smallint,
        expected_exam_date  date,
        daily_goal          text,
        guest_display_name  text,
        updated_at          timestamptz NOT NULL DEFAULT now(),
        CONSTRAINT pk_profiles PRIMARY KEY (user_id),
        CONSTRAINT fk_profiles_user_id_users
            FOREIGN KEY (user_id) REFERENCES identity.users (id) ON DELETE CASCADE,
        CONSTRAINT fk_profiles_program_id_programs
            FOREIGN KEY (program_id) REFERENCES identity.programs (id),
        CONSTRAINT ck_profiles_semester CHECK (semester BETWEEN 1 AND 12),
        CONSTRAINT ck_profiles_daily_goal CHECK (daily_goal IN ('casual', 'regular', 'intense'))
    )
    """,
    # §2.3 role_assignments -------------------------------------------------------------------
    """
    CREATE TABLE identity.role_assignments (
        user_id      uuid        NOT NULL,
        role         text        NOT NULL,
        assigned_by  uuid,
        assigned_at  timestamptz NOT NULL DEFAULT now(),
        CONSTRAINT pk_role_assignments PRIMARY KEY (user_id, role),
        CONSTRAINT fk_role_assignments_user_id_users
            FOREIGN KEY (user_id) REFERENCES identity.users (id) ON DELETE CASCADE,
        CONSTRAINT fk_role_assignments_assigned_by_users
            FOREIGN KEY (assigned_by) REFERENCES identity.users (id),
        CONSTRAINT ck_role_assignments_role
            CHECK (role IN ('student', 'guest', 'teacher', 'program_director', 'admin'))
    )
    """,
    # Bloqueo de administradores activos (FR-025) y búsquedas por rol.
    "CREATE INDEX ix_role_assignments_role ON identity.role_assignments (role, user_id)",
    # §2.4 director_programs ------------------------------------------------------------------
    """
    CREATE TABLE identity.director_programs (
        user_id     uuid NOT NULL,
        program_id  uuid NOT NULL,
        CONSTRAINT pk_director_programs PRIMARY KEY (user_id, program_id),
        CONSTRAINT fk_director_programs_user_id_users
            FOREIGN KEY (user_id) REFERENCES identity.users (id) ON DELETE CASCADE,
        CONSTRAINT fk_director_programs_program_id_programs
            FOREIGN KEY (program_id) REFERENCES identity.programs (id)
    )
    """,
    # §2.6 groups, group_members, group_teachers ----------------------------------------------
    """
    CREATE TABLE identity.groups (
        id            uuid        NOT NULL DEFAULT uuidv7(),
        name          text        NOT NULL,
        description   text,
        cohort_label  text,
        program_id    uuid,
        created_by    uuid        NOT NULL,
        created_at    timestamptz NOT NULL DEFAULT now(),
        archived_at   timestamptz,
        CONSTRAINT pk_groups PRIMARY KEY (id),
        CONSTRAINT fk_groups_program_id_programs
            FOREIGN KEY (program_id) REFERENCES identity.programs (id),
        CONSTRAINT fk_groups_created_by_users
            FOREIGN KEY (created_by) REFERENCES identity.users (id)
    )
    """,
    """
    CREATE TABLE identity.group_members (
        group_id  uuid        NOT NULL,
        user_id   uuid        NOT NULL,
        added_at  timestamptz NOT NULL DEFAULT now(),
        CONSTRAINT pk_group_members PRIMARY KEY (group_id, user_id),
        CONSTRAINT fk_group_members_group_id_groups
            FOREIGN KEY (group_id) REFERENCES identity.groups (id) ON DELETE CASCADE,
        CONSTRAINT fk_group_members_user_id_users
            FOREIGN KEY (user_id) REFERENCES identity.users (id) ON DELETE CASCADE
    )
    """,
    "CREATE INDEX ix_group_members_user_id ON identity.group_members (user_id)",
    """
    CREATE TABLE identity.group_teachers (
        group_id  uuid        NOT NULL,
        user_id   uuid        NOT NULL,
        added_at  timestamptz NOT NULL DEFAULT now(),
        CONSTRAINT pk_group_teachers PRIMARY KEY (group_id, user_id),
        CONSTRAINT fk_group_teachers_group_id_groups
            FOREIGN KEY (group_id) REFERENCES identity.groups (id) ON DELETE CASCADE,
        CONSTRAINT fk_group_teachers_user_id_users
            FOREIGN KEY (user_id) REFERENCES identity.users (id) ON DELETE CASCADE
    )
    """,
    "CREATE INDEX ix_group_teachers_user_id ON identity.group_teachers (user_id)",
    # §2.9 invitation_batches -----------------------------------------------------------------
    """
    CREATE TABLE identity.invitation_batches (
        id             uuid        NOT NULL DEFAULT uuidv7(),
        created_by     uuid        NOT NULL,
        status         text        NOT NULL DEFAULT 'pending_confirmation',
        rows           jsonb       NOT NULL DEFAULT '[]',
        valid_count    integer     NOT NULL DEFAULT 0,
        invalid_count  integer     NOT NULL DEFAULT 0,
        expires_at     timestamptz NOT NULL,
        created_at     timestamptz NOT NULL DEFAULT now(),
        confirmed_at   timestamptz,
        CONSTRAINT pk_invitation_batches PRIMARY KEY (id),
        CONSTRAINT fk_invitation_batches_created_by_users
            FOREIGN KEY (created_by) REFERENCES identity.users (id),
        CONSTRAINT ck_invitation_batches_status
            CHECK (status IN ('pending_confirmation', 'confirmed', 'expired')),
        CONSTRAINT ck_invitation_batches_rows_array CHECK (jsonb_typeof(rows) = 'array'),
        CONSTRAINT ck_invitation_batches_counts_non_negative
            CHECK (valid_count >= 0 AND invalid_count >= 0)
    )
    """,
    # §2.7 invitations ------------------------------------------------------------------------
    """
    CREATE TABLE identity.invitations (
        id                    uuid        NOT NULL DEFAULT uuidv7(),
        email                 citext,
        invitee_name          text,
        invited_by            uuid        NOT NULL,
        batch_id              uuid,
        guest_user_id         uuid,
        status                text        NOT NULL DEFAULT 'sent',
        access_expires_at     timestamptz NOT NULL,
        link_expires_at       timestamptz,
        sent_at               timestamptz,
        accepted_at           timestamptz,
        revoked_at            timestamptz,
        last_delivery_status  text,
        created_at            timestamptz NOT NULL DEFAULT now(),
        updated_at            timestamptz NOT NULL DEFAULT now(),
        CONSTRAINT pk_invitations PRIMARY KEY (id),
        CONSTRAINT fk_invitations_invited_by_users
            FOREIGN KEY (invited_by) REFERENCES identity.users (id),
        -- Los lotes se purgan a los 30 días (§2.9); la invitación se conserva.
        CONSTRAINT fk_invitations_batch_id_invitation_batches
            FOREIGN KEY (batch_id) REFERENCES identity.invitation_batches (id) ON DELETE SET NULL,
        CONSTRAINT fk_invitations_guest_user_id_users
            FOREIGN KEY (guest_user_id) REFERENCES identity.users (id),
        CONSTRAINT ck_invitations_status
            CHECK (status IN ('sent', 'accepted', 'expired', 'revoked')),
        CONSTRAINT ck_invitations_last_delivery_status
            CHECK (last_delivery_status IN ('queued', 'sent', 'failed')),
        CONSTRAINT ck_invitations_access_after_creation CHECK (access_expires_at > created_at)
    )
    """,
    # Caso límite de duplicados: no hay dos invitaciones vigentes al mismo correo.
    """
    CREATE UNIQUE INDEX ux_invitations_active_email
        ON identity.invitations (lower(email))
        WHERE status IN ('sent', 'accepted')
    """,
    """
    CREATE INDEX ix_invitations_invited_by
        ON identity.invitations (invited_by, created_at DESC)
    """,
    "CREATE INDEX ix_invitations_status_access ON identity.invitations (status, access_expires_at)",
    # §2.8 access_links (R-19: solo el SHA-256 del token) ------------------------------------
    """
    CREATE TABLE identity.access_links (
        id             uuid        NOT NULL DEFAULT uuidv7(),
        invitation_id  uuid        NOT NULL,
        purpose        text        NOT NULL,
        token_hash     bytea       NOT NULL,
        expires_at     timestamptz NOT NULL,
        used_at        timestamptz,
        created_at     timestamptz NOT NULL DEFAULT now(),
        CONSTRAINT pk_access_links PRIMARY KEY (id),
        CONSTRAINT fk_access_links_invitation_id_invitations
            FOREIGN KEY (invitation_id) REFERENCES identity.invitations (id) ON DELETE CASCADE,
        CONSTRAINT uq_access_links_token_hash UNIQUE (token_hash),
        CONSTRAINT ck_access_links_purpose CHECK (purpose IN ('invitation', 'sign_in')),
        CONSTRAINT ck_access_links_token_hash_sha256 CHECK (octet_length(token_hash) = 32)
    )
    """,
    """
    CREATE INDEX ix_access_links_unused
        ON identity.access_links (invitation_id, purpose)
        WHERE used_at IS NULL
    """,
    # §2.10 policy_versions -------------------------------------------------------------------
    """
    CREATE TABLE identity.policy_versions (
        id              uuid        NOT NULL DEFAULT uuidv7(),
        version         text        NOT NULL,
        title           text        NOT NULL,
        body_markdown   text        NOT NULL,
        effective_from  timestamptz NOT NULL,
        published_by    uuid,
        created_at      timestamptz NOT NULL DEFAULT now(),
        CONSTRAINT pk_policy_versions PRIMARY KEY (id),
        CONSTRAINT uq_policy_versions_version UNIQUE (version),
        CONSTRAINT fk_policy_versions_published_by_users
            FOREIGN KEY (published_by) REFERENCES identity.users (id)
    )
    """,
    """
    CREATE INDEX ix_policy_versions_effective_from
        ON identity.policy_versions (effective_from DESC)
    """,
    # §2.11 consents (solo inserción; permisos en 0003) ---------------------------------------
    """
    CREATE TABLE identity.consents (
        id                 uuid        NOT NULL DEFAULT uuidv7(),
        user_id            uuid        NOT NULL,
        policy_version_id  uuid        NOT NULL,
        decision           text        NOT NULL,
        channel            text        NOT NULL,
        decided_at         timestamptz NOT NULL DEFAULT now(),
        CONSTRAINT pk_consents PRIMARY KEY (id),
        CONSTRAINT fk_consents_user_id_users
            FOREIGN KEY (user_id) REFERENCES identity.users (id),
        CONSTRAINT fk_consents_policy_version_id_policy_versions
            FOREIGN KEY (policy_version_id) REFERENCES identity.policy_versions (id),
        CONSTRAINT ck_consents_decision CHECK (decision IN ('accepted', 'rejected', 'revoked'))
    )
    """,
    "CREATE INDEX ix_consents_user_decided ON identity.consents (user_id, decided_at DESC)",
    # §2.12 deletion_requests -----------------------------------------------------------------
    """
    CREATE TABLE identity.deletion_requests (
        id            uuid        NOT NULL DEFAULT uuidv7(),
        user_id       uuid        NOT NULL,
        origin        text        NOT NULL,
        status        text        NOT NULL DEFAULT 'received',
        requested_at  timestamptz NOT NULL DEFAULT now(),
        due_date      date        NOT NULL,
        completed_at  timestamptz,
        CONSTRAINT pk_deletion_requests PRIMARY KEY (id),
        CONSTRAINT fk_deletion_requests_user_id_users
            FOREIGN KEY (user_id) REFERENCES identity.users (id),
        CONSTRAINT ck_deletion_requests_origin
            CHECK (origin IN ('user_request', 'guest_retention', 'institutional_retention')),
        CONSTRAINT ck_deletion_requests_status
            CHECK (status IN ('received', 'in_progress', 'completed'))
    )
    """,
    """
    CREATE UNIQUE INDEX ux_deletion_requests_open
        ON identity.deletion_requests (user_id)
        WHERE status <> 'completed'
    """,
    # §2.13 sessions y refresh_tokens (R-14, R-15) --------------------------------------------
    """
    CREATE TABLE identity.sessions (
        id                           uuid        NOT NULL DEFAULT uuidv7(),
        user_id                      uuid        NOT NULL,
        auth_method                  text        NOT NULL,
        auth_time                    timestamptz NOT NULL,
        last_seen_at                 timestamptz NOT NULL,
        last_privileged_activity_at  timestamptz,
        absolute_expires_at          timestamptz NOT NULL,
        revoked_at                   timestamptz,
        revoked_reason               text,
        created_at                   timestamptz NOT NULL DEFAULT now(),
        CONSTRAINT pk_sessions PRIMARY KEY (id),
        CONSTRAINT fk_sessions_user_id_users
            FOREIGN KEY (user_id) REFERENCES identity.users (id) ON DELETE CASCADE,
        CONSTRAINT ck_sessions_auth_method CHECK (auth_method IN ('entra_id', 'guest_link'))
    )
    """,
    """
    CREATE INDEX ix_sessions_user_active
        ON identity.sessions (user_id)
        WHERE revoked_at IS NULL
    """,
    """
    CREATE TABLE identity.refresh_tokens (
        id               uuid        NOT NULL DEFAULT uuidv7(),
        session_id       uuid        NOT NULL,
        token_hash       bytea       NOT NULL,
        issued_at        timestamptz NOT NULL DEFAULT now(),
        idle_expires_at  timestamptz NOT NULL,
        rotated_at       timestamptz,
        CONSTRAINT pk_refresh_tokens PRIMARY KEY (id),
        CONSTRAINT fk_refresh_tokens_session_id_sessions
            FOREIGN KEY (session_id) REFERENCES identity.sessions (id) ON DELETE CASCADE,
        CONSTRAINT uq_refresh_tokens_token_hash UNIQUE (token_hash),
        CONSTRAINT ck_refresh_tokens_token_hash_sha256 CHECK (octet_length(token_hash) = 32)
    )
    """,
    "CREATE INDEX ix_refresh_tokens_session_id ON identity.refresh_tokens (session_id)",
    # §2.14 audit_events (solo inserción; sin FK para que la supresión no la toque) -----------
    """
    CREATE TABLE identity.audit_events (
        id               uuid        NOT NULL DEFAULT uuidv7(),
        occurred_at      timestamptz NOT NULL DEFAULT now(),
        actor_id         uuid,
        action           text        NOT NULL,
        target_type      text        NOT NULL,
        target_id        uuid,
        subject_user_id  uuid,
        details          jsonb       NOT NULL DEFAULT '{}',
        CONSTRAINT pk_audit_events PRIMARY KEY (id),
        CONSTRAINT ck_audit_events_action_format CHECK (action ~ '^[a-z_]+\\.[a-z_]+$'),
        CONSTRAINT ck_audit_events_target_type CHECK (
            target_type IN ('user', 'invitation', 'group', 'program', 'policy', 'setting',
                            'deletion_request', 'session')
        ),
        CONSTRAINT ck_audit_events_details_object CHECK (jsonb_typeof(details) = 'object')
    )
    """,
    "CREATE INDEX ix_audit_events_occurred_at ON identity.audit_events (occurred_at DESC)",
    """
    CREATE INDEX ix_audit_events_subject
        ON identity.audit_events (subject_user_id, occurred_at DESC)
    """,
    "CREATE INDEX ix_audit_events_actor ON identity.audit_events (actor_id, occurred_at DESC)",
    # §2.15 settings (semilla en 0004, T056) --------------------------------------------------
    """
    CREATE TABLE identity.settings (
        key         text        NOT NULL,
        value       jsonb       NOT NULL,
        updated_by  uuid,
        updated_at  timestamptz NOT NULL DEFAULT now(),
        CONSTRAINT pk_settings PRIMARY KEY (key),
        CONSTRAINT fk_settings_updated_by_users
            FOREIGN KEY (updated_by) REFERENCES identity.users (id)
    )
    """,
]


def upgrade() -> None:
    for statement in UPGRADE:
        op.execute(statement)


def downgrade() -> None:
    op.execute("DROP SCHEMA identity CASCADE")
