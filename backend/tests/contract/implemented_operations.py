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
        # US3 (T100)
        "listActivePrograms",
        "getMyProfile",
        "updateMyProfile",
        # US4 (T115)
        "createGuestSession",
        "requestGuestSignInLink",
        # US5 (T130)
        "listInvitations",
        "createInvitation",
        "getInvitation",
        "updateInvitationExpiry",
        "resendInvitation",
        "revokeInvitation",
        "validateInvitationBatch",
        "getInvitationBatch",
        "confirmInvitationBatch",
    }
)
