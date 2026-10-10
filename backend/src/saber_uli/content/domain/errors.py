"""Errores del banco de ítems. El `slug` es el `type` del contrato de 002."""

from collections.abc import Sequence

from saber_uli.content.domain.validation import ContentIssue
from saber_uli.shared.domain.errors import (
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
    RuleViolationError,
)


class ItemNotFoundError(NotFoundError):
    slug = "not-found"


class ModuleNotFoundError(NotFoundError):
    slug = "not-found"


class InvalidTransitionError(ConflictError):
    slug = "invalid-transition"


class SelfApprovalError(PermissionDeniedError):
    slug = "self-approval-forbidden"


class CodeTakenError(ConflictError):
    slug = "code-taken"


class DuplicateItemError(ConflictError):
    slug = "duplicate-item"


class EditConflictError(ConflictError):
    """La revisión no coincide con `If-Match` (research R-09); la API responde 412."""

    slug = "edit-conflict"


class ContentValidationError(RuleViolationError):
    """Contenido con problemas al enviar a revisión o al crear (FR-024)."""

    slug = "validation-error"

    def __init__(self, issues: Sequence[ContentIssue]) -> None:
        super().__init__("El contenido tiene problemas por corregir.")
        self.issues = tuple(issues)


class FileTooLargeError(RuleViolationError):
    """Imagen de más de 1 MB (research R-11); la API responde 413."""

    slug = "file-too-large"


class UnsupportedMediaError(RuleViolationError):
    """No es PNG, JPEG ni WebP válido, o pasa de 4 000 px por lado (R-11); la API responde 415."""

    slug = "unsupported-media-type"


class TaxonomyNodeNotFoundError(NotFoundError):
    slug = "not-found"


class RubricNotFoundError(NotFoundError):
    slug = "not-found"


class TaxonomyCodeTakenError(ConflictError):
    slug = "taxonomy-code-taken"


class TaxonomyNodeInUseError(ConflictError):
    """La usa algún ítem, contexto o categoría hija: se desactiva, no se borra (FR-045)."""

    slug = "taxonomy-node-in-use"


class RubricCodeTakenError(ConflictError):
    slug = "rubric-code-taken"


class InvalidTaxonomyNodeError(RuleViolationError):
    """La categoría no encaja en la jerarquía (padre de otro tipo o de otro módulo)."""
