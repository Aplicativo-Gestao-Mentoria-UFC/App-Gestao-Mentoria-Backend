import logging
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from repositories import activity_repository
from schemas.activity_schema import ActivityCreate, ActivityRegister, ActivityUpdate

logger = logging.getLogger(__name__)


async def create(db: AsyncSession, activity: ActivityCreate, course_class_id: UUID):
    try:
        return await activity_repository.create(
            db=db,
            activity_register=ActivityRegister(
                title=activity.title,
                description=activity.description,
                fileUrl=activity.fileUrl,
                course_class_id=course_class_id,
            ),
        )
    except Exception:
        logger.exception("Erro ao criar atividade")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")


async def get_by_id(db: AsyncSession, activity_id: UUID):
    activity = await activity_repository.get_by_id(db, activity_id)
    if activity is None:
        raise HTTPException(status_code=404, detail="Atividade não encontrada")
    return activity


async def get_by_class_id(db: AsyncSession, course_class_id: UUID):
    return await activity_repository.get_by_class_id(db, course_class_id)


async def update(db: AsyncSession, activity_id: UUID, activity: ActivityUpdate):
    updated = await activity_repository.update(db, activity_id, activity)
    if updated is None:
        raise HTTPException(status_code=404, detail="Atividade não encontrada")
    return updated


async def delete(db: AsyncSession, activity_id: UUID):
    if not await activity_repository.delete(db, activity_id):
        raise HTTPException(status_code=404, detail="Atividade não encontrada")
    return {"detail": "Atividade excluída"}
