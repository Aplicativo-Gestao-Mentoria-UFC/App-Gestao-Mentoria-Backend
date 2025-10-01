from typing import Optional
from repositories import course_class_repository
from schemas.course_class_schema import CourseClassBase, CourseClassRegister
from sqlalchemy.ext.asyncio import AsyncSession


async def create(db: AsyncSession, course_class: CourseClassBase, teacher_id: str):
    course_class_register = CourseClassRegister(
        name=course_class.name,
        discipline=course_class.discipline,
        teacher_id=teacher_id,
    )
    return await course_class_repository.create(db, course_class_register)


async def get_classes(
    db: AsyncSession, teacher_id: str, course_class_id: Optional[str] = None
):
    if course_class_id is None:
        return await course_class_repository.get_teacher_classes(db, teacher_id)
    else:
        return await course_class_repository.get_teacher_class_by_id(
            db, teacher_id, course_class_id
        )
