"""T045: política de sesión y tokens (research R-14, R-15; data-model §2.13; FR-037, FR-038)."""

import base64
import hashlib
from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt
import pytest

from saber_uli.identity.domain.roles import Role
from saber_uli.identity.domain.session import (
    ABSOLUTE_LIFETIME,
    IDLE_TIMEOUT,
    REUSE_GRACE,
    AuthMethod,
    RefreshToken,
    Session,
    SessionExpiredError,
    SessionRevokedError,
    rotate_refresh_token,
)
from saber_uli.identity.infrastructure.tokens import (
    ACCESS_TOKEN_TTL_SECONDS,
    AccessTokenClaims,
    AccessTokenCodec,
    InvalidAccessTokenError,
    hash_refresh_token,
    new_refresh_token,
)
from saber_uli.shared.domain.errors import UnauthenticatedError

NOW = datetime(2026, 10, 6, 12, 0, tzinfo=UTC)
USER_ID = UUID("0192f3c4-0000-7000-8000-000000000001")
SESSION_ID = UUID("0192f3c4-0000-7000-8000-0000000000aa")
KEY = b"k" * 48
OTHER_KEY = b"o" * 48


def codec() -> AccessTokenCodec:
    return AccessTokenCodec({"2026-10": KEY}, active_kid="2026-10")


def claims(**overrides: object) -> AccessTokenClaims:
    values: dict[str, object] = {
        "sub": USER_ID,
        "sid": SESSION_ID,
        "roles": ("student", "teacher"),
        "epoch": 3,
        "priv": True,
        "iat": NOW,
    }
    values.update(overrides)
    return AccessTokenClaims(**values)  # type: ignore[arg-type]


def started(now: datetime = NOW) -> Session:
    session = Session.start(USER_ID, AuthMethod.ENTRA_ID, now)
    session.id = SESSION_ID
    return session


# --- Token de acceso (R-14) ---------------------------------------------------------------------


def test_jwt_hs256_de_600_segundos_con_kid_y_claims_exactos() -> None:
    token = codec().encode(claims())

    header = jwt.get_unverified_header(token)
    payload = jwt.decode(token, KEY, algorithms=["HS256"], options={"verify_exp": False})

    assert header["alg"] == "HS256"
    assert header["kid"] == "2026-10"
    assert set(payload) == {"sub", "sid", "roles", "epoch", "priv", "iat", "exp"}
    assert payload["exp"] - payload["iat"] == ACCESS_TOKEN_TTL_SECONDS == 600
    assert payload["sub"] == str(USER_ID)
    assert payload["sid"] == str(SESSION_ID)
    assert payload["roles"] == ["student", "teacher"]
    assert (payload["epoch"], payload["priv"]) == (3, True)


def test_decodificar_devuelve_los_claims() -> None:
    decoded = codec().decode(codec().encode(claims()), now=NOW + timedelta(seconds=599))

    assert decoded.sub == USER_ID
    assert decoded.sid == SESSION_ID
    assert decoded.roles == ("student", "teacher")
    assert decoded.expires_at == NOW + timedelta(seconds=600)


def test_token_vencido() -> None:
    token = codec().encode(claims())

    with pytest.raises(InvalidAccessTokenError):
        codec().decode(token, now=NOW + timedelta(seconds=600))


@pytest.mark.parametrize(
    "token",
    [
        jwt.encode({"sub": "x"}, OTHER_KEY, algorithm="HS256", headers={"kid": "2026-10"}),
        jwt.encode({"sub": "x"}, KEY, algorithm="HS256", headers={"kid": "otra"}),
        jwt.encode({"sub": "x"}, KEY * 2, algorithm="HS512", headers={"kid": "2026-10"}),
        jwt.encode({"sub": "x"}, None, algorithm="none", headers={"kid": "2026-10"}),
        "no-es-un-jwt",
    ],
    ids=["firma", "kid-desconocido", "alg-hs512", "alg-none", "basura"],
)
def test_tokens_invalidos(token: str) -> None:
    with pytest.raises(InvalidAccessTokenError) as info:
        codec().decode(token, now=NOW)
    assert isinstance(info.value, UnauthenticatedError)
    assert info.value.slug == "unauthenticated"


