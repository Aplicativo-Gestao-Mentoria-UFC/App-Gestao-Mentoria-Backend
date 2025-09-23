from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from schemas import user_schema
from services import auth_service
from core import deps

router = APIRouter(prefix="/auth")

@router.post("/register")
async def register(user: user_schema.UserCreate, db: AsyncSession = Depends(deps.get_session)):
    return await auth_service.register_user(db , user.username, user.email, user.password)