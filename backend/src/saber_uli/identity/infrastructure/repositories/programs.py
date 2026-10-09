"""Catálogo de programas académicos (data-model §2.5)."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from saber_uli.identity.domain.program import Program, ProgramCodeExistsError
from saber_uli.identity.infrastructure.orm import ProgramRow
from saber_uli.shared.infrastructure.db import LIKE_ESCAPE, contains_pattern


class SqlAlchemyProgramRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._db = session

    async def get(self, program_id: UUID) -> Program | None:
        row = await self._db.get(ProgramRow, program_id)
        return None if row is None else _to_domain(row)

    async def get_by_code(self, code: str) -> Program | None:
        row = await self._db.scalar(select(ProgramRow).where(ProgramRow.code == code))
        return None if row is None else _to_domain(row)

    async def list_active(self) -> list[Program]:
        rows = await self._db.scalars(
            select(ProgramRow)
            .where(ProgramRow.active.is_(True))
            .order_by(ProgramRow.name, ProgramRow.campus, ProgramRow.code)
        )
        return [_to_domain(row) for row in rows]

    async def search(self, *, q: str | None, offset: int, limit: int) -> tuple[list[Program], int]:
        conditions = []
        if q:
            pattern = contains_pattern(q)
            conditions.append(
                func.lower(ProgramRow.code).like(pattern, escape=LIKE_ESCAPE)
                | func.lower(ProgramRow.name).like(pattern, escape=LIKE_ESCAPE)
                | func.lower(ProgramRow.campus).like(pattern, escape=LIKE_ESCAPE)
            )
        total = await self._db.scalar(
            select(func.count()).select_from(ProgramRow).where(*conditions)
        )
        rows = await self._db.scalars(
            select(ProgramRow)
            .where(*conditions)
            .order_by(ProgramRow.name, ProgramRow.campus, ProgramRow.code)
            .offset(offset)
            .limit(limit)
        )
        return [_to_domain(row) for row in rows], int(total or 0)

    async def add(self, program: Program) -> Program:
        row = ProgramRow(
            code=program.code, name=program.name, campus=program.campus, active=program.active
        )
        self._db.add(row)
        try:
            await self._db.flush()
        except IntegrityError as error:
            if "uq_programs_code" in str(error.orig):
                raise ProgramCodeExistsError(
                    f"Ya existe un programa con el código {program.code}."
                ) from error
            raise
        program.id = row.id
        return program

    async def save(self, program: Program) -> None:
        if program.id is None:
            raise ValueError("el programa aún no se ha guardado; use add()")
        row = await self._db.get(ProgramRow, program.id)
        if row is None:
            raise LookupError("el programa no existe")
        row.name, row.campus, row.active = program.name, program.campus, program.active
        row.updated_at = func.now()
        await self._db.flush()


def _to_domain(row: ProgramRow) -> Program:
    return Program(id=row.id, code=row.code, name=row.name, campus=row.campus, active=row.active)
