from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.professor_signup_verification_model import (
    ProfessorSignupVerificationModel,
)

async def create(
    db: AsyncSession,
    email: str,
    code_hash: str,
    expires_at: datetime,
):
    verification = ProfessorSignupVerificationModel(
        email=email,
        code_hash=code_hash,
        expires_at=expires_at,
    )

    db.add(verification)
    await db.flush()

    return verification


async def get_latest_active_by_email(
    db: AsyncSession,
    email: str,
):
    now = datetime.now(UTC)

    stmt = (
        select(ProfessorSignupVerificationModel)
        .where(
            ProfessorSignupVerificationModel.email == email,
            ProfessorSignupVerificationModel.expires_at > now,
            ProfessorSignupVerificationModel.verified_at.is_(None),
        )
        .order_by(
            ProfessorSignupVerificationModel.created_at.desc()
        )
        .limit(1)
    )

    result = await db.execute(stmt)

    return result.scalars().first()


async def get_by_id(
    db: AsyncSession,
    verification_id: UUID,
):
    return await db.get(
        ProfessorSignupVerificationModel,
        verification_id,
    )


async def invalidate_active_codes(
    db: AsyncSession,
    email: str,
):
    now = datetime.now(UTC)

    stmt = select(
        ProfessorSignupVerificationModel
    ).where(
        ProfessorSignupVerificationModel.email == email,
        ProfessorSignupVerificationModel.expires_at > now,
        ProfessorSignupVerificationModel.verified_at.is_(None),
    )

    result = await db.execute(stmt)

    verifications = result.scalars().all()

    for verification in verifications:
        verification.expires_at = now

    await db.flush()


async def increment_attempts(
    db: AsyncSession,
    verification: ProfessorSignupVerificationModel,
):
    verification.attempts += 1
    await db.flush()


async def mark_as_verified(
    db: AsyncSession,
    verification: ProfessorSignupVerificationModel,
):
    verification.verified_at = datetime.now(UTC)
    await db.flush()


async def mark_as_completed(
    db: AsyncSession,
    verification: ProfessorSignupVerificationModel,
):
    verification.completed_at = datetime.now(UTC)
    await db.flush()


