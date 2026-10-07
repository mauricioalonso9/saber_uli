"""Mapeos SQLAlchemy del esquema `identity` (data-model.md §2).

Reflejan exactamente las migraciones 0002 y 0003: una prueba (T043) compara este modelo con el
esquema migrado. Son filas de persistencia, no el dominio: los repositorios traducen entre estas
clases y los agregados de `identity.domain`. Los `CHECK` viven en la migración y no se repiten
aquí (Alembic no los compara).
"""

from datetime import date, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    PrimaryKeyConstraint,
    SmallInteger,
    Text,
    UniqueConstraint,
    Uuid,
    text,
)
from sqlalchemy.dialects.postgresql import CITEXT, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from saber_uli.shared.infrastructure.db import Base

SCHEMA = "identity"
_UUIDV7 = text("uuidv7()")
_NOW = text("now()")


def _fk(target: str, **kwargs: Any) -> ForeignKey:
    return ForeignKey(f"{SCHEMA}.{target}", **kwargs)


def _pk() -> Mapped[UUID]:
    return mapped_column(Uuid, primary_key=True, server_default=_UUIDV7)


def _ts(*, nullable: bool = False, default_now: bool = False) -> Any:
    return mapped_column(
        DateTime(timezone=True), nullable=nullable, server_default=_NOW if default_now else None
    )


# §2.5 ---------------------------------------------------------------------------------------
class ProgramRow(Base):
    __tablename__ = "programs"
    __table_args__ = (UniqueConstraint("code", name="uq_programs_code"), {"schema": SCHEMA})

    id: Mapped[UUID] = _pk()
    code: Mapped[str] = mapped_column(Text)
    name: Mapped[str] = mapped_column(Text)
    campus: Mapped[str] = mapped_column(Text)
    active: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))
    created_at: Mapped[datetime] = _ts(default_now=True)
    updated_at: Mapped[datetime] = _ts(default_now=True)


# §2.1 y §2.3 ----------------------------------------------------------------------------------
class UserRow(Base):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("entra_tenant_id", "entra_object_id", name="uq_users_entra_identity"),
        Index(
            "ux_users_active_guest_email",
            text("lower(email)"),
            unique=True,
            postgresql_where=text("kind = 'guest' AND status <> 'deleted'"),
        ),
        Index(
            "ix_users_retention",
            "kind",
            "last_login_at",
            postgresql_where=text("status = 'active'"),
        ),
        {"schema": SCHEMA},
    )

    id: Mapped[UUID] = _pk()
    kind: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, server_default=text("'active'"))
    entra_tenant_id: Mapped[UUID | None] = mapped_column(Uuid)
    entra_object_id: Mapped[UUID | None] = mapped_column(Uuid)
    email: Mapped[str | None] = mapped_column(CITEXT)
    display_name: Mapped[str | None] = mapped_column(Text)
    auth_epoch: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    last_login_at: Mapped[datetime | None] = _ts(nullable=True)
    retention_notice_sent_at: Mapped[datetime | None] = _ts(nullable=True)
    onboarding_completed_at: Mapped[datetime | None] = _ts(nullable=True)
    created_at: Mapped[datetime] = _ts(default_now=True)
    updated_at: Mapped[datetime] = _ts(default_now=True)

    role_assignments: Mapped[list["RoleAssignmentRow"]] = relationship(
        cascade="all, delete-orphan",
        lazy="selectin",
        foreign_keys="RoleAssignmentRow.user_id",
    )


class RoleAssignmentRow(Base):
    __tablename__ = "role_assignments"
    __table_args__ = (
        PrimaryKeyConstraint("user_id", "role", name="pk_role_assignments"),
        Index("ix_role_assignments_role", "role", "user_id"),
        {"schema": SCHEMA},
    )

    user_id: Mapped[UUID] = mapped_column(Uuid, _fk("users.id", ondelete="CASCADE"))
    role: Mapped[str] = mapped_column(Text)
    assigned_by: Mapped[UUID | None] = mapped_column(Uuid, _fk("users.id"))
    assigned_at: Mapped[datetime] = _ts(default_now=True)


