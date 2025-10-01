import uuid
from fastapi import APIRouter, Depends

from core import deps
from schemas.course_class_schema import AddMonitorSchema, CourseClassBase
from schemas.user_schema import User
from services import course_class_service
from services.auth_service import require_role
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
):
    return await course_class_service.get_classes(db, current_user.id)


@router.get("/my-classes/{course_class_id}")
async def get_teacher_class_by_id(
    course_class_id: str,
    db: AsyncSession = Depends(deps.get_session),
    current_user: User = Depends(require_role("TEACHER")),
):
    return await course_class_service.get_classes(db, current_user.id, course_class_id)


@router.patch("/my-classes/{course_class_id}/add-monitor")
async def add_monitor(
    course_class_id: str,
    data: AddMonitorSchema,
    db: AsyncSession = Depends(deps.get_session),
    current_user: User = Depends(require_role("TEACHER")),
):
    return await course_class_service.add_monitor(
        course_class_id, data.email, db, current_user.id
    )
