from typing import Optional
from fastapi import APIRouter, Depends
from services.auth_service import require_role
from sqlalchemy.ext.asyncio import AsyncSession
from core import deps
from schemas.user_schema import User
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
