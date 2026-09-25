from datetime import UTC, datetime, timedelta
from uuid import UUID
import hashlib
import hmac
import secrets

from fastapi import BackgroundTasks, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import exceptions, jwt
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from core import deps
from core.config import settings
from core.security import create_access_token, get_password_hash, verify_password
from models.__all_models import UserRole
from models.user_model import UserModel
from repositories import professor_signup_repository
from repositories.activity_repository import get_by_id as get_activity_by_id
from repositories.course_class_repository import (
    get_class_by_id,
    has_class_read_permission,
    has_class_write_permission,
    is_monitor_of_class,
    is_student_of_class,
    is_teacher_of_class,
)
from repositories.user_repository import (
    create_user,
    create_verified_teacher,
    get_user_by_email,
    get_user_by_id,
    get_user_by_username,
)
from schemas.user_schema import validate_strong_password, validate_teacher_institutional_email
from services.email_service import safe_send_confirmation_code


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")


def resolve_registration_role(requested_role: UserRole) -> str:
    if requested_role == UserRole.student:
        return UserRole.student.value
    if requested_role == UserRole.teacher:
        return UserRole.teacher.value
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Tipo de usuário inválido",
    )


def generate_professor_signup_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def hash_professor_signup_code(email: str, code: str) -> str:
    normalized_email = email.strip().lower()
    payload = f"professor_signup:{normalized_email}:{code}".encode("utf-8")
    return hmac.new(
        settings.JWT_SECRET.encode("utf-8"),
        payload,
        hashlib.sha256,
    ).hexdigest()


def create_professor_signup_token(email: str, verification_id: UUID) -> str:
    return create_access_token(
        data={
            "sub": email.strip().lower(),
            "type": "professor_signup",
            "verification_id": str(verification_id),
        },
        expires_delta=timedelta(minutes=settings.PROFESSOR_SIGNUP_TOKEN_EXPIRE_MINUTES),
    )


async def request_professor_signup_code(
    db: AsyncSession,
    email: str,
    background_tasks: BackgroundTasks,
):
    normalized_email = email.strip().lower()

    try:
        normalized_email = validate_teacher_institutional_email(
            normalized_email,
            UserRole.teacher,
        )
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))

    existing_user = await get_user_by_email(db, normalized_email)
    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Já existe uma conta cadastrada com esse email.",
        )

    if await professor_signup_repository.has_completed_signup_for_email(
        db=db,
        email=normalized_email,
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Este email institucional já foi utilizado em um cadastro concluído.",
        )

    raw_code = generate_professor_signup_code()
    code_hash = hash_professor_signup_code(normalized_email, raw_code)
    expires_at = datetime.now(UTC) + timedelta(
        minutes=settings.PROFESSOR_SIGNUP_CODE_EXPIRE_MINUTES
    )

    try:
        await professor_signup_repository.invalidate_active_codes(
            db=db,
            email=normalized_email,
        )
        await professor_signup_repository.create(
            db=db,
            email=normalized_email,
            code_hash=code_hash,
            expires_at=expires_at,
        )
        await db.commit()
    except Exception:
        await db.rollback()
        raise

    background_tasks.add_task(
        safe_send_confirmation_code,
        normalized_email,
        raw_code,
        "professor_signup",
    )
    return {"message": "Código enviado para o email institucional."}


async def verify_professor_signup_code(
    db: AsyncSession,
    email: str,
    code: str,
):
    normalized_email = email.strip().lower()

    if not code.isdigit() or len(code) != 6:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Código inválido ou expirado.",
        )

    verification = await professor_signup_repository.get_latest_active_by_email(
        db=db,
        email=normalized_email,
    )
    if verification is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Código inválido, expirado ou já utilizado.",
        )

    if verification.attempts >= settings.PROFESSOR_SIGNUP_MAX_ATTEMPTS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Muitas tentativas. Solicite um novo código.",
        )

    received_hash = hash_professor_signup_code(normalized_email, code)
    if not hmac.compare_digest(received_hash, verification.code_hash):
        await professor_signup_repository.increment_attempts(
            db=db,
            verification=verification,
        )
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Código inválido ou expirado.",
        )

    try:
        await professor_signup_repository.mark_as_verified(
            db=db,
            verification=verification,
        )
        await db.commit()
    except Exception:
        await db.rollback()
        raise

    signup_token = create_professor_signup_token(
        email=normalized_email,
        verification_id=verification.id,
    )
    return {
        "signup_token": signup_token,
        "token_type": "bearer",
        "expires_in": settings.PROFESSOR_SIGNUP_TOKEN_EXPIRE_MINUTES * 60,
    }


