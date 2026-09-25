from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core import deps
from schemas.activity_schema import Activity, ActivityCreate, ActivityUpdate
from services import activity_service
from services.auth_service import (
    require_activity_access,
    require_class_access,
    require_teacher_or_monitor_activity,
    require_teacher_or_monitor_class,
)

router = APIRouter(prefix="/activities")


@router.post("/class/{course_class_id}", response_model=Activity, summary="Criar atividade na turma")
async def create_activity(
    activity: ActivityCreate,
    db: AsyncSession = Depends(deps.get_session),
    course_class=Depends(require_teacher_or_monitor_class()),
):
    return await activity_service.create(db, activity, course_class.id)


@router.get("/class/{course_class_id}", response_model=list[Activity], summary="Listar atividades da turma")
async def get_class_activities(
    db: AsyncSession = Depends(deps.get_session),
    course_class=Depends(require_class_access()),
):
    return await activity_service.get_by_class_id(db, course_class.id)


@router.get("/{activity_id}", response_model=Activity, summary="Detalhar atividade")
async def get_activity(activity=Depends(require_activity_access())):
    return activity


@router.patch("/{activity_id}", response_model=Activity, summary="Atualizar atividade")
async def update_activity(
    activity: ActivityUpdate,
    db: AsyncSession = Depends(deps.get_session),
    current_activity=Depends(require_teacher_or_monitor_activity()),
):
    return await activity_service.update(db, current_activity.id, activity)


@router.delete("/{activity_id}", summary="Excluir atividade")
async def delete_activity(
    db: AsyncSession = Depends(deps.get_session),
    current_activity=Depends(require_teacher_or_monitor_activity()),
):
    return await activity_service.delete(db, current_activity.id)