# §2.2 ---------------------------------------------------------------------------------------
class ProfileRow(Base):
    __tablename__ = "profiles"
    __table_args__ = ({"schema": SCHEMA},)

    user_id: Mapped[UUID] = mapped_column(
        Uuid, _fk("users.id", ondelete="CASCADE"), primary_key=True
    )
    program_id: Mapped[UUID | None] = mapped_column(Uuid, _fk("programs.id"))
    semester: Mapped[int | None] = mapped_column(SmallInteger)
    expected_exam_date: Mapped[date | None] = mapped_column(Date)
    daily_goal: Mapped[str | None] = mapped_column(Text)
    guest_display_name: Mapped[str | None] = mapped_column(Text)
    updated_at: Mapped[datetime] = _ts(default_now=True)


# §2.4 ---------------------------------------------------------------------------------------
class DirectorProgramRow(Base):
    __tablename__ = "director_programs"
    __table_args__ = (
        PrimaryKeyConstraint("user_id", "program_id", name="pk_director_programs"),
        {"schema": SCHEMA},
    )

    user_id: Mapped[UUID] = mapped_column(Uuid, _fk("users.id", ondelete="CASCADE"))
    program_id: Mapped[UUID] = mapped_column(Uuid, _fk("programs.id"))


# §2.6 ---------------------------------------------------------------------------------------
class GroupRow(Base):
    __tablename__ = "groups"
    __table_args__ = ({"schema": SCHEMA},)

    id: Mapped[UUID] = _pk()
    name: Mapped[str] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    cohort_label: Mapped[str | None] = mapped_column(Text)
    program_id: Mapped[UUID | None] = mapped_column(Uuid, _fk("programs.id"))
    created_by: Mapped[UUID] = mapped_column(Uuid, _fk("users.id"))
    created_at: Mapped[datetime] = _ts(default_now=True)
    archived_at: Mapped[datetime | None] = _ts(nullable=True)


class GroupMemberRow(Base):
    __tablename__ = "group_members"
    __table_args__ = (
        PrimaryKeyConstraint("group_id", "user_id", name="pk_group_members"),
        Index("ix_group_members_user_id", "user_id"),
        {"schema": SCHEMA},
    )

    group_id: Mapped[UUID] = mapped_column(Uuid, _fk("groups.id", ondelete="CASCADE"))
    user_id: Mapped[UUID] = mapped_column(Uuid, _fk("users.id", ondelete="CASCADE"))
    added_at: Mapped[datetime] = _ts(default_now=True)


class GroupTeacherRow(Base):
    __tablename__ = "group_teachers"
    __table_args__ = (
        PrimaryKeyConstraint("group_id", "user_id", name="pk_group_teachers"),
        Index("ix_group_teachers_user_id", "user_id"),
        {"schema": SCHEMA},
    )

    group_id: Mapped[UUID] = mapped_column(Uuid, _fk("groups.id", ondelete="CASCADE"))
    user_id: Mapped[UUID] = mapped_column(Uuid, _fk("users.id", ondelete="CASCADE"))
    added_at: Mapped[datetime] = _ts(default_now=True)


# §2.9 ---------------------------------------------------------------------------------------
class InvitationBatchRow(Base):
    __tablename__ = "invitation_batches"
    __table_args__ = ({"schema": SCHEMA},)

    id: Mapped[UUID] = _pk()
    created_by: Mapped[UUID] = mapped_column(Uuid, _fk("users.id"))
    status: Mapped[str] = mapped_column(Text, server_default=text("'pending_confirmation'"))
    rows: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, server_default=text("'[]'"))
    valid_count: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    invalid_count: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    expires_at: Mapped[datetime] = _ts()
    created_at: Mapped[datetime] = _ts(default_now=True)
    confirmed_at: Mapped[datetime | None] = _ts(nullable=True)


