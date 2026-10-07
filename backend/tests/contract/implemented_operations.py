"""Operaciones del contrato ya implementadas (T059). Cada historia agrega sus `operationId`.

El arnés de contrato (`test_openapi_contract.py`) solo prueba estas operaciones; T179 exige al
final que la lista coincida con todas las del contrato.
"""

IMPLEMENTED_OPERATIONS: frozenset[str] = frozenset(
    {
        # Fase 2 (T058, T050)
        "getHealth",
        "getReadiness",
        "refreshSession",
        "logout",
        # US1 (T078, T079)
        "startMicrosoftLogin",
        "completeMicrosoftLogin",
        "getMe",
        # US2 (T090)
        "listMyConsents",
        "decideConsent",
        "revokeConsent",
        "getCurrentPolicy",
        "getPolicyVersion",
        "publishPolicyVersion",
    }
)
