from typing import Optional
from fastapi import APIRouter, Depends
from services.auth_service import require_role, require_monitor_class
from sqlalchemy.ext.asyncio import AsyncSession
from core import deps
from schemas.user_schema import User
from schemas.course_class_schema import CourseClass
from services import course_class_service

router = APIRouter(prefix="/monitor", dependencies=[Depends(require_role("STUDENT"))])


@router.get("/my-classes")
async def get_classes(
    db: AsyncSession = Depends(deps.get_session),
    current_user: User = Depends(require_role("STUDENT")),
    name: Optional[str] = None,
    discipline: Optional[str] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 10,
):
    return await course_class_service.get_monitor_classes(
        db,
        current_user.id,
        name=name,
        discipline=discipline,
        status=status,
        skip=skip,
        limit=limit,
    )


@router.get("/my-classes/{course_class_id}")
async def get_monitor_class_by_id(
    course_class: CourseClass = Depends(require_monitor_class()),
):
    return CourseClass.from_orm(course_class)
