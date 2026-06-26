from uuid import UUID

from fastapi import HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, exceptions
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from core.security import get_password_hash, verify_password
from core.config import settings
from core import deps

from repositories.user_repository import (
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


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")


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

    return user


async def register_user(
    db: AsyncSession,
    username: str,
    email: str,
    role: UserRole,
    password: str,
):
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