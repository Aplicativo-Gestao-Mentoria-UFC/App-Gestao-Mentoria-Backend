from datetime import datetime, UTC
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import SQLAlchemyError

from models.__all_models import UserModel, UserRole
from schemas.user_schema import User


async def get_user_by_id(db: AsyncSession, user_id: UUID):
    result = await db.execute(select(UserModel).filter_by(id=user_id))
    return result.scalars().first()


async def get_user_by_username(db: AsyncSession, username: str):
    result = await db.execute(select(UserModel).filter_by(username=username))
    return result.scalars().first()


async def get_user_by_email(db: AsyncSession, email: str):
    result = await db.execute(select(UserModel).filter_by(email=email))
    return result.scalars().first()


async def create_user(
    db: AsyncSession,
    username: str,
    email: str,
    role: UserRole,
    hashed_password: str,
):
    user = UserModel(
        username=username,
        email=email,
        role=role,
        hashed_password=hashed_password,
    )

    db.add(user)

    try:
        await db.commit()
        await db.refresh(user)
        return User.model_validate(user)
    
    except SQLAlchemyError:
        await db.rollback()
        raise

async def update_user_password(
    db: AsyncSession,
    user: UserModel,
    hashed_password: str,
):
    setattr(user, "hashed_password", hashed_password)

    await db.commit()
    await db.refresh(user)

    return user


async def mark_email_as_verified(db: AsyncSession, user_id: UUID, commit: bool = True):
    user = await get_user_by_id(db, user_id)

    if not user:
        raise ValueError("User not found")

    setattr(user, "email_verified_at", datetime.now(UTC))

    if commit:
        await db.commit()
        await db.refresh(user)

    return user


async def create_verified_teacher(
    db: AsyncSession,
    username: str,
    email: str,
    hashed_password: str,
):
    user = UserModel(
        username=username,
        email=email,
        role=UserRole.teacher.value,
        hashed_password=hashed_password,
        email_verified_at=datetime.now(UTC),
    )

    db.add(user)
    await db.flush()

    return user