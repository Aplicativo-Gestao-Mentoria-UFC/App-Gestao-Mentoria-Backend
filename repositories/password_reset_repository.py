from datetime import datetime

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from models.password_reset_code_model import PasswordResetCodeModel
from models.user_model import UserModel


async def invalidate_active_codes(db: AsyncSession, user_id):
    now = datetime.utcnow()

    await db.execute(
        update(PasswordResetCodeModel)
        .where(PasswordResetCodeModel.user_id == user_id)
        .where(PasswordResetCodeModel.used_at.is_(None))
        .values(used_at=now)
    )

    await db.commit()


async def create_password_reset_code(
    db: AsyncSession,
    user_id,
    code_hash: str,
    expires_at: datetime,
):
    reset_code = PasswordResetCodeModel(
        user_id=user_id,
        code_hash=code_hash,
        expires_at=expires_at,
    )

    db.add(reset_code)
    await db.commit()
    await db.refresh(reset_code)

    return reset_code


async def get_latest_active_code_by_user_id(db: AsyncSession, user_id):
    now = datetime.utcnow()

    result = await db.execute(
        select(PasswordResetCodeModel)
        .where(PasswordResetCodeModel.user_id == user_id)
        .where(PasswordResetCodeModel.used_at.is_(None))
        .where(PasswordResetCodeModel.expires_at > now)
        .order_by(PasswordResetCodeModel.created_at.desc())
    )

    return result.scalars().first()


async def increment_attempts(db: AsyncSession, reset_code: PasswordResetCodeModel):
    reset_code.attempts += 1

    await db.commit()
    await db.refresh(reset_code)

    return reset_code


async def mark_code_as_used(db: AsyncSession, reset_code: PasswordResetCodeModel):
    reset_code.used_at = datetime.now()

    await db.commit()
    await db.refresh(reset_code)

    return reset_code


async def complete_password_reset(
    db: AsyncSession,
    user: UserModel,
    reset_code: PasswordResetCodeModel,
    hashed_password: str,
):
    user.hashed_password = hashed_password
    reset_code.used_at = datetime.now()

    await db.commit()
    await db.refresh(user)

    return user