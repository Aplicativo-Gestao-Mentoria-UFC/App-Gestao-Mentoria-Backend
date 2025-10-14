from sqlalchemy.ext.asyncio import AsyncSession
from schemas.activity_schema import ActivityRegister
from models.activity_model import ActivityModel


async def create(db: AsyncSession, activity_register: ActivityRegister):
    activity = ActivityModel(
        title=activity_register.title,
        description=activity_register.description,
        course_class_id=activity_register.course_class_id,
    )

    db.add(activity)
    await db.commit()
    await db.refresh(activity)
    return activity
