import hashlib
import hmac
import secrets
from datetime import datetime, timedelta

from fastapi import BackgroundTasks, HTTPException, status
from jose import jwt, exceptions
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.security import create_access_token, get_password_hash
from repositories.user_repository import get_user_by_email, get_user_by_id
from repositories import password_reset_repository
from schemas.token import Token
from services.email_service import send_password_reset_code


PASSWORD_RESET_CODE_EXPIRE_MINUTES = 30
PASSWORD_RESET_JWT_EXPIRE_MINUTES = 15
PASSWORD_RESET_MAX_ATTEMPTS = 5


def generate_six_digit_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def hash_reset_code(user_id, code: str) -> str:
    payload = f"{user_id}:{code}".encode("utf-8")
    secret = settings.JWT_SECRET.encode("utf-8")

    return hmac.new(secret, payload, hashlib.sha256).hexdigest()


def validate_code_format(code: str):
    if not code.isdigit() or len(code) != 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Código inválido ou expirado.",
        )


def validate_new_password(new_password: str):
    if len(new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A nova senha deve ter pelo menos 8 caracteres.",
        )


def create_password_reset_token(user_id) -> str:
    expires_at = datetime.utcnow() + timedelta(
        minutes=PASSWORD_RESET_JWT_EXPIRE_MINUTES
    )

    payload = {
        "sub": str(user_id),
        "purpose": "password_reset",
        "exp": expires_at,
    }

    return jwt.encode(
        payload,
        settings.JWT_SECRET,
        algorithm=settings.ALGORITHM,
    )


def decode_password_reset_token(reset_token: str) -> str:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token de recuperação inválido ou expirado.",
    )

    try:
        payload = jwt.decode(
            reset_token,
            settings.JWT_SECRET,
            algorithms=[settings.ALGORITHM],
        )

        user_id = payload.get("sub")
        purpose = payload.get("purpose")

        if user_id is None or purpose != "password_reset":
            raise credentials_exception

        return user_id

    except exceptions.JWTError:
        raise credentials_exception


async def request_password_reset(
    db: AsyncSession,
    email: str,
    background_tasks: BackgroundTasks,
):
    generic_response = {
        "message": "Se o email estiver cadastrado, enviaremos um código de recuperação."
    }

    user = await get_user_by_email(db, email)

    if not user:
        return generic_response

    raw_code = generate_six_digit_code()
    code_hash = hash_reset_code(user.id, raw_code)

    expires_at = datetime.utcnow() + timedelta(
        minutes=PASSWORD_RESET_CODE_EXPIRE_MINUTES
    )

    await password_reset_repository.invalidate_active_codes(db, user.id)

    await password_reset_repository.create_password_reset_code(
        db=db,
        user_id=user.id,
        code_hash=code_hash,
        expires_at=expires_at,
    )

    background_tasks.add_task(
        send_password_reset_code,
        user.email,
        raw_code,
    )

    return generic_response


async def verify_password_reset_code(
    db: AsyncSession,
    email: str,
    code: str,
):
    validate_code_format(code)

    user = await get_user_by_email(db, email)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Código inválido ou expirado.",
        )

    reset_code = await password_reset_repository.get_latest_active_code_by_user_id(
        db=db,
        user_id=user.id,
    )

    if not reset_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Código inválido ou expirado.",
        )

    if reset_code.attempts >= PASSWORD_RESET_MAX_ATTEMPTS:
        await password_reset_repository.mark_code_as_used(db, reset_code)

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Código inválido ou expirado.",
        )

    received_code_hash = hash_reset_code(user.id, code)

    if not hmac.compare_digest(received_code_hash, reset_code.code_hash):
        await password_reset_repository.increment_attempts(db, reset_code)

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Código inválido ou expirado.",
        )

    await password_reset_repository.mark_code_as_used(db, reset_code)

    reset_token = create_password_reset_token(user.id)

    return {
        "reset_token": reset_token,
        "token_type": "bearer",
    }


async def reset_password_with_token(
    db: AsyncSession,
    reset_token: str,
    new_password: str,
):
    validate_new_password(new_password)

    user_id = decode_password_reset_token(reset_token)

    user = await get_user_by_id(db, user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de recuperação inválido ou expirado.",
        )

    hashed_password = get_password_hash(new_password)

    setattr(user, "hashed_password", hashed_password)

    await db.commit()
    await db.refresh(user)

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    access_token = create_access_token(
        data={"sub": user.email},
        expires_delta=access_token_expires,
    )

    return Token(
        access_token=access_token,
        token_type="bearer",
    )