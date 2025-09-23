from fastapi import HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, exceptions
from sqlalchemy.ext.asyncio import AsyncSession
from core.security import get_password_hash, verify_password
from core.config import settings
from core import deps
from repositories.user_repository import get_user_by_email, get_user_by_username
from repositories.user_repository import create_user
from schemas.user_schema import User
from models.__all_models import UserRole

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")


async def authenticate_user(db: AsyncSession, email: str, password: str):
    user = await get_user_by_email(db, email)

    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


async def register_user(db: AsyncSession, username: str, email: str, password: str):
    exists_email = await get_user_by_email(db, email)

    if exists_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Já existe um usuário com esse email!",
        )

    exists_username = await get_user_by_username(db, username)

    if exists_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Já existe um usuário com esse username!",
        )

    hashed_password = get_password_hash(password)
    return await create_user(db, username, email, hashed_password)


async def get_current_user(
    db: AsyncSession = Depends(deps.get_session),
    token: str = Depends(oauth2_scheme),
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Não foi possível validar as credenciais",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=settings.ALGORITHM)
        email = payload.get("sub")
        if email is None:
            raise credentials_exception
    except exceptions.JWTError:
        raise credentials_exception
    user = await get_user_by_email(db, email)
    if user is None:
        raise credentials_exception
    return user

async def require_role(required_role: UserRole, current_user: User = Depends(get_current_user)):
    if current_user.role != required_role.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você não tem permissão para acecessar essa rota",
        )
    return current_user
