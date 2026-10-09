"""Perfiles de usuario (data-model §2.2): uno por usuario."""

from uuid import UUID

from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from saber_uli.identity.domain.profile import DailyGoal, Profile
from saber_uli.identity.infrastructure.orm import ProfileRow


class SqlAlchemyProfileRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._db = session

    async def get(self, user_id: UUID) -> Profile | None:
        row = await self._db.get(ProfileRow, user_id)
        if row is None:
            return None
        return Profile(
            user_id=row.user_id,
            daily_goal=DailyGoal(row.daily_goal) if row.daily_goal else None,
            program_id=row.program_id,
            semester=row.semester,
            expected_exam_date=row.expected_exam_date,
            guest_display_name=row.guest_display_name,
        )

    async def save(self, profile: Profile) -> None:
        values = {
            "program_id": profile.program_id,
            "semester": profile.semester,
            "expected_exam_date": profile.expected_exam_date,
            "daily_goal": profile.daily_goal.value if profile.daily_goal else None,
            "guest_display_name": profile.guest_display_name,
        }
        row = await self._db.get(ProfileRow, profile.user_id)
        if row is not None:
            for name, value in values.items():
                setattr(row, name, value)
            row.updated_at = func.now()
            await self._db.flush()
            return
        # Primer guardado: dos envíos simultáneos (doble toque) no deben chocar con la llave.
        statement = insert(ProfileRow).values(user_id=profile.user_id, **values)
        await self._db.execute(
            statement.on_conflict_do_update(
                index_elements=[ProfileRow.user_id], set_={**values, "updated_at": func.now()}
            )
        )
