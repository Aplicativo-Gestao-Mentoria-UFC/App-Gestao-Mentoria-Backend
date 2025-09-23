from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from core.security import get_password_hash
from repositories.user_repository import get_user_by_email, get_user_by_username
from repositories.user_repository import create_user

async def register_user(db: AsyncSession, username: str, email: str, password: str):
    exists_email = await get_user_by_email(db, email)

    if exists_email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Já existe um usuário com esse email!")
    
    exists_username = await get_user_by_username(db, username)

    if exists_username:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Já existe um usuário com esse username!")
    
    hashed_password = get_password_hash(password)
    return await create_user(db, username, email, hashed_password) 