def test_faltan_claims() -> None:
    token = jwt.encode(
        {"sub": str(USER_ID), "exp": int((NOW + timedelta(minutes=5)).timestamp())},
        KEY,
        algorithm="HS256",
        headers={"kid": "2026-10"},
    )

    with pytest.raises(InvalidAccessTokenError):
        codec().decode(token, now=NOW)


def test_rotacion_de_claves_por_kid() -> None:
    old = AccessTokenCodec({"2026-09": OTHER_KEY}, active_kid="2026-09").encode(claims())
    rotated = AccessTokenCodec({"2026-10": KEY, "2026-09": OTHER_KEY}, active_kid="2026-10")

    assert rotated.decode(old, now=NOW).sub == USER_ID
    assert jwt.get_unverified_header(rotated.encode(claims()))["kid"] == "2026-10"


def test_la_clave_debe_tener_256_bits() -> None:
    with pytest.raises(ValueError):
        AccessTokenCodec({"k": b"corta"}, active_kid="k")


# --- Token de renovación (R-14, R-19) ----------------------------------------------------------


def test_token_de_renovacion_de_256_bits_guardado_solo_como_sha256() -> None:
    plaintext, token_hash = new_refresh_token()

    raw = base64.urlsafe_b64decode(plaintext + "=" * (-len(plaintext) % 4))
    assert len(raw) == 32
    assert token_hash == hashlib.sha256(plaintext.encode()).digest()
    assert hash_refresh_token(plaintext) == token_hash
    assert len(token_hash) == 32
    assert new_refresh_token()[0] != plaintext


def rt(now: datetime, session: Session) -> RefreshToken:
    return RefreshToken.issue(session, token_hash=b"\x01" * 32, now=now)


def test_rotacion_en_cada_uso() -> None:
    session = started()
    current = rt(NOW, session)
    later = NOW + timedelta(days=1)

    new = rotate_refresh_token(session, current, new_hash=b"\x02" * 32, now=later)

    assert current.rotated_at == later
    assert new.token_hash == b"\x02" * 32
    assert new.rotated_at is None
    assert new.idle_expires_at == later + IDLE_TIMEOUT
    assert session.last_seen_at == later


def test_reutilizar_un_token_rotado_revoca_la_sesion() -> None:
    session = started()
    current = rt(NOW, session)
    rotate_refresh_token(session, current, new_hash=b"\x02" * 32, now=NOW + timedelta(minutes=10))

    with pytest.raises(SessionRevokedError) as info:
        rotate_refresh_token(
            session, current, new_hash=b"\x03" * 32, now=NOW + timedelta(minutes=11)
        )

    assert info.value.slug == "session-revoked"
    assert session.revoked_at == NOW + timedelta(minutes=11)
    assert session.revoked_reason == "token_reuse"
    assert not session.is_active(NOW + timedelta(minutes=12))


@pytest.mark.parametrize("delay", [timedelta(0), timedelta(seconds=30)])
def test_reutilizar_dentro_del_margen_es_una_carrera_y_no_revoca(delay: timedelta) -> None:
    # Dos pestañas que renuevan a la vez, o la app cerrada antes de recibir la cookie nueva.
    session = started()
    current = rt(NOW, session)
    rotated_at = NOW + timedelta(minutes=10)
    rotate_refresh_token(session, current, new_hash=b"" * 32, now=rotated_at)

    again = rotate_refresh_token(session, current, new_hash=b"" * 32, now=rotated_at + delay)

    assert again.token_hash == b"" * 32
    assert session.revoked_at is None
    assert current.rotated_at == rotated_at  # el margen cuenta desde la primera rotación


