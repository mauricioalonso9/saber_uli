"""Operaciones del contrato de 002 ya implementadas (T005). Cada historia agrega sus `operationId`.

`test_content_contract.py` prueba estas operaciones y, desde T112, exige que la lista coincida con
todas las de `specs/002-banco-items/contracts/openapi.yaml`.
"""

IMPLEMENTED_CONTENT_OPERATIONS: frozenset[str] = frozenset(
    {
        # Fase 2 (T030)
        "listContentModules",
        # US2 (T045)
        "listItems",
        "getItem",
        "getItemHistory",
        "getItemVersion",
        "commentItem",
        "approveItem",
        "returnItem",
        "rejectItem",
        "retireItem",
    }
)
