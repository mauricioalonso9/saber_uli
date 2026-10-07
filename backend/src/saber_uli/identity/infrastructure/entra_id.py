"""Cliente OIDC de Microsoft Entra ID (research R-10 a R-13; FR-001, FR-002, FR-004).

- Autoridad del inquilino de la Universidad Libre, nunca `common` ni `organizations` (R-11).
- Flujo authorization code con PKCE S256; `state` y `nonce` aleatorios (el router los guarda en
  la cookie firmada `su_oidc`, R-13).
- El canje del código lo hace Authlib (`AsyncOAuth2Client`, `client_secret_post`).
- El ID token se valida con PyJWT: solo RS256, clave por `kid` del JWKS del proveedor (si el
  `kid` no está se vuelve a descargar una vez, para la rotación de claves), `iss` igual al del
  descubrimiento, `aud` igual al `client_id`, `nonce`, vencimiento y `tid` del inquilino.
- Solo se toman `oid`, `tid`, `name` y `email` (o `preferred_username`); nada más del token
  (R-12, minimización). No se llama a Microsoft Graph.
"""

import base64
import hashlib
import hmac
import secrets
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode, urlsplit
from uuid import UUID

import httpx
import jwt
from authlib.integrations.base_client.errors import OAuthError
from authlib.integrations.httpx_client import AsyncOAuth2Client

from saber_uli.identity.application.authenticate_institutional_user import (
    InstitutionalClaims,
    TenantNotAllowedError,
)

_SCOPES = "openid profile email"
_MULTITENANT = frozenset({"common", "organizations", "consumers"})
_TIMEOUT = httpx.Timeout(10.0)
_LEEWAY_SECONDS = 60


class IdpUnavailableError(Exception):
    """El proveedor de identidad no responde o respondió con un error del servidor."""


class LoginFailedError(Exception):
    """El código o el ID token no son válidos (firma, `aud`, `iss`, `nonce`, vencimiento…)."""


@dataclass(frozen=True)
class AuthorizationRequest:
    url: str
    state: str
    nonce: str
    code_verifier: str


