"""Representaciones JSON del banco de ítems con la forma del contrato de 002.

Se arman como diccionarios (el contrato publicado es `specs/002-banco-items/contracts/openapi.yaml`
y Schemathesis verifica cada respuesta contra él).
"""

from typing import Any
from uuid import UUID

from saber_uli.content.application.contexts import ContextDetails
from saber_uli.content.application.queries.items import (
    ItemDetails,
    ItemHistory,
    ItemSummary,
    VersionDetails,
)
from saber_uli.content.domain.context import ContextContent
from saber_uli.content.domain.diff import FieldChange
from saber_uli.content.domain.events import HistoryEvent
from saber_uli.content.domain.item_version import ItemContent, ItemVersion
from saber_uli.content.domain.validation import ContentIssue

STEM_EXCERPT = 160


def user_ref(user_id: UUID | None, names: dict[UUID, str]) -> dict[str, Any] | None:
    if user_id is None:
        return None
    return {"id": str(user_id), "display_name": names.get(user_id, "Cuenta eliminada")}


def _iso(value: Any) -> str | None:
    return None if value is None else value.isoformat()


def item_content(content: ItemContent) -> dict[str, Any]:
    tags = content.taxonomy
    return {
        "difficulty": content.difficulty.value,
        "context_code": content.context_code,
        "taxonomy": {
            name: None if getattr(tags, name) is None else str(getattr(tags, name))
            for name in (
                "competence_id",
                "assertion_id",
                "evidence_id",
                "component_id",
                "situation_id",
                "part_id",
            )
        },
        "stem_md": content.stem_md,
        "options": None
        if content.options is None
        else [
            {"key": o.key, "text": o.text, "correct": o.correct, "feedback": o.feedback}
            for o in content.options
        ],
        "answer_key": content.answer_key,
        "explanation_md": content.explanation_md,
        "prompt_context_md": content.prompt_context_md,
        "rubric_id": None if content.rubric_id is None else str(content.rubric_id),
    }


def issues(found: list[ContentIssue]) -> list[dict[str, str]]:
    return [{"field": i.field, "rule": i.rule.value, "message": i.message} for i in found]


def item_version(
    version: ItemVersion,
    *,
    names: dict[UUID, str],
    context_numbers: dict[UUID, int],
    found: list[ContentIssue],
) -> dict[str, Any]:
    return {
        "number": version.number,
        "state": version.state.value,
        "content": item_content(version.content),
        "context_version": None
        if version.context_version_id is None
        else context_numbers.get(version.context_version_id),
        "content_issues": issues(found),
        "author": user_ref(version.author_id, names),
        "contributors": [
            user_ref(person, names) for person in sorted(version.contributor_ids, key=str)
        ],
        "reviewer": user_ref(version.reviewed_by, names),
        "created_at": _iso(version.created_at),
        "submitted_at": _iso(version.submitted_at),
        "published_at": _iso(version.published_at),
        "retired_at": _iso(version.retired_at),
        "retire_reason": version.retire_reason,
    }


def item(details: ItemDetails) -> dict[str, Any]:
    entity = details.item

    def version(value: ItemVersion | None, found: list[ContentIssue]) -> dict[str, Any] | None:
        if value is None:
            return None
        return item_version(
            value, names=details.names, context_numbers=details.context_numbers, found=found
        )

    return {
        "code": entity.code,
        "module": entity.module_code,
        "kind": entity.kind.value,
        "origin": entity.origin.value,
        "revision": entity.revision,
        "published": version(entity.published, []),
        "open": version(entity.open, details.open_issues),
        "last_review_comment": details.last_review_comment,
        "can": {**details.can, "approve_blocked_reason": details.approve_blocked_reason},
    }


def item_summary(summary: ItemSummary) -> dict[str, Any]:
    row = summary.row
    return {
        "code": row.code,
        "module": row.module,
        "kind": row.kind,
        "origin": row.origin,
        "difficulty": row.difficulty,
        "stem_excerpt": row.stem[:STEM_EXCERPT],
        "context_code": row.context_code,
        "assertion_code": row.assertion_code,
        "part_code": row.part_code,
        "published_version": row.published_version,
        "open_version": None
        if row.open_version is None
        else {"number": row.open_version, "state": row.open_state},
        "retired": row.published_version is None and row.open_version is None,
        "needs_another_reviewer": summary.needs_another_reviewer,
        "signals": list(row.signals),
        "updated_at": _iso(row.updated_at),
    }


def event(value: HistoryEvent, names: dict[UUID, str]) -> dict[str, Any]:
    return {
        "id": str(value.id),
        "type": value.type.value,
        "version": value.version_number,
        "actor": user_ref(value.actor_id, names),
        "occurred_at": _iso(value.occurred_at),
        "comment": value.comment,
        "reason": value.reason,
        "details": value.details,
    }


def history(value: ItemHistory) -> dict[str, Any]:
    return {
        "versions": [
            {
                "number": entry.version.number,
                "state": entry.version.state.value,
                "author": user_ref(entry.version.author_id, value.names),
                "reviewer": user_ref(entry.version.reviewed_by, value.names),
                "created_at": _iso(entry.version.created_at),
                "published_at": _iso(entry.version.published_at),
                "retired_at": _iso(entry.version.retired_at),
                "changed_fields": entry.changed_fields,
            }
            for entry in value.versions
        ],
        "events": [event(entry, value.names) for entry in value.events],
    }


def field_change(change: FieldChange) -> dict[str, Any]:
    return {"field": change.field, "before": change.before, "after": change.after}


def version_details(value: VersionDetails) -> dict[str, Any]:
    return {
        "version": item_version(
            value.version,
            names=value.names,
            context_numbers=value.context_numbers,
            found=value.issues,
        ),
        "changes": [field_change(change) for change in value.changes],
    }


def context_content(content: ContextContent) -> dict[str, Any]:
    return {
        "kind": content.kind.value,
        "title": content.title,
        "body_md": content.body_md,
        "media_id": None if content.media_id is None else str(content.media_id),
        "alt_text": content.alt_text,
        "text_type_node_id": None
        if content.text_type_node_id is None
        else str(content.text_type_node_id),
        "part_node_id": None if content.part_node_id is None else str(content.part_node_id),
        "subtype": content.subtype,
        "shared_options": None
        if content.shared_options is None
        else [
            {"key": o.key, "text": o.text, "feedback": o.feedback} for o in content.shared_options
        ],
    }


def context(details: ContextDetails) -> dict[str, Any]:
    value = details.context
    current = value.current
    return {
        "code": value.code,
        "module": value.module_code,
        "version": current.number,
        "word_count": current.word_count,
        "item_count": details.item_count,
        "published_item_count": details.published_item_count,
        **context_content(current.content),
        "origin": current.origin.value,
        "updated_at": _iso(current.created_at),
        "revision": value.revision,
        "items": [{"code": code, "state": state} for code, state in details.items],
    }
