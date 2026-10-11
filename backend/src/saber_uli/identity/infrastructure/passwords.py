"""Hash de contraseñas con Argon2id y lista de contraseñas comunes (ADR 0009; ASVS V2.1.7, V2.4).

`argon2-cffi` con sus parámetros por defecto (RFC 9106, perfil de baja memoria). Las contraseñas
nunca se registran: solo entran a `hash` y `verify`.
"""

from functools import lru_cache
from pathlib import Path

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

_COMMON_FILE = Path(__file__).with_name("common_passwords.txt")


class Argon2PasswordHasher:
    def __init__(self) -> None:
        self._hasher = PasswordHasher()
        # Para igualar el tiempo cuando el usuario no existe (ADR 0009, punto 5).
        self._dummy = self._hasher.hash("saber-uli-sin-usuario")

    def hash(self, password: str) -> str:
        return self._hasher.hash(password)

    def verify(self, password_hash: str, password: str) -> bool:
        try:
            return self._hasher.verify(password_hash, password)
        except (VerifyMismatchError, VerificationError, InvalidHashError):
            return False

    def needs_rehash(self, password_hash: str) -> bool:
        return self._hasher.check_needs_rehash(password_hash)

    def waste_time(self, password: str) -> None:
        self.verify(self._dummy, password)


@lru_cache(maxsize=1)
def common_passwords() -> frozenset[str]:
    """Lista de contraseñas comunes, en minúsculas (una por línea; `#` es comentario)."""
    lines = _COMMON_FILE.read_text(encoding="utf-8").splitlines()
    return frozenset(
        line.strip().casefold() for line in lines if line.strip() and not line.startswith("#")
    )
