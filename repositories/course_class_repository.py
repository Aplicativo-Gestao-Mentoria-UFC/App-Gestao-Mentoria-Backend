from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.course_class_model import (
    CourseClassModel,
    course_class_monitors,
    course_class_students,
)
from models.user_model import UserModel
from schemas.course_class_schema import CourseClassRegister


def _with_relationships(stmt):
    return stmt.options(
        selectinload(CourseClassModel.activities),
        selectinload(CourseClassModel.monitor),
        selectinload(CourseClassModel.students),
    )


def _apply_filters(stmt, name=None, discipline=None, status=None):
    if name:
        stmt = stmt.where(CourseClassModel.name.ilike(f"%{name}%"))
    if discipline:
        stmt = stmt.where(CourseClassModel.discipline.ilike(f"%{discipline}%"))
    if status:
        stmt = stmt.where(CourseClassModel.status == status)
    return stmt


async def create(db: AsyncSession, course_class: CourseClassRegister) -> CourseClassModel:
    db_class = CourseClassModel(**course_class.model_dump())
    db.add(db_class)
    await db.commit()
    return await get_class_by_id(db, db_class.id)


async def get_teacher_classes(
    db: AsyncSession,
    teacher_id: UUID,
    name: str | None = None,
    discipline: str | None = None,
    status: str | None = None,
    skip: int = 0,
    limit: int = 10,
):
    stmt = select(CourseClassModel).where(CourseClassModel.teacher_id == teacher_id)
    stmt = _apply_filters(stmt, name, discipline, status)
    stmt = _with_relationships(stmt.order_by(CourseClassModel.name).offset(skip).limit(limit))
    result = await db.execute(stmt)
    return list(result.scalars().unique().all())


async def get_student_classes(
    db: AsyncSession,
    student_id: UUID,
    name: str | None = None,
    discipline: str | None = None,
    status: str | None = None,
    skip: int = 0,
    limit: int = 10,
):
    stmt = (
        select(CourseClassModel)
        .join(course_class_students, course_class_students.c.course_class_id == CourseClassModel.id)
        .where(course_class_students.c.student_id == student_id)
    )
    stmt = _apply_filters(stmt, name, discipline, status)
    stmt = _with_relationships(stmt.order_by(CourseClassModel.name).offset(skip).limit(limit))
    result = await db.execute(stmt)
    return list(result.scalars().unique().all())


async def get_monitor_classes(
    db: AsyncSession,
    student_id: UUID,
    name: str | None = None,
    discipline: str | None = None,
    status: str | None = None,
    skip: int = 0,
    limit: int = 10,
):
    stmt = (
        select(CourseClassModel)
        .join(course_class_monitors, course_class_monitors.c.course_class_id == CourseClassModel.id)
        .where(course_class_monitors.c.monitor_id == student_id)
    )
    stmt = _apply_filters(stmt, name, discipline, status)
    stmt = _with_relationships(stmt.order_by(CourseClassModel.name).offset(skip).limit(limit))
    result = await db.execute(stmt)
    return list(result.scalars().unique().all())


async def get_class_by_id(db: AsyncSession, course_class_id: UUID):
    stmt = _with_relationships(
        select(CourseClassModel).where(CourseClassModel.id == course_class_id)
    )
    result = await db.execute(stmt)
    return result.scalars().unique().first()


async def add_monitor(db: AsyncSession, course_class: CourseClassModel, new_monitor: UserModel):
    course_class.monitor.append(new_monitor)
    await db.commit()
    return await get_class_by_id(db, course_class.id)


async def add_student(db: AsyncSession, course_class: CourseClassModel, new_student: UserModel):
    course_class.students.append(new_student)
    await db.commit()
    return await get_class_by_id(db, course_class.id)


async def remove_monitor(db: AsyncSession, course_class: CourseClassModel, monitor: UserModel):
    course_class.monitor.remove(monitor)
    await db.commit()
    return await get_class_by_id(db, course_class.id)


async def remove_student(db: AsyncSession, course_class: CourseClassModel, student: UserModel):
    course_class.students.remove(student)
    await db.commit()
    return await get_class_by_id(db, course_class.id)


async def is_teacher_of_class(db: AsyncSession, user_id: UUID, course_class_id: UUID) -> bool:
    result = await db.execute(
        select(CourseClassModel.id).where(
            CourseClassModel.id == course_class_id,
            CourseClassModel.teacher_id == user_id,
        )
    )
    return result.scalar_one_or_none() is not None


async def is_monitor_of_class(db: AsyncSession, user_id: UUID, course_class_id: UUID) -> bool:
    result = await db.execute(
        select(course_class_monitors.c.course_class_id).where(
            course_class_monitors.c.course_class_id == course_class_id,
            course_class_monitors.c.monitor_id == user_id,
        )
    )
    return result.scalar_one_or_none() is not None


async def is_student_of_class(db: AsyncSession, user_id: UUID, course_class_id: UUID) -> bool:
    result = await db.execute(
        select(course_class_students.c.course_class_id).where(
            course_class_students.c.course_class_id == course_class_id,
            course_class_students.c.student_id == user_id,
        )
    )
    return result.scalar_one_or_none() is not None


async def has_class_write_permission(db: AsyncSession, user_id: UUID, course_class_id: UUID) -> bool:
    return await is_teacher_of_class(db, user_id, course_class_id) or await is_monitor_of_class(
        db, user_id, course_class_id
    )


async def has_class_read_permission(db: AsyncSession, user_id: UUID, course_class_id: UUID) -> bool:
    return (
        await is_teacher_of_class(db, user_id, course_class_id)
        or await is_monitor_of_class(db, user_id, course_class_id)
        or await is_student_of_class(db, user_id, course_class_id)
    )
