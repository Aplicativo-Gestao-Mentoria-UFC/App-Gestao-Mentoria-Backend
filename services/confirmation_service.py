import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, UTC, timezone

from fastapi import BackgroundTasks, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from repositories import user_repository
from repositories.user_repository import get_user_by_email
from repositories import confirmation_code_repository
from services.email_service import send_confirmation_code
from usr.user_repository import mark_email_as_verified


CONFIRMATION_CODE_EXPIRE_MINUTES = 30
CONFIRMATION_CODE_MAX_ATTEMPTS = 5


def generate_six_digit_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def hash_confirmation_code(user_id, code: str, confirmation_type: str) -> str:
    payload = f"{user_id}:{confirmation_type}:{code}".encode("utf-8")
    secret = settings.JWT_SECRET.encode("utf-8")

    return hmac.new(secret, payload, hashlib.sha256).hexdigest()


def validate_code_format(code: str):
    if not code.isdigit() or len(code) != 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Código inválido ou expirado.",
        )


async def request_confirmation_code(
    db: AsyncSession,
    email: str,
    background_tasks: BackgroundTasks,
    confirmation_type: str = "email_verification",
):
    generic_response = {
        "message": "Se o email estiver cadastrado, enviaremos um código de confirmação."
    }

    user = await get_user_by_email(db, email)

    if not user:
        return generic_response

    raw_code = generate_six_digit_code()
    code_hash = hash_confirmation_code(user.id, raw_code, confirmation_type)

    expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=CONFIRMATION_CODE_EXPIRE_MINUTES
    )

    await confirmation_code_repository.invalidate_active_codes(
        db, user.id, confirmation_type
    )

    await confirmation_code_repository.create_confirmation_code(
        db=db,
        user_id=user.id,
        code_hash=code_hash,
        expires_at=expires_at,
        confirmation_type=confirmation_type,
    )

    background_tasks.add_task(
        send_confirmation_code,
        user.email,
        raw_code,
        confirmation_type,
    )

    return generic_response


async def verify_confirmation_code(
    db: AsyncSession,
    email: str,
    code: str,
    confirmation_type: str = "email_verification",
):
    validate_code_format(code)

    user = await get_user_by_email(db, email)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Código inválido ou expirado.",
        )

    confirmation_code = (
        await confirmation_code_repository.get_latest_active_code_by_user_id(
            db=db,
            user_id=user.id,
            confirmation_type=confirmation_type,
        )
    )

    if not confirmation_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Código inválido ou expirado.",
        )

    if confirmation_code.attempts >= CONFIRMATION_CODE_MAX_ATTEMPTS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Muitas tentativas. Solicite um novo código.",
        )

    code_hash = hash_confirmation_code(user.id, code, confirmation_type)

    if not hmac.compare_digest(code_hash, confirmation_code.code_hash):
        confirmation_code.attempts += 1
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Código inválido ou expirado.",
        )

    try: 
        await confirmation_code_repository.mark_as_confirmed(
            db=db,
            confirmation_code_id=confirmation_code.id,
            commit=False
        )

        await mark_email_as_verified(db=db, user_id=user.id, commit=False)

        await db.commit()

    except Exception:
        await db.rollback()
        raise 

    return {
        "message": f"Confirmação de {confirmation_type} realizada com sucesso!",
        "confirmation_type": confirmation_type,
    }
