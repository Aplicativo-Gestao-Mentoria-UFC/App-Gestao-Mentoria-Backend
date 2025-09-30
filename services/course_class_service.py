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
