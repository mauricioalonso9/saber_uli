"""Carga masiva del catálogo de programas (data-model §2.5; quickstart §3).

Inserta los códigos nuevos y actualiza nombre y seccional de los existentes, sin duplicar al
repetir la carga. Las filas inválidas se reportan con su número y no impiden cargar las demás.
Todo queda auditado con actor `system` (sin `actor_id`). El estado activo de un programa
existente no se toca: se gestiona desde la administración.
"""

from collections.abc import Callable, Iterable
from dataclasses import dataclass, field

from saber_uli.identity.application.audit import AuditAction, AuditTarget, record_audit
from saber_uli.identity.application.unit_of_work import IdentityUnitOfWork
from saber_uli.identity.domain.program import InvalidProgramError, Program
from saber_uli.shared.domain.clock import Clock


@dataclass(frozen=True)
class ProgramLine:
    """Una fila del archivo: `line` es su número (el encabezado es la fila 1)."""

    line: int
    code: str
    name: str
    campus: str


@dataclass(frozen=True)
class RejectedLine:
    line: int
    reason: str


@dataclass
class ImportReport:
    created: int = 0
    updated: int = 0
    unchanged: int = 0
    rejected: list[RejectedLine] = field(default_factory=list)


class ImportPrograms:
    def __init__(self, *, uow_factory: Callable[[], IdentityUnitOfWork], clock: Clock) -> None:
        self._uow_factory = uow_factory
        self._clock = clock

    async def execute(
        self, lines: Iterable[ProgramLine], rejected: Iterable[RejectedLine] = ()
    ) -> ImportReport:
        """`rejected` trae las filas que ya se descartaron al leer el archivo."""
        report = ImportReport(rejected=list(rejected))
        now = self._clock.now()
        seen: set[str] = set()
        async with self._uow_factory() as uow:
            for item in lines:
                code = item.code.strip()
                if code in seen:
                    report.rejected.append(RejectedLine(item.line, f"el código {code} se repite"))
                    continue
                try:
                    candidate = Program.new(code=code, name=item.name, campus=item.campus)
                except InvalidProgramError as error:
                    report.rejected.append(RejectedLine(item.line, error.message))
                    continue
                seen.add(code)
                existing = await uow.programs.get_by_code(candidate.code)
                if existing is None:
                    program = await uow.programs.add(candidate)
                    action = AuditAction.PROGRAM_CREATED
                    report.created += 1
                elif existing.describe(name=candidate.name, campus=candidate.campus):
                    await uow.programs.save(existing)
                    program, action = existing, AuditAction.PROGRAM_UPDATED
                    report.updated += 1
                else:
                    report.unchanged += 1
                    continue
                await record_audit(
                    uow,
                    action,
                    target=AuditTarget.PROGRAM,
                    target_id=program.id,
                    details={"code": program.code, "origin": "import"},
                    now=now,
                )
            await uow.commit()
        report.rejected.sort(key=lambda rejected_line: rejected_line.line)
        return report
