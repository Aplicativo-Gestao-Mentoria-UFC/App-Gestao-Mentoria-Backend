from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import BackgroundTasks, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, exceptions
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

import hmac
import hashlib
import secrets

from core.security import create_access_token, get_password_hash, verify_password
from core.config import settings
from core import deps

from repositories import professor_signup_repository
from repositories.user_repository import (
    create_verified_teacher,
    get_user_by_email,
    get_user_by_id,
    get_user_by_username,
    create_user,
)

from repositories.course_class_repository import (
    get_class_by_id,
    is_teacher_of_class,
    is_student_of_class,
    is_monitor_of_class,
    has_class_write_permission,
    has_class_read_permission,
)

from repositories.activity_repository import get_by_id as get_activity_by_id

from schemas.user_schema import (
    validate_strong_password,
    validate_teacher_institutional_email,
)

from models.user_model import UserModel
from models.__all_models import UserRole
from services.email_service import send_confirmation_code


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")

PROFESSOR_SIGNUP_CODE_EXPIRE_MINUTES = 30
PROFESSOR_SIGNUP_TOKEN_EXPIRE_MINUTES = 30

PROFESSOR_SIGNUP_MAX_ATTEMPTS = 5


def resolve_registration_role(
    email: str,
    requested_role: UserRole,
) -> str:
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

def hash_professor_signup_code(
    email: str,
    code: str,
) -> str:
    normalized_email = email.strip().lower()

    payload = (
        f"professor_signup:{normalized_email}:{code}"
    ).encode("utf-8")

    secret = settings.JWT_SECRET.encode("utf-8")

    return hmac.new(
        secret,
        payload,
        hashlib.sha256,
    ).hexdigest()

async def request_professor_signup_code(
    db: AsyncSession,
    email: str,
    background_tasks: BackgroundTasks,
):
    normalized_email = email.strip().lower()

    try:
        normalized_email = (
            validate_teacher_institutional_email(
                normalized_email,
                UserRole.teacher,
            )
        )

    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        )

    existing_user = await get_user_by_email(
        db,
        normalized_email,
    )

    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Já existe uma conta cadastrada com esse email.",
        )

    raw_code = generate_professor_signup_code()

    code_hash = hash_professor_signup_code(
        normalized_email,
        raw_code,
    )

    expires_at = (
        datetime.now(UTC)
        + timedelta(
            minutes=PROFESSOR_SIGNUP_CODE_EXPIRE_MINUTES
        )
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
        send_confirmation_code,
        normalized_email,
        raw_code,
        "professor_signup",
    )

    return {
        "message": "Código enviado para o email institucional."
    }

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

    verification = (
        await professor_signup_repository
        .get_latest_active_by_email(
            db=db,
            email=normalized_email,
        )
    )

    if verification is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Código inválido, expirado ou já utilizado.",
        )

    if (
        verification.attempts
        >= PROFESSOR_SIGNUP_MAX_ATTEMPTS
    ):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                "Muitas tentativas. "
                "Solicite um novo código."
            ),
        )

    received_hash = hash_professor_signup_code(
        normalized_email,
        code,
    )

    if not hmac.compare_digest(
        received_hash,
        verification.code_hash,
    ):
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
        "expires_in": (
            PROFESSOR_SIGNUP_TOKEN_EXPIRE_MINUTES * 60
        ),
    }

def decode_professor_signup_token(
    signup_token: str,
) -> tuple[str, UUID]:
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
        verification_id = payload.get(
            "verification_id"
        )

        if (
            not email
            or token_type != "professor_signup"
            or not verification_id
        ):
            raise credentials_exception

        verification_uuid = UUID(
            verification_id
        )

    except (
        exceptions.JWTError,
        ValueError,
    ):
        raise credentials_exception

    return email, verification_uuid


async def complete_professor_signup(
    db: AsyncSession,
    signup_token: str,
    username: str,
    email: str,
    password: str,
):
    # ---------------------------------------------------------
    # 1. Valida e decodifica o token temporário
    # ---------------------------------------------------------

    institutional_email, verification_id = (
        decode_professor_signup_token(
            signup_token
        )
    )

    institutional_email = institutional_email.strip().lower()
    email = email.strip().lower()
    username = username.strip()

    # ---------------------------------------------------------
    # 2. Busca a verificação no banco
    # ---------------------------------------------------------

    verification = (
        await professor_signup_repository.get_by_id(
            db=db,
            verification_id=verification_id,
        )
    )

    # ---------------------------------------------------------
    # 3. Valida o estado da verificação
    # ---------------------------------------------------------

    if verification is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de cadastro inválido.",
        )

    if verification.email != institutional_email:
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
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Este cadastro já foi concluído.",
        )

    # ---------------------------------------------------------
    # 4. Verifica se o email escolhido já está em uso
    # ---------------------------------------------------------

    existing_email = await get_user_by_email(
        db,
        email,
    )

    if existing_email is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Já existe uma conta com esse email.",
        )

    # ---------------------------------------------------------
    # 5. Verifica se o username já está em uso
    # ---------------------------------------------------------

    existing_username = await get_user_by_username(
        db,
        username,
    )

    if existing_username is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username já está em uso.",
        )

    # ---------------------------------------------------------
    # 6. Valida a senha
    # ---------------------------------------------------------

    try:
        password = validate_strong_password(
            password
        )

    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        )

    # ---------------------------------------------------------
    # 7. Cria hash da senha
    # ---------------------------------------------------------

    hashed_password = get_password_hash(
        password
    )

    # ---------------------------------------------------------
    # 8. Cria o professor
    # ---------------------------------------------------------

    try:
        user = await create_verified_teacher(
            db=db,
            username=username,
            email=email,
            hashed_password=hashed_password,
        )

        # O processo de signup não pode ser reutilizado
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

    # ---------------------------------------------------------
    # 9. Cria o access token normal
    # ---------------------------------------------------------

    access_token_expires = timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )

    access_token = create_access_token(
        data={
            "sub": str(user.id),
            "type": "access",
        },
        expires_delta=access_token_expires,
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
    }

