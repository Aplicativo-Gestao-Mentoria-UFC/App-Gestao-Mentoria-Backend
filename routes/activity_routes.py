from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core import deps

from schemas.activity_schema import ActivityCreate, ActivityUpdate

from services import activity_service

from services.auth_service import (
    require_teacher_or_monitor_class,
    require_teacher_or_monitor_activity,
    require_class_access,
    require_activity_access,
)


router = APIRouter(
    prefix="/activities",
    tags=["Activities"],
)


@router.post("/class/{course_class_id}")
async def create_activity(
    activity: ActivityCreate,
    db: AsyncSession = Depends(deps.get_session),
    course_class=Depends(require_teacher_or_monitor_class()),
):
    return await activity_service.create(
        db=db,
        activity=activity,
        course_class_id=course_class.id,
    )


@router.get("/class/{course_class_id}")
async def get_class_activities(
    db: AsyncSession = Depends(deps.get_session),
    course_class=Depends(require_class_access()),
):
    return await activity_service.get_by_class_id(
        db=db,
        course_class_id=course_class.id,
    )


@router.get("/{activity_id}")
async def get_activity(
    activity=Depends(require_activity_access()),
):
    return activity


@router.patch("/{activity_id}")
async def update_activity(
    activity: ActivityUpdate,
    db: AsyncSession = Depends(deps.get_session),
    current_activity=Depends(require_teacher_or_monitor_activity()),
):
    return await activity_service.update(
        db=db,
        activity_id=current_activity.id,
        activity=activity,
    )


@router.delete("/{activity_id}")
async def delete_activity(
    db: AsyncSession = Depends(deps.get_session),
    current_activity=Depends(require_teacher_or_monitor_activity()),
):
    return await activity_service.delete(
        db=db,
        activity_id=current_activity.id,
    )