def decode_professor_signup_token(signup_token: str) -> tuple[str, UUID]:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token de cadastro inválido ou expirado.",
    )
    try:
        payload = jwt.decode(
            signup_token,
            settings.JWT_SECRET,
            algorithms=[settings.ALGORITHM],
        )
        email = payload.get("sub")
        token_type = payload.get("type")
        verification_id = payload.get("verification_id")
        if not email or token_type != "professor_signup" or not verification_id:
            raise credentials_exception
        return email, UUID(verification_id)
    except (exceptions.JWTError, ValueError, TypeError):
        raise credentials_exception


async def complete_professor_signup(
    db: AsyncSession,
    signup_token: str,
    username: str,
    email: str,
    password: str,
):
    institutional_email, verification_id = decode_professor_signup_token(signup_token)
    institutional_email = institutional_email.strip().lower()
    email = email.strip().lower()
    username = username.strip()

    verification = await professor_signup_repository.get_by_id(
        db=db,
        verification_id=verification_id,
    )
    if verification is None or verification.email != institutional_email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de cadastro inválido.",
        )
    if verification.verified_at is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="O email institucional ainda não foi verificado.",
        )
    if verification.completed_at is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Este cadastro já foi concluído.",
        )

    if await get_user_by_email(db, email) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Já existe uma conta com esse email.",
        )
    if await get_user_by_username(db, username) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username já está em uso.",
        )

    try:
        password = validate_strong_password(password)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))

    try:
        user = await create_verified_teacher(
            db=db,
            username=username,
            email=email,
            hashed_password=get_password_hash(password),
        )
        await professor_signup_repository.mark_as_completed(
            db=db,
            verification=verification,
        )
        await db.commit()
        await db.refresh(user)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email ou username já está em uso.",
        )
    except Exception:
        await db.rollback()
        raise

    return {
        "access_token": create_access_token(
            data={"sub": str(user.id), "type": "access"},
            expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        ),
        "token_type": "bearer",
    }


async def authenticate_user(db: AsyncSession, email: str, password: str):
    user = await get_user_by_email(db, email.strip().lower())
    if user is None or not verify_password(password, user.hashed_password):
        return None
    if user.email_verified_at is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email não verificado. Verifique seu email antes de fazer login.",
        )
    return user


async def register_user(
    db: AsyncSession,
    username: str,
    email: str,
    role: UserRole,
    password: str,
):
    if role == UserRole.teacher:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Não é possível registrar um professor diretamente. "
                "Use o fluxo /auth/professor/signup/*."
            ),
        )

    username = username.strip()
    try:
        email = validate_teacher_institutional_email(email, role)
        password = validate_strong_password(password)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))

    if await get_user_by_email(db, email) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Já existe um usuário com esse email!",
        )
    if await get_user_by_username(db, username) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Já existe um usuário com esse username!",
        )

    try:
        return await create_user(
            db,
            username,
            email,
            resolve_registration_role(role),
            get_password_hash(password),
        )
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email ou username já está em uso!",
        )


async def get_current_user(
    db: AsyncSession = Depends(deps.get_session),
    token: str = Depends(oauth2_scheme),
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Não foi possível validar as credenciais",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.ALGORITHM],
        )
        user_id = payload.get("sub")
        if user_id is None or payload.get("type") != "access":
            raise credentials_exception
        user_uuid = UUID(user_id)
    except (exceptions.JWTError, ValueError, TypeError):
        raise credentials_exception

    user = await get_user_by_id(db, user_uuid)
    if user is None:
        raise credentials_exception
    if user.email_verified_at is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email não verificado",
        )
    return user


