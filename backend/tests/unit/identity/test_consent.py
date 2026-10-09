"""T084: reglas de autorización y versiones de la política (FR-014 a FR-018; data-model §2.10)."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from saber_uli.identity.domain.consent import (
    WEB_PWA_CHANNEL,
    ConsentDecision,
    ConsentRecord,
    InvalidConsentDecisionError,
    NoActiveConsentError,
    PolicyVersionNotCurrentError,
    consent_is_current,
    decide_consent,
    revoke_consent,
)
from saber_uli.identity.domain.policy import (
    EffectiveFromTooEarlyError,
    InvalidPolicyVersionError,
    PolicyVersion,
    PolicyVersionExistsError,
)
from saber_uli.shared.domain.errors import ConflictError, RuleViolationError

CURRENT = UUID("00000000-0000-7000-8000-000000000002")
OLD = UUID("00000000-0000-7000-8000-000000000001")
ADMIN = UUID("00000000-0000-7000-8000-0000000000aa")
T0 = datetime(2026, 10, 7, 12, 0, tzinfo=UTC)
BODY = "Finalidad, datos recogidos, derechos y canales. " * 5  # 245 caracteres


def record(decision: ConsentDecision, version: UUID = CURRENT) -> ConsentRecord:
    return ConsentRecord(policy_version_id=version, decision=decision, decided_at=T0)


# ---------------------------------------------------------------------------- decidir


@pytest.mark.parametrize("decision", [ConsentDecision.ACCEPTED, ConsentDecision.REJECTED])
def test_se_decide_aceptar_o_rechazar_sobre_la_version_vigente(
    decision: ConsentDecision,
) -> None:
    result = decide_consent(
        decision, policy_version_id=CURRENT, current_policy_version_id=CURRENT, now=T0
    )

    assert result == ConsentRecord(
        policy_version_id=CURRENT, decision=decision, decided_at=T0, channel=WEB_PWA_CHANNEL
    )
    assert result.channel == "web_pwa"


def test_revocar_no_es_una_decision_valida() -> None:
    with pytest.raises(InvalidConsentDecisionError) as info:
        decide_consent(
            ConsentDecision.REVOKED,
            policy_version_id=CURRENT,
            current_policy_version_id=CURRENT,
            now=T0,
        )
    assert isinstance(info.value, RuleViolationError)


def test_decidir_sobre_una_version_anterior_se_rechaza() -> None:
    with pytest.raises(PolicyVersionNotCurrentError) as info:
        decide_consent(
            ConsentDecision.ACCEPTED,
            policy_version_id=OLD,
            current_policy_version_id=CURRENT,
            now=T0,
        )
    assert info.value.slug == "policy-version-not-current"
    assert isinstance(info.value, ConflictError)


def test_sin_politica_publicada_no_se_puede_decidir() -> None:
    with pytest.raises(PolicyVersionNotCurrentError):
        decide_consent(
            ConsentDecision.ACCEPTED,
            policy_version_id=CURRENT,
            current_policy_version_id=None,
            now=T0,
        )


# ---------------------------------------------------------------------------- revocar


def test_se_revoca_una_autorizacion_vigente() -> None:
    result = revoke_consent(
        record(ConsentDecision.ACCEPTED), current_policy_version_id=CURRENT, now=T0
    )

    assert result.decision is ConsentDecision.REVOKED
    assert result.policy_version_id == CURRENT
    assert result.decided_at == T0
    assert not consent_is_current(result, current_policy_version_id=CURRENT)


@pytest.mark.parametrize(
    "latest",
    [
        None,
        record(ConsentDecision.REJECTED),
        record(ConsentDecision.REVOKED),
        record(ConsentDecision.ACCEPTED, version=OLD),
    ],
    ids=["sin-registros", "rechazada", "ya-revocada", "version-anterior"],
)
def test_sin_autorizacion_vigente_no_hay_que_revocar(latest: ConsentRecord | None) -> None:
    with pytest.raises(NoActiveConsentError) as info:
        revoke_consent(latest, current_policy_version_id=CURRENT, now=T0)
    assert info.value.slug == "no-active-consent"
    assert isinstance(info.value, ConflictError)


# ---------------------------------------------------------------------------- publicar


def publish(**overrides: object) -> PolicyVersion:
    values: dict[str, object] = {
        "version": "2.0",
        "title": "Política de tratamiento de datos",
        "body_markdown": BODY,
        "effective_from": T0 + timedelta(days=1),
        "published_by": ADMIN,
        "existing_versions": {"1.0"},
        "latest_effective_from": T0,
    }
    values.update(overrides)
    return PolicyVersion.publish(**values)  # type: ignore[arg-type]


def test_se_publica_una_version_nueva() -> None:
    version = publish()

    assert version.id is None  # lo asigna la base de datos
    assert (version.version, version.published_by) == ("2.0", ADMIN)
    assert version.effective_from == T0 + timedelta(days=1)


@pytest.mark.parametrize("value", ["2", "v2.0", "2.0.1", "2.", ".1", "2,0", " 2.0", "2.0\n"])
def test_la_version_debe_tener_el_formato_mayor_punto_menor(value: str) -> None:
    with pytest.raises(InvalidPolicyVersionError) as info:
        publish(version=value)
    assert isinstance(info.value, RuleViolationError)


@pytest.mark.parametrize("length", [200, 100_000])
def test_el_texto_admite_de_200_a_100000_caracteres(length: int) -> None:
    assert len(publish(body_markdown="x" * length).body_markdown) == length


@pytest.mark.parametrize("length", [0, 199, 100_001])
def test_el_texto_fuera_de_rango_se_rechaza(length: int) -> None:
    with pytest.raises(InvalidPolicyVersionError):
        publish(body_markdown="x" * length)


@pytest.mark.parametrize("title", ["", "   ", "t" * 201])
def test_el_titulo_es_obligatorio_y_de_maximo_200_caracteres(title: str) -> None:
    with pytest.raises(InvalidPolicyVersionError):
        publish(title=title)


def test_la_version_debe_ser_unica() -> None:
    with pytest.raises(PolicyVersionExistsError) as info:
        publish(version="1.0")
    assert isinstance(info.value, ConflictError)


@pytest.mark.parametrize("offset", [timedelta(0), -timedelta(seconds=1)])
def test_la_vigencia_debe_ser_posterior_a_la_de_la_ultima_version(offset: timedelta) -> None:
    # Con la misma fecha la versión vigente sería ambigua; con una anterior, nunca regiría.
    with pytest.raises(EffectiveFromTooEarlyError) as info:
        publish(effective_from=T0 + offset)
    assert isinstance(info.value, RuleViolationError)


def test_la_primera_version_no_tiene_limite_de_vigencia() -> None:
    assert publish(latest_effective_from=None, effective_from=T0).effective_from == T0
