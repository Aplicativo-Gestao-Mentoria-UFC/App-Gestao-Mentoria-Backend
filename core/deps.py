from fastapi import status
from multiprocessing import Value
from typing import AsyncGenerator
from uuid import UUID
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from core.database import Session


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    session: AsyncSession = Session()

    try:
        yield session
    finally:
        await session.close()


def validate_uuid(id: str) -> UUID:
    try:
        return UUID(id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ID inválido, deve ser um UUID válido",
        )
