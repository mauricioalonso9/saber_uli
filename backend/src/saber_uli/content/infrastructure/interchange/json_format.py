"""Lector y escritor JSON del formato de intercambio v1 (research R-03).

El lector valida primero el sobre (JSON, `esquema_version: "1.0"`, listas) y después cada entrada
por separado: un error de forma en un ítem queda como `EntryError` de ese ítem y el resto del
archivo se lee; un sobre ilegible lanza `UnreadableFileError`.
"""

import json
from collections.abc import Callable
from functools import partial
from typing import Any

from pydantic import BaseModel, ValidationError

from saber_uli.content.application.bundle import (
    Bundle,
    EntryError,
    EntryKind,
    ModuleSpec,
    UnreadableFileError,
)
from saber_uli.content.domain.validation import ContentIssue, ValidationRule
from saber_uli.content.infrastructure.interchange import mapping
from saber_uli.content.infrastructure.interchange import models as m

__all__ = ["UnreadableFileError", "read_bundle", "write_bundle"]

SCHEMA_VERSION = "1.0"
_LISTS = ("modulos", "contextos", "items", "consignas_escritura", "rubricas")
_METADATA = ("nombre", "descripcion", "fuente_taxonomia", "estructura_examen")


def issues_from(error: ValidationError) -> tuple[ContentIssue, ...]:
    issues = []
    for detail in error.errors():
        field = ".".join(str(part) for part in detail.get("loc", ())) or "entrada"
        missing = detail.get("type") == "missing"
        issues.append(
            ContentIssue(
                field,
                ValidationRule.REQUIRED if missing else ValidationRule.INVALID_VALUE,
                f"Falta «{field}»." if missing else f"El valor de «{field}» no es válido.",
            )
        )
    return tuple(issues)


def _decode(content: bytes) -> dict[str, Any]:
    try:
        data = json.loads(content.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise UnreadableFileError("El archivo no es un JSON en UTF-8.") from error
    if not isinstance(data, dict):
        raise UnreadableFileError("El archivo debe ser un objeto JSON con el banco.")
    if data.get("esquema_version") != SCHEMA_VERSION:
        raise UnreadableFileError(
            f'El archivo debe declarar "esquema_version": "{SCHEMA_VERSION}".'
        )
    for key in _LISTS:
        if not isinstance(data.get(key, []), list):
            raise UnreadableFileError(f"«{key}» debe ser una lista.")
    unknown = set(data) - {"esquema_version", *_LISTS, *_METADATA}
    if unknown:
        raise UnreadableFileError(
            f"Claves desconocidas en el archivo: {', '.join(sorted(unknown))}."
        )
    return data


def _entries[M: BaseModel, S](
    raw: list[Any],
    model: type[M],
    convert: Callable[[M], S],
    entity: EntryKind,
    errors: list[EntryError],
    label: str,
) -> list[S]:
    out: list[S] = []
    for index, entry in enumerate(raw, start=1):
        code = (
            str(entry.get("id") or entry.get("codigo") or f"{label} {index}")
            if isinstance(entry, dict)
            else f"{label} {index}"
        )
        try:
            out.append(convert(model.model_validate(entry)))
        except ValidationError as error:
            errors.append(EntryError(code=code, entity=entity, issues=issues_from(error)))
    return out


def _module_spec(model: m.Modulo, *, position: int, questions: dict[str, Any] | None) -> ModuleSpec:
    return mapping.module_spec(model, position, questions)


def read_bundle(content: bytes) -> Bundle:
    data = _decode(content)
    errors: list[EntryError] = []
    exam = data.get("estructura_examen") or {}
    questions = exam.get("preguntas_por_modulo") if isinstance(exam, dict) else None
    modules: list[Any] = []
    for position, raw in enumerate(data.get("modulos", []), start=1):
        modules.extend(
            _entries(
                [raw],
                m.Modulo,
                partial(_module_spec, position=position, questions=questions),
                EntryKind.TAXONOMY_NODE,
                errors,
                "módulo",
            )
        )
    items = _entries(
        data.get("items", []), m.Item, mapping.item_spec, EntryKind.ITEM, errors, "ítem"
    )
    items += _entries(
        data.get("consignas_escritura", []),
        m.Consigna,
        mapping.prompt_spec,
        EntryKind.WRITING_PROMPT,
        errors,
        "consigna",
    )
    return Bundle(
        schema_version=SCHEMA_VERSION,
        modules=modules,
        contexts=_entries(
            data.get("contextos", []),
            m.Contexto,
            mapping.context_spec,
            EntryKind.CONTEXT,
            errors,
            "contexto",
        ),
        items=items,
        rubrics=_entries(
            data.get("rubricas", []), m.Rubrica, mapping.rubric, EntryKind.RUBRIC, errors, "rúbrica"
        ),
        errors=errors,
        metadata={key: data[key] for key in _METADATA if key in data},
    )


def write_bundle(bundle: Bundle) -> bytes:
    from saber_uli.content.domain.item_version import ItemKind

    out: dict[str, Any] = {"esquema_version": SCHEMA_VERSION, **bundle.metadata}
    out["modulos"] = [mapping.module_out(spec) for spec in bundle.modules]
    out["contextos"] = [mapping.context_out(spec) for spec in bundle.contexts]
    out["items"] = [
        mapping.item_out(spec) for spec in bundle.items if spec.kind is not ItemKind.WRITING_PROMPT
    ]
    out["consignas_escritura"] = [
        mapping.item_out(spec) for spec in bundle.items if spec.kind is ItemKind.WRITING_PROMPT
    ]
    out["rubricas"] = [mapping.rubric_out(value) for value in bundle.rubrics]
    return (json.dumps(out, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
