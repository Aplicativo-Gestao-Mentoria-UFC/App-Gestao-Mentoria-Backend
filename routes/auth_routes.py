from datetime import timedelta

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from core import deps
from core.config import settings
from core.security import create_access_token
from schemas.common import MessageResponse
from schemas.confirmation_schema import (
    ConfirmationCodeVerifiedResponse,
    RequestConfirmationCodeRequest,
    VerifyConfirmationCodeRequest,
)
from schemas.password_reset_schema import (
    ForgotPasswordRequest,
    ResetCodeVerifiedResponse,
    ResetPasswordRequest,
    VerifyResetCodeRequest,
)
from schemas.professor_signup_schema import (
    ProfessorSignupCompleteRequest,
    ProfessorSignupRequest,
    ProfessorSignupVerifiedResponse,
    ProfessorSignupVerifyRequest,
)
from schemas.token import Token
from schemas.user_schema import User, UserCreate
from services.auth_service import (
    authenticate_user,
    complete_professor_signup,
    get_current_user,
    register_user,
    request_professor_signup_code,
    verify_professor_signup_code,
)
from services.confirmation_service import request_confirmation_code, verify_confirmation_code
from services.password_reset_service import (
    request_password_reset,
    reset_password_with_token,
    verify_password_reset_code,
)

router = APIRouter(prefix="/auth")


@router.post(
    "/register",
    response_model=User,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastrar aluno",
    description="Cria uma conta de aluno ainda não verificada e envia um código por email.",
)
async def register(
    user: UserCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(deps.get_session),
):
    created_user = await register_user(
        db,
        user.username,
        str(user.email),
        user.role,
        user.password,
    )
    await request_confirmation_code(
        db=db,
        email=str(created_user.email),
        background_tasks=background_tasks,
        confirmation_type="email_verification",
    )
    return created_user


@router.post(
    "/token",
    response_model=Token,
    summary="Login",
    description="OAuth2 password flow. No campo username informe o email do usuário.",
)
async def login_for_access_token(
    db: AsyncSession = Depends(deps.get_session),
    form_data: OAuth2PasswordRequestForm = Depends(),
) -> Token:
    user = await authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha incorretos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(
        data={"sub": str(user.id), "type": "access"},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return Token(access_token=access_token, token_type="bearer")


@router.get("/me", response_model=User, summary="Usuário autenticado")
async def read_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.post("/forgot-password", response_model=MessageResponse, summary="Solicitar recuperação de senha")
async def forgot_password(
    data: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(deps.get_session),
):
    return await request_password_reset(db, str(data.email), background_tasks)


@router.post(
    "/verify-reset-code",
    response_model=ResetCodeVerifiedResponse,
    summary="Validar código de recuperação",
)
async def verify_reset_code(
    data: VerifyResetCodeRequest,
    db: AsyncSession = Depends(deps.get_session),
):
    return await verify_password_reset_code(db, str(data.email), data.code)


@router.post("/reset-password", response_model=Token, summary="Definir nova senha")
async def reset_password(
    data: ResetPasswordRequest,
    db: AsyncSession = Depends(deps.get_session),
):
    return await reset_password_with_token(db, data.reset_token, data.new_password)


@router.post(
    "/request-confirmation-code",
    response_model=MessageResponse,
    summary="Reenviar código de confirmação",
)
async def request_confirmation(
    data: RequestConfirmationCodeRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(deps.get_session),
):
    return await request_confirmation_code(
        db=db,
        email=str(data.email),
        background_tasks=background_tasks,
        confirmation_type="email_verification",
    )


@router.post(
    "/verify-confirmation-code",
    response_model=ConfirmationCodeVerifiedResponse,
    summary="Confirmar email do aluno",
)
async def verify_confirmation(
    data: VerifyConfirmationCodeRequest,
    db: AsyncSession = Depends(deps.get_session),
):
    return await verify_confirmation_code(
        db=db,
        email=str(data.email),
        code=data.code,
        confirmation_type="email_verification",
    )


@router.post(
    "/professor/signup/request",
    response_model=MessageResponse,
    summary="Solicitar código institucional de professor",
)
async def professor_signup_request(
    data: ProfessorSignupRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(deps.get_session),
):
    return await request_professor_signup_code(
        db=db,
        email=str(data.email),
        background_tasks=background_tasks,
    )


@router.post(
    "/professor/signup/verify",
    response_model=ProfessorSignupVerifiedResponse,
    summary="Validar código institucional de professor",
)
async def professor_signup_verify(
    data: ProfessorSignupVerifyRequest,
    db: AsyncSession = Depends(deps.get_session),
):
    return await verify_professor_signup_code(
        db=db,
        email=str(data.email),
        code=data.code,
    )


@router.post(
    "/professor/signup/complete",
    response_model=Token,
    status_code=status.HTTP_201_CREATED,
    summary="Concluir cadastro de professor",
    description=(
        "Usa o signup_token obtido após validar o email institucional. "
        "O email da conta final pode ser diferente do email institucional validado."
    ),
)
async def professor_signup_complete(
    data: ProfessorSignupCompleteRequest,
    db: AsyncSession = Depends(deps.get_session),
):
    return await complete_professor_signup(
        db=db,
        signup_token=data.signup_token,
        username=data.username,
        email=str(data.email),
        password=data.password,
    )
