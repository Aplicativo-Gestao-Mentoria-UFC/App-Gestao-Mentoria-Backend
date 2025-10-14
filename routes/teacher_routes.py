from typing import Optional
from fastapi import APIRouter, Depends

from core import deps
from schemas.course_class_schema import (
    AddStudentSchema,
    CourseClass,
    CourseClassBase,
    RemoveStudentSchema,
)
from schemas.user_schema import User
from schemas.activity_schema import ActivityBase
from services import course_class_service, activity_service
from services.auth_service import require_role, require_teacher_class
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/teacher", dependencies=[Depends(require_role("TEACHER"))])


@router.post("/register-class")
async def register_class(
    course_class: CourseClassBase,
    db: AsyncSession = Depends(deps.get_session),
    current_user: User = Depends(require_role("TEACHER")),
):
    return await course_class_service.create(db, course_class, current_user.id)


@router.get("/my-classes")
async def get_classes(
    db: AsyncSession = Depends(deps.get_session),
    current_user: User = Depends(require_role("TEACHER")),
    name: Optional[str] = None,
    discipline: Optional[str] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 10,
):
    return await course_class_service.get_classes(
        db,
        current_user.id,
        name=name,
        discipline=discipline,
        status=status,
        skip=skip,
        limit=limit,
    )


@router.get("/my-classes/{course_class_id}")
async def get_teacher_class_by_id(
    course_class_id: str,
    db: AsyncSession = Depends(deps.get_session),
    current_user: User = Depends(require_role("TEACHER")),
):
    return await course_class_service.get_classes(db, current_user.id, course_class_id)


@router.put("/my-classes/{course_class_id}/add-monitor")
async def add_monitor(
    data: AddStudentSchema,
    course_class: CourseClass = Depends(require_teacher_class()),
    db: AsyncSession = Depends(deps.get_session),
):
    return await course_class_service.add_monitor(
        course_class,
        data.email,
        db,
    )


@router.patch("/my-classes/{course_class_id}/remove-monitor")
async def remove_monitor(
    data: RemoveStudentSchema,
    course_class: CourseClass = Depends(require_teacher_class()),
    db: AsyncSession = Depends(deps.get_session),
):
    monitor_id = deps.validate_uuid(data.student_id)
    return await course_class_service.remove_monitor(course_class, monitor_id, db)


@router.put("/my-classes/{course_class_id}/add-student")
async def add_student(
    data: AddStudentSchema,
    course_class: CourseClass = Depends(require_teacher_class()),
    db: AsyncSession = Depends(deps.get_session),
):
    return await course_class_service.add_student(course_class, data.email, db)


@router.patch("/my-classes/{course_class_id}/remove-student")
async def remove_student(
    data: RemoveStudentSchema,
    course_class: CourseClass = Depends(require_teacher_class()),
    db: AsyncSession = Depends(deps.get_session),
):
    student_id = deps.validate_uuid(data.student_id)
    return await course_class_service.remove_student(course_class, student_id, db)


@router.post("/my-classes/{course_class_id}/add-activity")
async def add_activity(
    activity: ActivityBase,
    course_class: CourseClass = Depends(require_teacher_class()),
    db: AsyncSession = Depends(deps.get_session),
):
    return await activity_service.create(db, activity, course_class.id)
