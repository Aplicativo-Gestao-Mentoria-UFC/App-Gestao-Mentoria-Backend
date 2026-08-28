from datetime import UTC, datetime, timezone
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.confirmation_code_model import ConfirmationCodeModel


async def create_confirmation_code(
    db: AsyncSession,
    user_id: uuid.UUID,
    code_hash: str,
    expires_at: datetime,
    confirmation_type: str = "email_verification",
):
    confirmation_code = ConfirmationCodeModel(
        user_id=user_id,
        code_hash=code_hash,
        expires_at=expires_at,
        confirmation_type=confirmation_type,
    )

    db.add(confirmation_code)
    await db.commit()
    await db.refresh(confirmation_code)
    return confirmation_code


async def get_latest_active_code_by_user_id(
    db: AsyncSession,
    user_id: uuid.UUID,
    confirmation_type: str = "email_verification",
):
    stmt = select(ConfirmationCodeModel).where(
        (ConfirmationCodeModel.user_id == user_id)
        & (ConfirmationCodeModel.confirmation_type == confirmation_type)
        & (ConfirmationCodeModel.expires_at > datetime.now(timezone.utc))
        & (ConfirmationCodeModel.confirmed_at.is_(None))
    )

    result = await db.execute(stmt)
    return result.scalars().first()


async def invalidate_active_codes(
    db: AsyncSession,
    user_id: uuid.UUID,
    confirmation_type: str = "email_verification",
):
    stmt = select(ConfirmationCodeModel).where(
        (ConfirmationCodeModel.user_id == user_id)
        & (ConfirmationCodeModel.confirmation_type == confirmation_type)
        & (ConfirmationCodeModel.confirmed_at.is_(None))
    )

    result = await db.execute(stmt)
    codes = result.scalars().all()

    for code in codes:
        code.expires_at = datetime.now(timezone.utc)

    await db.commit()


async def mark_as_confirmed(
    db: AsyncSession,
    confirmation_code_id: uuid.UUID,
    commit: bool = True,
):
    code = await db.get(ConfirmationCodeModel, confirmation_code_id)

    if not code:
        return None
    
    code.confirmed_at = datetime.now(timezone.utc)

    if(commit):
        await db.commit()
        await db.refresh(code)

    else:
        await db.flush()

    return code
