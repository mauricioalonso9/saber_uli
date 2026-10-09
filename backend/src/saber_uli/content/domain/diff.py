"""Diferencias campo por campo entre dos contenidos de ítem (FR-018; US5).

Los nombres de campo son los del contrato (`stem_md`, `options[B].feedback`,
`taxonomy.assertion_id`…). Se usan en la historia (`changed_fields`), en `getItemVersion` y en la
vista previa de una importación que actualiza ítems.
"""

from dataclasses import dataclass, fields
from typing import Any

from saber_uli.content.domain.item_version import ItemContent, Option

_SCALARS = (
    "difficulty",
    "stem_md",
    "explanation_md",
    "answer_key",
    "prompt_context_md",
    "rubric_id",
    "context_code",
)


@dataclass(frozen=True)
class FieldChange:
    field: str
    before: Any
    after: Any


def _plain(value: Any) -> Any:
    if value is None or isinstance(value, bool | int | float | str):
        return value
    if hasattr(value, "value"):
        return value.value
    return str(value)


def _options(content: ItemContent) -> dict[str, Option]:
    return {option.key: option for option in content.options or ()}


def diff_content(before: ItemContent | None, after: ItemContent) -> list[FieldChange]:
    """Cambios de `before` a `after`; vacío si `before` es None (primera versión)."""
    if before is None:
        return []
    changes: list[FieldChange] = []
    for name in _SCALARS:
        old, new = getattr(before, name), getattr(after, name)
        if old != new:
            changes.append(FieldChange(name, _plain(old), _plain(new)))
    for tag in fields(before.taxonomy):
        old, new = getattr(before.taxonomy, tag.name), getattr(after.taxonomy, tag.name)
        if old != new:
            changes.append(FieldChange(f"taxonomy.{tag.name}", _plain(old), _plain(new)))
    old_options, new_options = _options(before), _options(after)
    for key in sorted(old_options.keys() | new_options.keys()):
        old_option, new_option = old_options.get(key), new_options.get(key)
        if old_option is None or new_option is None:
            changes.append(
                FieldChange(
                    f"options[{key}]",
                    None if old_option is None else old_option.text,
                    None if new_option is None else new_option.text,
                )
            )
            continue
        for part in ("text", "correct", "feedback"):
            old, new = getattr(old_option, part), getattr(new_option, part)
            if old != new:
                changes.append(FieldChange(f"options[{key}].{part}", old, new))
    return changes
