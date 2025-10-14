from sqlalchemy.ext.asyncio import AsyncSession
from schemas.activity_schema import ActivityBase, ActivityRegister
from fastapi import HTTPException, status
from repositories import activity_repository


async def create(db: AsyncSession, activity: ActivityBase, course_class_id: str):
    activity_register = ActivityRegister(
        title=activity.title,
        description=activity.description,
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
