from sqlalchemy.ext.asyncio import AsyncSession
from schemas.activity_schema import ActivityBase, ActivityRegister
from fastapi import HTTPException, status
from repositories import activity_repository


async def create(db: AsyncSession, activity: ActivityBase, course_class_id: str):
    activity_register = ActivityRegister(
        title=activity.title,
        description=activity.description,
        fileUrl=getattr(activity, "fileUrl", None),
        course_class_id=course_class_id,
    )

    try:
        return await activity_repository.create(db, activity_register)
    except Exception as e:
        print(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor",
        )


async def update(db: AsyncSession, activity_id: str, activity: ActivityBase):
    try:
        updated = await activity_repository.update(db, activity_id, activity)
        if not updated:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Atividade não encontrada"
            )
        return updated
    except HTTPException:
        raise
    except Exception as e:
        print(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor",
        )


async def delete(db: AsyncSession, activity_id: str):
    try:
        deleted = await activity_repository.delete(db, activity_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Atividade não encontrada"
            )
        return {"detail": "Atividade excluída"}
    except HTTPException:
        raise
    except Exception as e:
        print(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor",
        )
