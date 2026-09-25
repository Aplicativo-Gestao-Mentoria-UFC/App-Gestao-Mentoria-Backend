from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.activity_model import ActivityModel
from schemas.activity_schema import ActivityRegister, ActivityUpdate


async def create(db: AsyncSession, activity_register: ActivityRegister) -> ActivityModel:
    db_activity = ActivityModel(**activity_register.model_dump())
    db.add(db_activity)
    await db.commit()
    await db.refresh(db_activity)
    return db_activity


async def get_by_id(db: AsyncSession, activity_id: UUID) -> ActivityModel | None:
    result = await db.execute(select(ActivityModel).where(ActivityModel.id == activity_id))
    return result.scalar_one_or_none()


async def get_by_class_id(db: AsyncSession, course_class_id: UUID) -> list[ActivityModel]:
    result = await db.execute(
        select(ActivityModel)
        .where(ActivityModel.course_class_id == course_class_id)
        .order_by(ActivityModel.title)
    )
    return list(result.scalars().all())


async def update(db: AsyncSession, activity_id: UUID, activity_update: ActivityUpdate) -> ActivityModel | None:
    db_activity = await get_by_id(db, activity_id)
    if db_activity is None:
        return None
    for key, value in activity_update.model_dump(exclude_unset=True).items():
        setattr(db_activity, key, value)
    await db.commit()
    await db.refresh(db_activity)
    return db_activity


async def delete(db: AsyncSession, activity_id: UUID) -> bool:
    db_activity = await get_by_id(db, activity_id)
    if db_activity is None:
        return False
    await db.delete(db_activity)
    await db.commit()
    return True
