import logging

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from repositories import activity_repository

from schemas.activity_schema import (
    ActivityCreate,
    ActivityRegister,
    ActivityUpdate,
)


logger = logging.getLogger(__name__)


async def create(
    db: AsyncSession,
    activity: ActivityCreate,
    course_class_id: UUID,
):
    activity_register = ActivityRegister(
        title=activity.title,
        description=activity.description,
        fileUrl=activity.fileUrl,
        course_class_id=course_class_id,
    )

    try:
        return await activity_repository.create(
            db=db,
            activity_register=activity_register,
        )

    except Exception:
        logger.exception("Erro ao criar atividade")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor",
        )


async def get_by_id(
    db: AsyncSession,
    activity_id: UUID,
):
    activity = await activity_repository.get_by_id(
        db=db,
        activity_id=activity_id,
    )

    if activity is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Atividade não encontrada",
        )

    return activity


async def get_by_class_id(
    db: AsyncSession,
    course_class_id: UUID,
):
    return await activity_repository.get_by_class_id(
        db=db,
        course_class_id=course_class_id,
    )


async def update(
    db: AsyncSession,
    activity_id: UUID,
    activity: ActivityUpdate,
):
    try:
        updated = await activity_repository.update(
            db=db,
            activity_id=activity_id,
            activity_update=activity,
        )

        if updated is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Atividade não encontrada",
            )

        return updated

    except HTTPException:
        raise

    except Exception:
        logger.exception("Erro ao atualizar atividade")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor",
        )


async def delete(
    db: AsyncSession,
    activity_id: UUID,
):
    try:
        deleted = await activity_repository.delete(
            db=db,
            activity_id=activity_id,
        )

        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Atividade não encontrada",
            )

        return {"detail": "Atividade excluída"}

    except HTTPException:
        raise

    except Exception:
        logger.exception("Erro ao excluir atividade")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor",
        )