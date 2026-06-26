import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from schemas.activity_schema import ActivityRegister, ActivityBase
from models.activity_model import ActivityModel


async def create(db: AsyncSession, activity_register: ActivityRegister):
    activity = ActivityModel(
        title=activity_register.title,
        description=activity_register.description,
        fileUrl=activity_register.fileUrl,
        course_class_id=activity_register.course_class_id,
    )

    db.add(activity)
    await db.commit()
    await db.refresh(activity)
    return activity


async def update(db: AsyncSession, activity_id: str, activity_data: ActivityRegister | ActivityBase):
    try:
        activity_uuid = uuid.UUID(str(activity_id))
    except Exception:
        return None
    activity = await db.get(ActivityModel, activity_uuid)
    if not activity:
        return None
    activity.title = activity_data.title
    activity.description = activity_data.description
    # allow both ActivityRegister and ActivityBase which may have fileUrl
    activity.fileUrl = getattr(activity_data, "fileUrl", None)
    await db.commit()
    await db.refresh(activity)
    return activity


async def delete(db: AsyncSession, activity_id: str):
    try:
        activity_uuid = uuid.UUID(str(activity_id))
    except Exception:
        return False
    activity = await db.get(ActivityModel, activity_uuid)
    if not activity:
        return False
    await db.delete(activity)
    await db.commit()
    return True
