"""Tokens de acceso (JWT HS256) y de renovación (research R-14, R-19).

- Acceso: JWT HS256 de 600 s con `kid` en la cabecera para rotar claves; claims exactos `sub`,
  `sid`, `roles`, `epoch`, `priv`, `iat` y `exp`. Solo se acepta HS256 (nunca `none` ni otro
  algoritmo) y el vencimiento se comprueba con el reloj inyectado.
- Renovación: 256 bits aleatorios codificados en base64url; en la base de datos solo se guarda su
  SHA-256.
"""

import hashlib
import secrets
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import jwt

from saber_uli.shared.domain.errors import UnauthenticatedError

ACCESS_TOKEN_TTL_SECONDS = 600
_ALGORITHM = "HS256"
_REQUIRED = frozenset({"sub", "sid", "roles", "epoch", "priv", "iat", "exp"})
_MIN_KEY_BYTES = 32


class InvalidAccessTokenError(UnauthenticatedError):
    """Token ausente, mal formado, con firma inválida o vencido."""


@dataclass(frozen=True)
class AccessTokenClaims:
    sub: UUID
    sid: UUID
    roles: tuple[str, ...]
    epoch: int
    priv: bool
    iat: datetime

    @property
    def expires_at(self) -> datetime:
        return self.iat + timedelta(seconds=ACCESS_TOKEN_TTL_SECONDS)


class AccessTokenCodec:
    def __init__(self, keys: Mapping[str, bytes], *, active_kid: str) -> None:
        if active_kid not in keys:
            raise ValueError("active_kid no está entre las claves")
        if any(len(key) < _MIN_KEY_BYTES for key in keys.values()):
            raise ValueError("cada clave de firma debe tener al menos 256 bits")
        self._keys = dict(keys)
        self._active_kid = active_kid

    def encode(self, claims: AccessTokenClaims) -> str:
        iat = int(claims.iat.timestamp())
        payload = {
            "sub": str(claims.sub),
            "sid": str(claims.sid),
            "roles": list(claims.roles),
            "epoch": claims.epoch,
            "priv": claims.priv,
            "iat": iat,
            "exp": iat + ACCESS_TOKEN_TTL_SECONDS,
        }
        return jwt.encode(
            payload,
            self._keys[self._active_kid],
            algorithm=_ALGORITHM,
            headers={"kid": self._active_kid},
        )

    def decode(self, token: str, *, now: datetime) -> AccessTokenClaims:
        try:
            kid = jwt.get_unverified_header(token).get("kid")
            key = self._keys.get(kid) if isinstance(kid, str) else None
            if key is None:
                raise InvalidAccessTokenError("Token de acceso inválido.")
            payload: dict[str, Any] = jwt.decode(
                token,
                key,
                algorithms=[_ALGORITHM],
                options={"verify_exp": False, "verify_iat": False, "require": sorted(_REQUIRED)},
            )
            claims = AccessTokenClaims(
                sub=UUID(payload["sub"]),
                sid=UUID(payload["sid"]),
                roles=tuple(str(role) for role in payload["roles"]),
                epoch=int(payload["epoch"]),
                priv=payload["priv"] is True,
                iat=datetime.fromtimestamp(int(payload["iat"]), UTC),
            )
            expires_at = datetime.fromtimestamp(int(payload["exp"]), UTC)
        except InvalidAccessTokenError:
            raise
        except (jwt.PyJWTError, KeyError, TypeError, ValueError):
            raise InvalidAccessTokenError("Token de acceso inválido.") from None
        if now >= expires_at:
            raise InvalidAccessTokenError("El token de acceso venció.")
        return claims


def hash_refresh_token(plaintext: str) -> bytes:
    return hashlib.sha256(plaintext.encode()).digest()


def new_refresh_token() -> tuple[str, bytes]:
    """Devuelve el token en claro (va solo a la cookie) y su SHA-256 (va a la base de datos)."""
    plaintext = secrets.token_urlsafe(32)
    return plaintext, hash_refresh_token(plaintext)
