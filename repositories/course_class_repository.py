from calendar import c
from models.course_class_model import CourseClassModel
from schemas.course_class_schema import (
    CourseClass,
    CourseClassBase,
    CourseClassRegister,
)
from sqlalchemy.ext.asyncio import AsyncSession


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
