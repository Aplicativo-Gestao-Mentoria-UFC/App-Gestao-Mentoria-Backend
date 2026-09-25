import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta

from fastapi import BackgroundTasks, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from repositories import confirmation_code_repository
from repositories.user_repository import get_user_by_email, mark_email_as_verified
from services.email_service import safe_send_confirmation_code

CONFIRMATION_CODE_EXPIRE_MINUTES = 30
CONFIRMATION_CODE_MAX_ATTEMPTS = 5


def generate_six_digit_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def hash_confirmation_code(user_id, code: str, confirmation_type: str) -> str:
    payload = f"{user_id}:{confirmation_type}:{code}".encode("utf-8")
    return hmac.new(settings.JWT_SECRET.encode(), payload, hashlib.sha256).hexdigest()


async def request_confirmation_code(
    db: AsyncSession,
    email: str,
    background_tasks: BackgroundTasks,
    confirmation_type: str = "email_verification",
):
    generic_response = {
        "message": "Se o email estiver cadastrado, enviaremos um código de confirmação."
    }
    user = await get_user_by_email(db, email.strip().lower())
    if not user or (confirmation_type == "email_verification" and user.email_verified_at is not None):
        return generic_response

    raw_code = generate_six_digit_code()
    code_hash = hash_confirmation_code(user.id, raw_code, confirmation_type)
    expires_at = datetime.now(UTC) + timedelta(minutes=CONFIRMATION_CODE_EXPIRE_MINUTES)

    await confirmation_code_repository.invalidate_active_codes(db, user.id, confirmation_type)
    await confirmation_code_repository.create_confirmation_code(
        db=db,
        user_id=user.id,
        code_hash=code_hash,
        expires_at=expires_at,
        confirmation_type=confirmation_type,
    )
    background_tasks.add_task(
        safe_send_confirmation_code,
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
    user = await get_user_by_email(db, email.strip().lower())
    if not user:
        raise HTTPException(status_code=400, detail="Código inválido ou expirado.")

    confirmation_code = await confirmation_code_repository.get_latest_active_code_by_user_id(
        db=db,
        user_id=user.id,
        confirmation_type=confirmation_type,
    )
    if not confirmation_code:
        raise HTTPException(status_code=400, detail="Código inválido ou expirado.")
    if confirmation_code.attempts >= CONFIRMATION_CODE_MAX_ATTEMPTS:
        raise HTTPException(status_code=429, detail="Muitas tentativas. Solicite um novo código.")

    code_hash = hash_confirmation_code(user.id, code, confirmation_type)
    if not hmac.compare_digest(code_hash, confirmation_code.code_hash):
        confirmation_code.attempts += 1
        await db.commit()
        raise HTTPException(status_code=400, detail="Código inválido ou expirado.")

    try:
        await confirmation_code_repository.mark_as_confirmed(
            db=db,
            confirmation_code_id=confirmation_code.id,
            commit=False,
        )
        if confirmation_type == "email_verification":
            await mark_email_as_verified(db=db, user_id=user.id, commit=False)
        await db.commit()
    except Exception:
        await db.rollback()
        raise

    return {
        "message": f"Confirmação de {confirmation_type} realizada com sucesso!",
        "confirmation_type": confirmation_type,
    }