def test_reutilizar_pasado_el_margen_revoca() -> None:
    session = started()
    current = rt(NOW, session)
    rotated_at = NOW + timedelta(minutes=10)
    rotate_refresh_token(session, current, new_hash=b"" * 32, now=rotated_at)

    with pytest.raises(SessionRevokedError):
        rotate_refresh_token(
            session,
            current,
            new_hash=b"" * 32,
            now=rotated_at + REUSE_GRACE + timedelta(seconds=1),
        )
    assert session.revoked_reason == "token_reuse"


def test_una_sesion_revocada_no_se_renueva() -> None:
    session = started()
    current = rt(NOW, session)
    session.revoke(NOW, "logout")

    with pytest.raises(SessionRevokedError):
        rotate_refresh_token(
            session, current, new_hash=b"\x02" * 32, now=NOW + timedelta(seconds=1)
        )


def test_inactividad_de_7_dias() -> None:
    session = started()
    current = rt(NOW, session)

    with pytest.raises(SessionExpiredError) as info:
        rotate_refresh_token(
            session, current, new_hash=b"\x02" * 32, now=NOW + IDLE_TIMEOUT + timedelta(seconds=1)
        )
    assert info.value.slug == "session-expired"


def test_duracion_absoluta_de_30_dias_aunque_se_renueve() -> None:
    session = started()
    token = rt(NOW, session)
    for day in (6, 12, 18, 24, 29):
        token = rotate_refresh_token(
            session, token, new_hash=bytes([day]) * 32, now=NOW + timedelta(days=day)
        )

    # El último token no puede vivir más allá del límite absoluto.
    assert token.idle_expires_at == NOW + ABSOLUTE_LIFETIME
    with pytest.raises(SessionExpiredError):
        rotate_refresh_token(
            session,
            token,
            new_hash=b"\x09" * 32,
            now=NOW + ABSOLUTE_LIFETIME + timedelta(seconds=1),
        )


# --- Sesión privilegiada (R-15) ----------------------------------------------------------------


def test_un_administrador_recien_autenticado_tiene_priv() -> None:
    session = started()

    assert session.last_privileged_activity_at == session.auth_time == NOW
    assert session.is_privileged(NOW, roles={Role.STUDENT, Role.ADMIN})


def test_sin_rol_privilegiado_no_hay_priv() -> None:
    assert not started().is_privileged(NOW, roles={Role.STUDENT})
    assert not started().is_privileged(NOW, roles={Role.GUEST})


def test_31_minutos_sin_actividad_privilegiada_quita_priv() -> None:
    session = started()
    roles = {Role.STUDENT, Role.TEACHER}

    assert session.is_privileged(NOW + timedelta(minutes=29), roles=roles)
    assert not session.is_privileged(NOW + timedelta(minutes=31), roles=roles)


def test_la_actividad_privilegiada_extiende_la_ventana_hasta_12_horas() -> None:
    session = started()
    roles = {Role.STUDENT, Role.ADMIN}
    for minutes in range(20, 12 * 60, 20):
        session.record_privileged_activity(NOW + timedelta(minutes=minutes))

    assert session.is_privileged(NOW + timedelta(hours=11, minutes=59), roles=roles)
    # Con actividad reciente, pero más de 12 horas desde la autenticación real.
    session.record_privileged_activity(NOW + timedelta(hours=12))
    assert not session.is_privileged(NOW + timedelta(hours=12, minutes=1), roles=roles)


def test_reautenticarse_restaura_priv() -> None:
    session = started()
    roles = {Role.STUDENT, Role.ADMIN}
    later = NOW + timedelta(hours=13)

    session.reauthenticate(later)

    assert session.auth_time == session.last_privileged_activity_at == later
    assert session.is_privileged(later, roles=roles)


def test_la_sesion_dura_30_dias_como_maximo() -> None:
    session = started()

    assert session.absolute_expires_at == NOW + ABSOLUTE_LIFETIME
    assert session.is_active(NOW + ABSOLUTE_LIFETIME - timedelta(seconds=1))
    assert not session.is_active(NOW + ABSOLUTE_LIFETIME)
