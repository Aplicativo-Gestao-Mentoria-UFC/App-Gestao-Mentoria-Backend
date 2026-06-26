from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core import deps
from schemas.activity_schema import ActivityBase
from services import activity_service
from services.auth_service import require_monitor_class, require_role

router = APIRouter(prefix="/activities", dependencies=[Depends()])

async def create_activity(
    activity: ActivityBase,
    db: AsyncSession = Depends(deps.get_session),
    permission: Depends(require_monitor_class()),
):
    return await activity_service.create(db, activity)

@router.patch("/{activity_id}")
async def update_activity(
    activity_id: str,
    activity: ActivityBase,
    db: AsyncSession = Depends(deps.get_session),
):
    return await activity_service.update(db, activity_id, activity)


@router.delete("/{activity_id}")
async def delete_activity(
    activity_id: str, db: AsyncSession = Depends(deps.get_session)
):
    return await activity_service.delete(db, activity_id)
