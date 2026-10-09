"""Persistencia con SQLAlchemy 2 asíncrono y asyncpg (research R-06).

Las URL llegan como `str`: quien tenga un `SecretStr` (config.py) llama a `get_secret_value()`
en la raíz de composición, nunca aquí.
"""

from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from saber_uli.shared.application.event_bus import EventBus
from saber_uli.shared.application.unit_of_work import UnitOfWork

# Nombres estables de restricciones e índices para las migraciones (T028, T044).
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


def create_engine(url: str) -> AsyncEngine:
    return create_async_engine(url, pool_pre_ping=True)


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


class SqlAlchemyUnitOfWork(UnitOfWork):
    """Unidad de trabajo sobre una `AsyncSession`; los repositorios usan `uow.session`."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession], bus: EventBus) -> None:
        super().__init__(bus)
        self._session_factory = session_factory
        self._session: AsyncSession | None = None

    @property
    def session(self) -> AsyncSession:
        if self._session is None:
            raise RuntimeError("use la unidad de trabajo dentro de `async with`")
        return self._session

    async def _begin(self) -> None:
        self._session = self._session_factory()

    async def _commit(self) -> None:
        await self.session.commit()

    async def _rollback(self) -> None:
        await self.session.rollback()

    async def _close(self) -> None:
        if self._session is not None:
            await self._session.close()
            self._session = None


LIKE_ESCAPE = "\\"


def contains_pattern(text: str) -> str:
    """Patrón de `LIKE … ESCAPE '\'` que busca `text` (en minúsculas) como subcadena literal."""
    escaped = text.strip().lower().replace("\\", "\\\\").replace("%", r"\%").replace("_", r"\_")
    return f"%{escaped}%"
