"""T072: adaptador de Microsoft Entra ID (research R-10 a R-13; FR-001, FR-002, FR-004).

El proveedor se simula con respx: descubrimiento, JWKS y endpoint de token, con claves RSA
generadas en la prueba. Ninguna prueba llama a Entra ID real.
"""

import base64
import hashlib
import time
from collections.abc import Iterator
from typing import Any
from urllib.parse import parse_qs, urlsplit
from uuid import UUID

import httpx
import jwt
import pytest
import respx
from cryptography.hazmat.primitives.asymmetric import rsa
from jwt.algorithms import RSAAlgorithm

from saber_uli.identity.application.authenticate_institutional_user import TenantNotAllowedError
from saber_uli.identity.infrastructure.entra_id import (
    EntraIdClient,
    IdpUnavailableError,
    LoginFailedError,
)

TENANT = UUID("11111111-1111-4111-8111-111111111111")
OTHER_TENANT = UUID("22222222-2222-4222-8222-222222222222")
CLIENT_ID = "33333333-3333-4333-8333-333333333333"
AUTHORITY = f"https://login.microsoftonline.com/{TENANT}/v2.0"
ISSUER = AUTHORITY
BASE = f"https://login.microsoftonline.com/{TENANT}"
REDIRECT = "https://saber.unilibre.edu.co/api/auth/microsoft/callback"
OID = "aaaaaaaa-0000-4000-8000-000000000001"


def rsa_key() -> rsa.RSAPrivateKey:
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


SIGNING_KEY = rsa_key()
OTHER_KEY = rsa_key()


def jwk(key: rsa.RSAPrivateKey, kid: str) -> dict[str, Any]:
    data: dict[str, Any] = RSAAlgorithm.to_jwk(key.public_key(), as_dict=True)
    return {**data, "kid": kid, "use": "sig", "alg": "RS256"}


def id_token(
    *,
    key: rsa.RSAPrivateKey = SIGNING_KEY,
    kid: str = "k1",
    algorithm: str = "RS256",
    **overrides: Any,
) -> str:
    now = int(time.time())
    claims: dict[str, Any] = {
        "iss": ISSUER,
        "aud": CLIENT_ID,
        "iat": now,
        "nbf": now,
        "exp": now + 3600,
        "nonce": "nonce-esperado",
        "tid": str(TENANT),
        "oid": OID,
        "sub": "sub-por-aplicacion",
        "name": "Ana Pérez",
        "email": "ana.perez@unilibre.edu.co",
        "preferred_username": "aperez@unilibre.edu.co",
        "given_name": "Ana",
        "roles": ["algo"],
    }
    claims.update(overrides)
    claims = {k: v for k, v in claims.items() if v is not None}
    return jwt.encode(claims, key, algorithm=algorithm, headers={"kid": kid})


@pytest.fixture
def idp() -> Iterator[respx.MockRouter]:
    with respx.mock(assert_all_called=False) as router:
        router.get(f"{AUTHORITY}/.well-known/openid-configuration").respond(
            json={
                "issuer": ISSUER,
                "authorization_endpoint": f"{BASE}/oauth2/v2.0/authorize",
                "token_endpoint": f"{BASE}/oauth2/v2.0/token",
                "jwks_uri": f"{BASE}/discovery/v2.0/keys",
            }
        )
        router.get(f"{BASE}/discovery/v2.0/keys").respond(json={"keys": [jwk(SIGNING_KEY, "k1")]})
        yield router


def client() -> EntraIdClient:
    return EntraIdClient(
        authority=AUTHORITY,
        tenant_id=TENANT,
        client_id=CLIENT_ID,
        client_secret="secreto-de-cliente",
        redirect_uri=REDIRECT,
    )


def token_endpoint(idp: respx.MockRouter, token: str) -> respx.Route:
    return idp.post(f"{BASE}/oauth2/v2.0/token").respond(
        json={"token_type": "Bearer", "id_token": token, "access_token": "no-se-usa"}
    )


# --- Inicio del flujo ---------------------------------------------------------------------------


async def test_inicio_con_pkce_s256_state_y_nonce(idp: respx.MockRouter) -> None:
    request = await client().begin()

    url = urlsplit(request.url)
    params = {k: v[0] for k, v in parse_qs(url.query).items()}
    assert f"{url.scheme}://{url.netloc}{url.path}" == f"{BASE}/oauth2/v2.0/authorize"
    assert params["client_id"] == CLIENT_ID
    assert params["response_type"] == "code"
    assert params["response_mode"] == "query"
    assert params["redirect_uri"] == REDIRECT
    assert set(params["scope"].split()) == {"openid", "profile", "email"}
    assert params["state"] == request.state
    assert params["nonce"] == request.nonce
    assert params["code_challenge_method"] == "S256"
    challenge = base64.urlsafe_b64encode(hashlib.sha256(request.code_verifier.encode()).digest())
    assert params["code_challenge"] == challenge.rstrip(b"=").decode()
    assert len(request.state) >= 32 and len(request.nonce) >= 32
    assert 43 <= len(request.code_verifier) <= 128


async def test_dos_inicios_usan_valores_distintos(idp: respx.MockRouter) -> None:
    first, second = await client().begin(), await client().begin()

    assert first.state != second.state
    assert first.nonce != second.nonce
    assert first.code_verifier != second.code_verifier


