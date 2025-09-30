from operator import or_
from pydoc import text
import re
from models.course_class_model import CourseClassModel
from schemas.course_class_schema import (
    CourseClass,
    CourseClassRegister,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select


async def create(db: AsyncSession, course_class_register: CourseClassRegister):
    course_class = CourseClassModel(
        name=course_class_register.name,
        discipline=course_class_register.discipline,
        teacher_id=course_class_register.teacher_id,
    )

    db.add(course_class)
    await db.commit()
    await db.refresh(course_class)
    return CourseClass.from_orm(course_class)


async def get_teacher_classes(db: AsyncSession, teacher_id: str):
    query = select(CourseClassModel).where(CourseClassModel.teacher_id == teacher_id)
    result = await db.execute(query)
    classes = result.scalars().all()
    return classes


async def get_teacher_classes_by_id(
    db: AsyncSession, teacher_id: str, course_class_id: str
):
    query = select(CourseClassModel).where(
        or_(
            CourseClassModel.teacher_id == teacher_id,
            CourseClassModel.id == course_class_id,
        )
    )

    result = await db.execute(query)
    return result.scalars().first()
