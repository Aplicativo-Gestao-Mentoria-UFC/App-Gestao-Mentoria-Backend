from models.course_class_model import (
    CourseClassModel,
    course_class_students,
    course_class_monitors,
)
from models.user_model import UserModel
from schemas.course_class_schema import (
    CourseClass,
    CourseClassRegister,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload


async def create(db: AsyncSession, course_class_register: CourseClassRegister):
    course_class = CourseClassModel(
        name=course_class_register.name,
        discipline=course_class_register.discipline,
        teacher_id=course_class_register.teacher_id,
    )

    db.add(course_class)
    await db.commit()
    await db.refresh(course_class)
    return course_class


async def get_teacher_classes(
    db: AsyncSession,
    teacher_id: str,
    name=None,
    discipline=None,
    status=None,
    skip: int = 0,
    limit: int = 10,
):
    query = select(CourseClassModel).where(CourseClassModel.teacher_id == teacher_id)

    if name:
        query = query.where(CourseClassModel.name.ilike(f"%{name}%"))

    if discipline:
        query = query.where(CourseClassModel.discipline.ilike(f"%{discipline}%"))

    if status:
        query = query.where(CourseClassModel.status == status)

    result = await db.execute(query.offset(skip).limit(limit))
    classes = result.scalars().all()
    return classes


async def get_monitor_classes(
    db: AsyncSession,
    student_id: str,
    name=None,
    discipline=None,
    status=None,
    skip: int = 0,
    limit: int = 10,
):
    query = (
        select(CourseClassModel)
        .join(course_class_monitors)
        .where(course_class_monitors.c.monitor_id == student_id)
    )

    if name:
        query = query.where(CourseClassModel.name.ilike(f"%{name}%"))

    if discipline:
        query = query.where(CourseClassModel.discipline.ilike(f"%{discipline}%"))

    if status:
        query = query.where(CourseClassModel.status == status)

    result = await db.execute(query.offset(skip).limit(limit))
    classes = result.scalars().all()
    return classes


async def get_student_classes(
    db: AsyncSession,
    student_id: str,
    name=None,
    discipline=None,
    status=None,
    skip: int = 0,
    limit: int = 10,
):
    query = (
        select(CourseClassModel)
        .join(course_class_students)
        .where(course_class_students.c.student_id == student_id)
    )

    if name:
        query = query.where(CourseClassModel.name.ilike(f"%{name}%"))

    if discipline:
        query = query.where(CourseClassModel.discipline.ilike(f"%{discipline}%"))

    if status:
        query = query.where(CourseClassModel.status == status)

    result = await db.execute(query.offset(skip).limit(limit))
    classes = result.scalars().all()
    return classes


async def get_class_by_id(db: AsyncSession, course_class_id: str):
    query = (
        select(CourseClassModel)
        .options(
            selectinload(CourseClassModel.activities),
            selectinload(CourseClassModel.monitor),
            selectinload(CourseClassModel.students),
        )
        .where(CourseClassModel.id == course_class_id)
    )

    result = await db.execute(query)
    course_class = result.scalars().first()

    return course_class


async def add_monitor(
    db: AsyncSession,
    course_class: CourseClassModel,
    new_monitor: UserModel,
):
    course_class.monitor.append(new_monitor)
    await db.commit()
    await db.refresh(course_class)
    return course_class


async def add_student(
    db: AsyncSession,
    course_class: CourseClassModel,
    new_student: UserModel,
):
    course_class.students.append(new_student)

    await db.commit()
    await db.refresh(course_class)
    return course_class


async def remove_monitor(
    db: AsyncSession, course_class: CourseClassModel, monitor: UserModel
):
    course_class.monitor.remove(monitor)

    await db.commit()
    await db.refresh(course_class)
    return course_class


async def remove_student(
    db: AsyncSession, course_class: CourseClassModel, student: UserModel
):
    course_class.students.remove(student)

    await db.commit()
    await db.refresh(course_class)
    return course_class