@pytest.mark.parametrize(
    "authority",
    [
        "https://login.microsoftonline.com/common/v2.0",
        "https://login.microsoftonline.com/organizations/v2.0",
        f"https://login.microsoftonline.com/{OTHER_TENANT}/v2.0",
    ],
)
def test_nunca_una_autoridad_multiinquilino_ni_de_otro_inquilino(authority: str) -> None:
    with pytest.raises(ValueError):
        EntraIdClient(
            authority=authority,
            tenant_id=TENANT,
            client_id=CLIENT_ID,
            client_secret="x",
            redirect_uri=REDIRECT,
        )


# --- Retorno: canje del código y validación del ID token -----------------------------------------


async def test_canje_valido_devuelve_solo_los_claims_necesarios(idp: respx.MockRouter) -> None:
    route = token_endpoint(idp, id_token())

    claims = await client().complete(code="codigo", code_verifier="v" * 64, nonce="nonce-esperado")

    assert claims.tenant_id == TENANT
    assert claims.object_id == UUID(OID)
    assert claims.name == "Ana Pérez"
    assert claims.email == "ana.perez@unilibre.edu.co"
    assert set(vars(claims)) == {"tenant_id", "object_id", "name", "email"}
    form = parse_qs(route.calls.last.request.content.decode())
    assert form["grant_type"] == ["authorization_code"]
    assert form["code"] == ["codigo"]
    assert form["code_verifier"] == ["v" * 64]
    assert form["redirect_uri"] == [REDIRECT]


async def test_sin_email_usa_preferred_username(idp: respx.MockRouter) -> None:
    token_endpoint(idp, id_token(email=None))

    claims = await client().complete(code="c", code_verifier="v" * 64, nonce="nonce-esperado")

    assert claims.email == "aperez@unilibre.edu.co"


@pytest.mark.parametrize(
    "token",
    [
        pytest.param(lambda: id_token(key=OTHER_KEY), id="firma-invalida"),
        pytest.param(lambda: id_token(aud="otra-aplicacion"), id="aud-distinto"),
        pytest.param(lambda: id_token(nonce="otro-nonce"), id="nonce-distinto"),
        pytest.param(
            lambda: id_token(iss=f"https://login.microsoftonline.com/{OTHER_TENANT}/v2.0"),
            id="iss-de-otro-inquilino",
        ),
        pytest.param(lambda: id_token(exp=int(time.time()) - 600), id="vencido"),
        pytest.param(lambda: id_token(oid=None), id="sin-oid"),
        pytest.param(
            lambda: jwt.encode(
                {"sub": "x"}, "clave-simetrica-de-32-caracteres!!", algorithm="HS256"
            ),
            id="hs256",
        ),
    ],
)
async def test_id_tokens_rechazados(idp: respx.MockRouter, token: Any) -> None:
    token_endpoint(idp, token())

    with pytest.raises(LoginFailedError):
        await client().complete(code="c", code_verifier="v" * 64, nonce="nonce-esperado")


async def test_tid_distinto_es_inquilino_no_permitido(idp: respx.MockRouter) -> None:
    token_endpoint(idp, id_token(tid=str(OTHER_TENANT)))

    with pytest.raises(TenantNotAllowedError):
        await client().complete(code="c", code_verifier="v" * 64, nonce="nonce-esperado")


async def test_rotacion_de_claves_del_proveedor(idp: respx.MockRouter) -> None:
    idp.get(f"{BASE}/discovery/v2.0/keys").mock(
        side_effect=[
            httpx.Response(200, json={"keys": [jwk(SIGNING_KEY, "k1")]}),
            httpx.Response(200, json={"keys": [jwk(SIGNING_KEY, "k1"), jwk(OTHER_KEY, "k2")]}),
        ]
    )
    entra = client()
    token_endpoint(idp, id_token())
    await entra.complete(code="c", code_verifier="v" * 64, nonce="nonce-esperado")

    token_endpoint(idp, id_token(key=OTHER_KEY, kid="k2"))
    claims = await entra.complete(code="c", code_verifier="v" * 64, nonce="nonce-esperado")

    assert claims.object_id == UUID(OID)


# --- Proveedor no disponible ---------------------------------------------------------------------


async def test_descubrimiento_caido(idp: respx.MockRouter) -> None:
    idp.get(f"{AUTHORITY}/.well-known/openid-configuration").respond(503)

    with pytest.raises(IdpUnavailableError):
        await client().begin()


async def test_sin_conexion_con_el_proveedor(idp: respx.MockRouter) -> None:
    idp.get(f"{AUTHORITY}/.well-known/openid-configuration").mock(
        side_effect=httpx.ConnectError("sin red")
    )

    with pytest.raises(IdpUnavailableError):
        await client().begin()


async def test_endpoint_de_token_caido(idp: respx.MockRouter) -> None:
    idp.post(f"{BASE}/oauth2/v2.0/token").respond(500)

    with pytest.raises(IdpUnavailableError):
        await client().complete(code="c", code_verifier="v" * 64, nonce="nonce-esperado")


async def test_codigo_rechazado_por_el_proveedor(idp: respx.MockRouter) -> None:
    idp.post(f"{BASE}/oauth2/v2.0/token").respond(
        400, json={"error": "invalid_grant", "error_description": "AADSTS70008"}
    )

    with pytest.raises(LoginFailedError):
        await client().complete(code="c", code_verifier="v" * 64, nonce="nonce-esperado")