# §2.7 ---------------------------------------------------------------------------------------
class InvitationRow(Base):
    __tablename__ = "invitations"
    __table_args__ = (
        Index(
            "ux_invitations_active_email",
            text("lower(email)"),
            unique=True,
            postgresql_where=text("status IN ('sent', 'accepted')"),
        ),
        Index("ix_invitations_invited_by", "invited_by", text("created_at DESC")),
        Index("ix_invitations_status_access", "status", "access_expires_at"),
        {"schema": SCHEMA},
    )

    id: Mapped[UUID] = _pk()
    email: Mapped[str | None] = mapped_column(CITEXT)
    invitee_name: Mapped[str | None] = mapped_column(Text)
    invited_by: Mapped[UUID | None] = mapped_column(Uuid, _fk("users.id"))  # NULL = sistema
    batch_id: Mapped[UUID | None] = mapped_column(
        Uuid, _fk("invitation_batches.id", ondelete="SET NULL")
    )
    guest_user_id: Mapped[UUID | None] = mapped_column(Uuid, _fk("users.id"))
    status: Mapped[str] = mapped_column(Text, server_default=text("'sent'"))
    access_expires_at: Mapped[datetime] = _ts()
    link_expires_at: Mapped[datetime | None] = _ts(nullable=True)
    sent_at: Mapped[datetime | None] = _ts(nullable=True)
    accepted_at: Mapped[datetime | None] = _ts(nullable=True)
    revoked_at: Mapped[datetime | None] = _ts(nullable=True)
    last_delivery_status: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = _ts(default_now=True)
    updated_at: Mapped[datetime] = _ts(default_now=True)


# §2.8 ---------------------------------------------------------------------------------------
class AccessLinkRow(Base):
    __tablename__ = "access_links"
    __table_args__ = (
        UniqueConstraint("token_hash", name="uq_access_links_token_hash"),
        Index(
            "ix_access_links_unused",
            "invitation_id",
            "purpose",
            postgresql_where=text("used_at IS NULL"),
        ),
        {"schema": SCHEMA},
    )

    id: Mapped[UUID] = _pk()
    invitation_id: Mapped[UUID] = mapped_column(Uuid, _fk("invitations.id", ondelete="CASCADE"))
    purpose: Mapped[str] = mapped_column(Text)
    token_hash: Mapped[bytes] = mapped_column(LargeBinary)
    expires_at: Mapped[datetime] = _ts()
    used_at: Mapped[datetime | None] = _ts(nullable=True)
    created_at: Mapped[datetime] = _ts(default_now=True)


# §2.10 --------------------------------------------------------------------------------------
class PolicyVersionRow(Base):
    __tablename__ = "policy_versions"
    __table_args__ = (
        UniqueConstraint("version", name="uq_policy_versions_version"),
        Index("ix_policy_versions_effective_from", text("effective_from DESC")),
        {"schema": SCHEMA},
    )

    id: Mapped[UUID] = _pk()
    version: Mapped[str] = mapped_column(Text)
    title: Mapped[str] = mapped_column(Text)
    body_markdown: Mapped[str] = mapped_column(Text)
    effective_from: Mapped[datetime] = _ts()
    published_by: Mapped[UUID | None] = mapped_column(Uuid, _fk("users.id"))
    created_at: Mapped[datetime] = _ts(default_now=True)


# §2.11 --------------------------------------------------------------------------------------
class ConsentRow(Base):
    __tablename__ = "consents"
    __table_args__ = (
        Index("ix_consents_user_decided", "user_id", text("decided_at DESC")),
        {"schema": SCHEMA},
    )

    id: Mapped[UUID] = _pk()
    user_id: Mapped[UUID] = mapped_column(Uuid, _fk("users.id"))
    policy_version_id: Mapped[UUID] = mapped_column(Uuid, _fk("policy_versions.id"))
    decision: Mapped[str] = mapped_column(Text)
    channel: Mapped[str] = mapped_column(Text)
    decided_at: Mapped[datetime] = _ts(default_now=True)


