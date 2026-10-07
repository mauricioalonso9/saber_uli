"""Tokens de los enlaces de invitados (research R-18, R-19).

256 bits aleatorios en base64url sin relleno (43 caracteres, caben en el `token` del contrato).
En la base de datos solo se guarda su SHA-256; el token en claro existe solo en memoria del
worker y en el correo.
"""

import hashlib
import secrets

TOKEN_BYTES = 32


def hash_link_token(plaintext: str) -> bytes:
    return hashlib.sha256(plaintext.encode("ascii", errors="replace")).digest()


def new_link_token() -> tuple[str, bytes]:
    """Devuelve el token en claro (para el correo) y su hash (para la base de datos)."""
    plaintext = secrets.token_urlsafe(TOKEN_BYTES)
    return plaintext, hash_link_token(plaintext)


class LinkTokenFactory:
    """Adaptador del puerto `LinkTokenGenerator` (lo usan los casos de uso)."""

    def new(self) -> tuple[str, bytes]:
        return new_link_token()

    def hash(self, plaintext: str) -> bytes:
        return hash_link_token(plaintext)
