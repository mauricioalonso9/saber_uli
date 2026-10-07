"""Perfiles de usuario (data-model §2.2): uno por usuario."""

from uuid import UUID

from sqlalchemy import func
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
        row = await self._db.get(ProfileRow, profile.user_id)
        if row is None:
            row = ProfileRow(user_id=profile.user_id)
            self._db.add(row)
        else:
            row.updated_at = func.now()
        row.program_id = profile.program_id
        row.semester = profile.semester
        row.expected_exam_date = profile.expected_exam_date
        row.daily_goal = profile.daily_goal.value if profile.daily_goal else None
        row.guest_display_name = profile.guest_display_name
        await self._db.flush()