def _s256(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


class EntraIdClient:
    def __init__(
        self,
        *,
        authority: str,
        tenant_id: UUID,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
    ) -> None:
        segments = {s.lower() for s in urlsplit(authority).path.split("/") if s}
        if segments & _MULTITENANT or str(tenant_id).lower() not in segments:
            raise ValueError("la autoridad debe ser la del inquilino configurado (R-11)")
        self._authority = authority.rstrip("/")
        self._tenant_id = tenant_id
        self._client_id = client_id
        self._client_secret = client_secret
        self._redirect_uri = redirect_uri
        self._metadata: dict[str, Any] | None = None
        self._jwks: jwt.PyJWKSet | None = None

    # --- Descubrimiento y claves ---------------------------------------------------------------

    async def _get_json(self, url: str) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as http:
                response = await http.get(url)
        except httpx.HTTPError as error:
            raise IdpUnavailableError("no se pudo contactar al proveedor") from error
        if response.status_code >= 500 or response.status_code == 429:
            raise IdpUnavailableError(f"el proveedor respondió {response.status_code}")
        if response.status_code != 200:
            raise LoginFailedError(f"respuesta inesperada del proveedor ({response.status_code})")
        data: dict[str, Any] = response.json()
        return data

    async def _discovery(self) -> dict[str, Any]:
        if self._metadata is None:
            metadata = await self._get_json(f"{self._authority}/.well-known/openid-configuration")
            required = ("issuer", "authorization_endpoint", "token_endpoint", "jwks_uri")
            if any(not metadata.get(key) for key in required):
                raise LoginFailedError("descubrimiento OIDC incompleto")
            if str(self._tenant_id).lower() not in str(metadata["issuer"]).lower():
                raise LoginFailedError("el emisor del descubrimiento no es el del inquilino")
            self._metadata = metadata
        return self._metadata

    async def _signing_key(self, kid: str) -> Any:
        metadata = await self._discovery()
        for attempt in range(2):
            if self._jwks is None or attempt == 1:
                self._jwks = jwt.PyJWKSet.from_dict(await self._get_json(metadata["jwks_uri"]))
            for key in self._jwks.keys:
                if key.key_id == kid:
                    return key.key
        raise LoginFailedError("clave de firma desconocida")

    # --- Flujo ---------------------------------------------------------------------------------

    async def begin(self) -> AuthorizationRequest:
        metadata = await self._discovery()
        state = secrets.token_urlsafe(32)
        nonce = secrets.token_urlsafe(32)
        verifier = secrets.token_urlsafe(64)
        query = urlencode(
            {
                "client_id": self._client_id,
                "response_type": "code",
                "response_mode": "query",
                "redirect_uri": self._redirect_uri,
                "scope": _SCOPES,
                "state": state,
                "nonce": nonce,
                "code_challenge": _s256(verifier),
                "code_challenge_method": "S256",
            }
        )
        return AuthorizationRequest(
            url=f"{metadata['authorization_endpoint']}?{query}",
            state=state,
            nonce=nonce,
            code_verifier=verifier,
        )

    async def complete(self, *, code: str, code_verifier: str, nonce: str) -> InstitutionalClaims:
        metadata = await self._discovery()
        id_token = await self._exchange(metadata["token_endpoint"], code, code_verifier)
        claims = await self._validate(id_token, metadata["issuer"], nonce)
        return self._extract(claims)

    async def _exchange(self, token_endpoint: str, code: str, code_verifier: str) -> str:
        try:
            async with AsyncOAuth2Client(
                client_id=self._client_id,
                client_secret=self._client_secret,
                token_endpoint_auth_method="client_secret_post",  # noqa: S106 - método, no secreto
                timeout=_TIMEOUT,
            ) as oauth:
                token: dict[str, Any] = await oauth.fetch_token(
                    token_endpoint,
                    grant_type="authorization_code",
                    code=code,
                    code_verifier=code_verifier,
                    redirect_uri=self._redirect_uri,
                )
        except OAuthError as error:
            raise LoginFailedError("el proveedor rechazó el código") from error
        except httpx.HTTPStatusError as error:
            if error.response.status_code >= 500:
                raise IdpUnavailableError("el proveedor no respondió el canje") from error
            raise LoginFailedError("el proveedor rechazó el código") from error
        except httpx.HTTPError as error:
            raise IdpUnavailableError("no se pudo contactar al proveedor") from error
        except ValueError as error:  # cuerpo que no es JSON (por ejemplo, una página de error)
            raise IdpUnavailableError("respuesta inválida del proveedor") from error
        id_token = token.get("id_token")
        if not isinstance(id_token, str):
            raise LoginFailedError("el proveedor no entregó un ID token")
        return id_token

    async def _validate(self, id_token: str, issuer: str, nonce: str) -> dict[str, Any]:
        try:
            header = jwt.get_unverified_header(id_token)
            if header.get("alg") != "RS256" or not isinstance(header.get("kid"), str):
                raise LoginFailedError("algoritmo o clave del ID token no permitidos")
            key = await self._signing_key(header["kid"])
            claims: dict[str, Any] = jwt.decode(
                id_token,
                key,
                algorithms=["RS256"],
                audience=self._client_id,
                issuer=issuer,
                leeway=_LEEWAY_SECONDS,
                options={"require": ["exp", "iat", "iss", "aud", "nonce", "tid", "oid"]},
            )
        except jwt.PyJWTError as error:
            raise LoginFailedError("ID token inválido") from error
        if not hmac.compare_digest(str(claims.get("nonce", "")), nonce):
            raise LoginFailedError("nonce distinto")
        if str(claims.get("tid", "")).lower() != str(self._tenant_id).lower():
            raise TenantNotAllowedError("Solo pueden ingresar cuentas de la Universidad Libre.")
        return claims

    @staticmethod
    def _extract(claims: dict[str, Any]) -> InstitutionalClaims:
        email = claims.get("email") or claims.get("preferred_username")
        if not isinstance(email, str) or "@" not in email:
            raise LoginFailedError("el ID token no trae un correo")
        try:
            tenant_id, object_id = UUID(str(claims["tid"])), UUID(str(claims["oid"]))
        except (KeyError, ValueError) as error:
            raise LoginFailedError("identificadores del ID token inválidos") from error
        name = claims.get("name")
        return InstitutionalClaims(
            tenant_id=tenant_id,
            object_id=object_id,
            name=name if isinstance(name, str) else None,
            email=email.strip(),
        )