# §2.12 --------------------------------------------------------------------------------------
class DeletionRequestRow(Base):
    __tablename__ = "deletion_requests"
    __table_args__ = (
        Index(
            "ux_deletion_requests_open",
            "user_id",
            unique=True,
            postgresql_where=text("status <> 'completed'"),
        ),
        {"schema": SCHEMA},
    )

    id: Mapped[UUID] = _pk()
    user_id: Mapped[UUID] = mapped_column(Uuid, _fk("users.id"))
    origin: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, server_default=text("'received'"))
    requested_at: Mapped[datetime] = _ts(default_now=True)
    due_date: Mapped[date] = mapped_column(Date)
    completed_at: Mapped[datetime | None] = _ts(nullable=True)


# §2.13 --------------------------------------------------------------------------------------
class SessionRow(Base):
    __tablename__ = "sessions"
    __table_args__ = (
        Index("ix_sessions_user_active", "user_id", postgresql_where=text("revoked_at IS NULL")),
        {"schema": SCHEMA},
    )

    id: Mapped[UUID] = _pk()
    user_id: Mapped[UUID] = mapped_column(Uuid, _fk("users.id", ondelete="CASCADE"))
    auth_method: Mapped[str] = mapped_column(Text)
    auth_time: Mapped[datetime] = _ts()
    last_seen_at: Mapped[datetime] = _ts()
    last_privileged_activity_at: Mapped[datetime | None] = _ts(nullable=True)
    absolute_expires_at: Mapped[datetime] = _ts()
    revoked_at: Mapped[datetime | None] = _ts(nullable=True)
    revoked_reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = _ts(default_now=True)


class RefreshTokenRow(Base):
    __tablename__ = "refresh_tokens"
    __table_args__ = (
        UniqueConstraint("token_hash", name="uq_refresh_tokens_token_hash"),
        Index("ix_refresh_tokens_session_id", "session_id"),
        {"schema": SCHEMA},
    )

    id: Mapped[UUID] = _pk()
    session_id: Mapped[UUID] = mapped_column(Uuid, _fk("sessions.id", ondelete="CASCADE"))
    token_hash: Mapped[bytes] = mapped_column(LargeBinary)
    issued_at: Mapped[datetime] = _ts(default_now=True)
    idle_expires_at: Mapped[datetime] = _ts()
    rotated_at: Mapped[datetime | None] = _ts(nullable=True)


# §2.14 --------------------------------------------------------------------------------------
class AuditEventRow(Base):
    __tablename__ = "audit_events"
    __table_args__ = (
        Index("ix_audit_events_occurred_at", text("occurred_at DESC")),
        Index("ix_audit_events_subject", "subject_user_id", text("occurred_at DESC")),
        Index("ix_audit_events_actor", "actor_id", text("occurred_at DESC")),
        {"schema": SCHEMA},
    )

    id: Mapped[UUID] = _pk()
    occurred_at: Mapped[datetime] = _ts(default_now=True)
    actor_id: Mapped[UUID | None] = mapped_column(Uuid)
    action: Mapped[str] = mapped_column(Text)
    target_type: Mapped[str] = mapped_column(Text)
    target_id: Mapped[UUID | None] = mapped_column(Uuid)
    subject_user_id: Mapped[UUID | None] = mapped_column(Uuid)
    details: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default=text("'{}'"))


# §2.15 --------------------------------------------------------------------------------------
class SettingRow(Base):
    __tablename__ = "settings"
    __table_args__ = ({"schema": SCHEMA},)

    key: Mapped[str] = mapped_column(Text, primary_key=True)
    value: Mapped[Any] = mapped_column(JSONB)
    updated_by: Mapped[UUID | None] = mapped_column(Uuid, _fk("users.id"))
    updated_at: Mapped[datetime] = _ts(default_now=True)
