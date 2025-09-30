from fastapi import APIRouter, Depends

from core import deps
from schemas.course_class_schema import CourseClassBase
from schemas.user_schema import User
from services import course_class_service
from services.auth_service import require_role
from sqlalchemy.ext.asyncio import AsyncSession


router = APIRouter(prefix="/teacher", dependencies=[Depends(require_role("ADMIN"))])


@router.post("/register-class")
async def register_class(
    course_class: CourseClassBase,
    db: AsyncSession = Depends(deps.get_session),
    current_user: User = Depends(require_role("ADMIN")),
):
    return await course_class_service.create(db, course_class, current_user.id)


@router.get("/my-classes")
async def get_classes(
    db: AsyncSession = Depends(deps.get_session),
    current_user: User = Depends(require_role("ADMIN")),
):
    return await course_class_service.get_classes(db, current_user.id)
