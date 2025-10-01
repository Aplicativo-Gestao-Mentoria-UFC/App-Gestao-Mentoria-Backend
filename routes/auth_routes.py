from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from schemas.user_schema import UserCreate, User
from schemas.token import Token
from services.auth_service import (
    authenticate_user,
    register_user,
    get_current_user,
    require_role,
)
from core import deps
from core.config import settings
from core.security import create_access_token
from models.__all_models import UserRole


router = APIRouter(prefix="/auth")


@router.post("/register")
async def register(user: UserCreate, db: AsyncSession = Depends(deps.get_session)):
    return await register_user(db, user.username, user.email, user.role, user.password)


@router.post("/token")
async def login_for_access_token(
    db: AsyncSession = Depends(deps.get_session),
    form_data: OAuth2PasswordRequestForm = Depends(),
) -> Token:
    user = await authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha incorretos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return Token(access_token=access_token, token_type="bearer")


@router.get("/me", response_model=User)
async def read_me(current_user: User = Depends(require_role("TEACHER"))):
    return current_user