def require_role(required_role: UserRole):
    async def role_checker(current_user: UserModel = Depends(get_current_user)):
        required_role_value = (
            required_role.value if isinstance(required_role, UserRole) else required_role
        )
        if current_user.role != required_role_value:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Você não tem permissão para acessar essa rota",
            )
        return current_user

    return role_checker


async def _get_class_or_404(db: AsyncSession, course_class_id: str | UUID):
    course_class_uuid = deps.validate_uuid(course_class_id)
    course_class = await get_class_by_id(db=db, course_class_id=course_class_uuid)
    if course_class is None:
        raise HTTPException(status_code=404, detail="Essa turma não existe")
    return course_class


async def _get_activity_or_404(db: AsyncSession, activity_id: str | UUID):
    activity_uuid = deps.validate_uuid(activity_id)
    activity = await get_activity_by_id(db=db, activity_id=activity_uuid)
    if activity is None:
        raise HTTPException(status_code=404, detail="Essa atividade não existe")
    return activity


def require_teacher_class():
    async def checker(
        course_class_id: str,
        current_user: UserModel = Depends(get_current_user),
        db: AsyncSession = Depends(deps.get_session),
    ):
        course_class = await _get_class_or_404(db, course_class_id)
        if not await is_teacher_of_class(db, current_user.id, course_class.id):
            raise HTTPException(status_code=403, detail="Você não é o responsável por essa turma")
        return course_class

    return checker


def require_student_class():
    async def checker(
        course_class_id: str,
        current_user: UserModel = Depends(get_current_user),
        db: AsyncSession = Depends(deps.get_session),
    ):
        course_class = await _get_class_or_404(db, course_class_id)
        if not await is_student_of_class(db, current_user.id, course_class.id):
            raise HTTPException(status_code=403, detail="Você não é aluno dessa turma")
        return course_class

    return checker


def require_monitor_class():
    async def checker(
        course_class_id: str,
        current_user: UserModel = Depends(get_current_user),
        db: AsyncSession = Depends(deps.get_session),
    ):
        course_class = await _get_class_or_404(db, course_class_id)
        if not await is_monitor_of_class(db, current_user.id, course_class.id):
            raise HTTPException(status_code=403, detail="Você não é monitor dessa turma")
        return course_class

    return checker


def require_teacher_or_monitor_class():
    async def checker(
        course_class_id: str,
        current_user: UserModel = Depends(get_current_user),
        db: AsyncSession = Depends(deps.get_session),
    ):
        course_class = await _get_class_or_404(db, course_class_id)
        if not await has_class_write_permission(db, current_user.id, course_class.id):
            raise HTTPException(
                status_code=403,
                detail="Apenas professor ou monitor podem realizar essa ação",
            )
        return course_class

    return checker


def require_class_access():
    async def checker(
        course_class_id: str,
        current_user: UserModel = Depends(get_current_user),
        db: AsyncSession = Depends(deps.get_session),
    ):
        course_class = await _get_class_or_404(db, course_class_id)
        if not await has_class_read_permission(db, current_user.id, course_class.id):
            raise HTTPException(status_code=403, detail="Você não tem acesso a essa turma")
        return course_class

    return checker


def require_teacher_or_monitor_activity():
    async def checker(
        activity_id: str,
        current_user: UserModel = Depends(get_current_user),
        db: AsyncSession = Depends(deps.get_session),
    ):
        activity = await _get_activity_or_404(db, activity_id)
        if not await has_class_write_permission(db, current_user.id, activity.course_class_id):
            raise HTTPException(
                status_code=403,
                detail="Apenas professor ou monitor podem alterar essa atividade",
            )
        return activity

    return checker


def require_activity_access():
    async def checker(
        activity_id: str,
        current_user: UserModel = Depends(get_current_user),
        db: AsyncSession = Depends(deps.get_session),
    ):
        activity = await _get_activity_or_404(db, activity_id)
        if not await has_class_read_permission(db, current_user.id, activity.course_class_id):
            raise HTTPException(status_code=403, detail="Você não tem acesso a essa atividade")
        return activity

    return checker
