"""T051: autorización de datos vigente (data-model §2.11; FR-014, FR-017, FR-018)."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from saber_uli.identity.domain.consent import ConsentDecision, ConsentRecord, consent_is_current

NOW = datetime(2026, 10, 6, 12, 0, tzinfo=UTC)
V1 = UUID(int=1)
V2 = UUID(int=2)


def record(decision: ConsentDecision, version: UUID = V1) -> ConsentRecord:
    return ConsentRecord(policy_version_id=version, decision=decision, decided_at=NOW)


def test_vigente_si_el_ultimo_registro_acepta_la_version_vigente() -> None:
    assert consent_is_current(record(ConsentDecision.ACCEPTED), current_policy_version_id=V1)


def test_sin_registros_no_hay_autorizacion() -> None:
    assert not consent_is_current(None, current_policy_version_id=V1)


@pytest.mark.parametrize("decision", [ConsentDecision.REJECTED, ConsentDecision.REVOKED])
def test_rechazo_o_revocacion(decision: ConsentDecision) -> None:
    assert not consent_is_current(record(decision), current_policy_version_id=V1)


def test_una_version_nueva_exige_aceptar_de_nuevo() -> None:
    assert not consent_is_current(
        record(ConsentDecision.ACCEPTED, V1), current_policy_version_id=V2
    )


def test_sin_politica_publicada_no_hay_autorizacion_posible() -> None:
    assert not consent_is_current(record(ConsentDecision.ACCEPTED), current_policy_version_id=None)


def test_el_registro_es_inmutable() -> None:
    consent = record(ConsentDecision.ACCEPTED)

    with pytest.raises(AttributeError):
        consent.decision = ConsentDecision.REVOKED  # type: ignore[misc]
    assert consent.decided_at == NOW
    assert NOW - timedelta(seconds=1) < consent.decided_at
