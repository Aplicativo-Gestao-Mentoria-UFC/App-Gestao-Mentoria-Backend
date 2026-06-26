from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.activity_model import ActivityModel
from models.course_class_model import CourseClassModel
from schemas.activity_schema import ActivityRegister, ActivityUpdate


async def create(
    db: AsyncSession,
    activity: ActivityRegister,
) -> ActivityModel:
    db_activity = ActivityModel(**activity.model_dump())

    db.add(db_activity)
    await db.commit()
    await db.refresh(db_activity)

    return db_activity


async def get_by_id(
    db: AsyncSession,
    activity_id: UUID,
) -> ActivityModel | None:
    result = await db.execute(
        select(ActivityModel).where(ActivityModel.id == activity_id)
    )

    return result.scalar_one_or_none()


async def get_by_class_id(
    db: AsyncSession,
    course_class_id: UUID,
) -> list[ActivityModel]:
    result = await db.execute(
        select(ActivityModel)
        .where(ActivityModel.course_class_id == course_class_id)
        .order_by(ActivityModel.title)
    )

    return list(result.scalars().all())


async def update(
    db: AsyncSession,
    activity_id: UUID,
    activity: ActivityUpdate,
) -> ActivityModel | None:
    db_activity = await get_by_id(db, activity_id)

    if db_activity is None:
        return None

    data = activity.model_dump(exclude_unset=True)

    for key, value in data.items():
        setattr(db_activity, key, value)

    await db.commit()
    await db.refresh(db_activity)

    return db_activity


async def delete(
    db: AsyncSession,
    activity_id: UUID,
) -> bool:
    db_activity = await get_by_id(db, activity_id)

    if db_activity is None:
        return False

    await db.delete(db_activity)
    await db.commit()

    return True

async def is_teacher_of_class(
    db: AsyncSession,
    user_id: UUID,
    course_class_id: UUID,
) -> bool:
    query = select(CourseClassModel.id).where(
        CourseClassModel.id == course_class_id,
        CourseClassModel.teacher_id == user_id,
    )

    result = await db.execute(query)

    return result.scalar_one_or_none() is not None


async def is_monitor_of_class(
    db: AsyncSession,
    user_id: UUID,
    course_class_id: UUID,
) -> bool:
    query = select(course_class_monitors.c.course_class_id).where(
        course_class_monitors.c.course_class_id == course_class_id,
        course_class_monitors.c.monitor_id == user_id,
    )

    result = await db.execute(query)

    return result.scalar_one_or_none() is not None


async def is_student_of_class(
    db: AsyncSession,
    user_id: UUID,
    course_class_id: UUID,
) -> bool:
    query = select(course_class_students.c.course_class_id).where(
        course_class_students.c.course_class_id == course_class_id,
        course_class_students.c.student_id == user_id,
    )

    result = await db.execute(query)

    return result.scalar_one_or_none() is not None


async def has_class_write_permission(
    db: AsyncSession,
    user_id: UUID,
    course_class_id: UUID,
) -> bool:
    is_teacher = await is_teacher_of_class(
        db=db,
        user_id=user_id,
        course_class_id=course_class_id,
    )

    if is_teacher:
        return True

    is_monitor = await is_monitor_of_class(
        db=db,
        user_id=user_id,
        course_class_id=course_class_id,
    )

    return is_monitor


async def has_class_read_permission(
    db: AsyncSession,
    user_id: UUID,
    course_class_id: UUID,
) -> bool:
    is_teacher = await is_teacher_of_class(
        db=db,
        user_id=user_id,
        course_class_id=course_class_id,
    )

    if is_teacher:
        return True

    is_monitor = await is_monitor_of_class(
        db=db,
        user_id=user_id,
        course_class_id=course_class_id,
    )

    if is_monitor:
        return True

    is_student = await is_student_of_class(
        db=db,
        user_id=user_id,
        course_class_id=course_class_id,
    )

    return is_student