async def authenticate_user(
    db: AsyncSession,
    email: str,
    password: str,
):
    user = await get_user_by_email(db, email)

    if user is None:
        return None

    if not verify_password(password, user.hashed_password):
        return None

    if user.email_verified_at is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email não verificado. Por favor, verifique seu email antes de fazer login",
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
            detail="Não é possível registrar um professor diretamente. Professores devem se registrar através do fluxo de cadastro de professores.",
        )

    try:
        email = validate_teacher_institutional_email(email, role)
        password = validate_strong_password(password)

    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        )

    exists_email = await get_user_by_email(db, email)

    if exists_email is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Já existe um usuário com esse email!",
        )

    exists_username = await get_user_by_username(db, username)

    if exists_username is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Já existe um usuário com esse username!",
        )

    user_role = resolve_registration_role(email, role)
    hashed_password = get_password_hash(password)

    try:
        return await create_user(
            db,
            username,
            email,
            user_role,
            hashed_password,
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
        token_type = payload.get("type")

        if user_id is None or token_type != "access":
            raise credentials_exception

        user_uuid = UUID(user_id)

    except (exceptions.JWTError, ValueError):
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
    async def role_checker(
        current_user: UserModel = Depends(get_current_user),
    ):
        required_role_value = (
            required_role.value
            if isinstance(required_role, UserRole)
            else required_role
        )

        if current_user.role != required_role_value:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Você não tem permissão para acessar essa rota",
            )

        return current_user

    return role_checker


async def _get_class_or_404(
    db: AsyncSession,
    course_class_id: str,
):
    course_class_uuid = deps.validate_uuid(course_class_id)

    course_class = await get_class_by_id(
        db=db,
        course_class_id=course_class_uuid,
    )

    if course_class is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Essa turma não existe",
        )

    return course_class


async def _get_activity_or_404(
    db: AsyncSession,
    activity_id: str,
):
    activity_uuid = deps.validate_uuid(activity_id)

    activity = await get_activity_by_id(
        db=db,
        activity_id=activity_uuid,
    )

    if activity is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Essa atividade não existe",
        )

    return activity


def require_teacher_class():
    async def checker(
        course_class_id: str,
        current_user: UserModel = Depends(get_current_user),
        db: AsyncSession = Depends(deps.get_session),
    ):
        course_class = await _get_class_or_404(
            db=db,
            course_class_id=course_class_id,
        )

        allowed = await is_teacher_of_class(
            db=db,
            user_id=current_user.id,
            course_class_id=course_class.id,
        )

        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Você não é o responsável por essa turma",
            )

        return course_class

    return checker


def require_student_class():
    async def checker(
        course_class_id: str,
        current_user: UserModel = Depends(get_current_user),
        db: AsyncSession = Depends(deps.get_session),
    ):
        course_class = await _get_class_or_404(
            db=db,
            course_class_id=course_class_id,
        )

        allowed = await is_student_of_class(
            db=db,
            user_id=current_user.id,
            course_class_id=course_class.id,
        )

        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Você não é aluno dessa turma",
            )

        return course_class

    return checker


def require_monitor_class():
    async def checker(
        course_class_id: str,
        current_user: UserModel = Depends(get_current_user),
        db: AsyncSession = Depends(deps.get_session),
    ):
        course_class = await _get_class_or_404(
            db=db,
            course_class_id=course_class_id,
        )

        allowed = await is_monitor_of_class(
            db=db,
            user_id=current_user.id,
            course_class_id=course_class.id,
        )

        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Você não é monitor dessa turma",
            )

        return course_class

    return checker


def require_teacher_or_monitor_class():
    async def checker(
        course_class_id: str,
        current_user: UserModel = Depends(get_current_user),
        db: AsyncSession = Depends(deps.get_session),
    ):
        course_class = await _get_class_or_404(
            db=db,
            course_class_id=course_class_id,
        )

        allowed = await has_class_write_permission(
            db=db,
            user_id=current_user.id,
            course_class_id=course_class.id,
        )

        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
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
        course_class = await _get_class_or_404(
            db=db,
            course_class_id=course_class_id,
        )

        allowed = await has_class_read_permission(
            db=db,
            user_id=current_user.id,
            course_class_id=course_class.id,
        )

        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Você não tem acesso a essa turma",
            )

        return course_class

    return checker


def require_teacher_or_monitor_activity():
    async def checker(
        activity_id: str,
        current_user: UserModel = Depends(get_current_user),
        db: AsyncSession = Depends(deps.get_session),
    ):
        activity = await _get_activity_or_404(
            db=db,
            activity_id=activity_id,
        )

        allowed = await has_class_write_permission(
            db=db,
            user_id=current_user.id,
            course_class_id=activity.course_class_id,
        )

        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
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
        activity = await _get_activity_or_404(
            db=db,
            activity_id=activity_id,
        )

        allowed = await has_class_read_permission(
            db=db,
            user_id=current_user.id,
            course_class_id=activity.course_class_id,
        )

        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Você não tem acesso a essa atividade",
            )

        return activity

    return checker