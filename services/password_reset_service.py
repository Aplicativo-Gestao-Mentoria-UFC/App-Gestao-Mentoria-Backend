import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import BackgroundTasks, HTTPException, status
from jose import exceptions, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.security import create_access_token, get_password_hash
from repositories import password_reset_repository
from repositories.user_repository import get_user_by_email, get_user_by_id
from schemas.token import Token
from schemas.user_schema import validate_strong_password
from services.email_service import safe_send_password_reset_code

PASSWORD_RESET_CODE_EXPIRE_MINUTES = 30
PASSWORD_RESET_JWT_EXPIRE_MINUTES = 15
PASSWORD_RESET_MAX_ATTEMPTS = 5


def generate_six_digit_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def hash_reset_code(user_id, code: str) -> str:
    payload = f"{user_id}:{code}".encode("utf-8")
    return hmac.new(settings.JWT_SECRET.encode(), payload, hashlib.sha256).hexdigest()


def create_password_reset_token(user_id: UUID) -> str:
    payload = {
        "sub": str(user_id),
        "type": "password_reset",
        "exp": datetime.now(UTC) + timedelta(minutes=PASSWORD_RESET_JWT_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.ALGORITHM)


def decode_password_reset_token(reset_token: str) -> UUID:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token de recuperação inválido ou expirado.",
    )
    try:
        payload = jwt.decode(reset_token, settings.JWT_SECRET, algorithms=[settings.ALGORITHM])
        if payload.get("type") != "password_reset" or not payload.get("sub"):
            raise credentials_exception
        return UUID(payload["sub"])
    except (exceptions.JWTError, ValueError, TypeError):
        raise credentials_exception


async def request_password_reset(
    db: AsyncSession,
    email: str,
    background_tasks: BackgroundTasks,
):
    generic_response = {
        "message": "Se o email estiver cadastrado, enviaremos um código de recuperação."
    }
    user = await get_user_by_email(db, email.strip().lower())
    if not user:
        return generic_response

    raw_code = generate_six_digit_code()
    await password_reset_repository.invalidate_active_codes(db, user.id)
    await password_reset_repository.create_password_reset_code(
        db=db,
        user_id=user.id,
        code_hash=hash_reset_code(user.id, raw_code),
        expires_at=datetime.now(UTC) + timedelta(minutes=PASSWORD_RESET_CODE_EXPIRE_MINUTES),
    )
    background_tasks.add_task(
        safe_send_password_reset_code,
        user.email,
        raw_code,
        user.username,
    )
    return generic_response


async def verify_password_reset_code(db: AsyncSession, email: str, code: str):
    user = await get_user_by_email(db, email.strip().lower())
    if not user:
        raise HTTPException(status_code=400, detail="Código inválido ou expirado.")

    reset_code = await password_reset_repository.get_latest_active_code_by_user_id(db, user.id)
    if not reset_code:
        raise HTTPException(status_code=400, detail="Código inválido ou expirado.")
    if reset_code.attempts >= PASSWORD_RESET_MAX_ATTEMPTS:
        await password_reset_repository.mark_code_as_used(db, reset_code)
        raise HTTPException(status_code=400, detail="Código inválido ou expirado.")

    if not hmac.compare_digest(hash_reset_code(user.id, code), reset_code.code_hash):
        await password_reset_repository.increment_attempts(db, reset_code)
        raise HTTPException(status_code=400, detail="Código inválido ou expirado.")

    await password_reset_repository.mark_code_as_used(db, reset_code)
    return {"reset_token": create_password_reset_token(user.id), "token_type": "bearer"}


async def reset_password_with_token(db: AsyncSession, reset_token: str, new_password: str):
    try:
        validate_strong_password(new_password)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))

    user_id = decode_password_reset_token(reset_token)
    user = await get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=401, detail="Token de recuperação inválido ou expirado.")

    user.hashed_password = get_password_hash(new_password)
    await db.commit()
    await db.refresh(user)

    access_token = create_access_token(
        data={"sub": str(user.id), "type": "access"},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return Token(access_token=access_token, token_type="bearer")
