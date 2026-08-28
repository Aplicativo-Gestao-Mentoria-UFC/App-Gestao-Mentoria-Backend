from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from schemas.password_reset_schema import (
    ForgotPasswordRequest,
    VerifyResetCodeRequest,
    ResetPasswordRequest,
    ResetCodeVerifiedResponse,
)
from schemas.confirmation_schema import (
    RequestConfirmationCodeRequest,
    VerifyConfirmationCodeRequest,
    ConfirmationCodeVerifiedResponse,
)

from services.password_reset_service import (
    request_password_reset,
    verify_password_reset_code,
    reset_password_with_token,
)
from services.confirmation_service import (
    request_confirmation_code,
    verify_confirmation_code,
)
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from schemas.user_schema import UserCreate, User
from schemas.token import Token
from services.auth_service import (
    authenticate_user,
    get_current_user,
    register_user,
    request_professor_signup_code,
    verify_professor_signup_code,

)
from core import deps
from core.config import settings
from core.security import create_access_token


router = APIRouter(prefix="/auth")


@router.post(
    "/register",
    response_model=User,
    status_code=status.HTTP_201_CREATED,
)
async def register(
    user: UserCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(deps.get_session),
):
    created_user = await register_user(
        db,
        user.username,
        user.email,
        user.role,
        user.password,
    )

    await request_confirmation_code(
        db=db,
        email=created_user.email,
        background_tasks=background_tasks,
        confirmation_type="email_verification",
    )

    return created_user


@router.post("/token")
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
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id), "type": "access"},
        expires_delta=access_token_expires,
    )
    return Token(access_token=access_token, token_type="bearer")


@router.get("/me", response_model=User)
async def read_me(current_user: User = Depends(get_current_user)):
    return current_user

@router.post("/forgot-password")
async def forgot_password(
    data: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(deps.get_session),
):
    return await request_password_reset(
        db=db,
        email=data.email,
        background_tasks=background_tasks,
    )


@router.post("/verify-reset-code", response_model=ResetCodeVerifiedResponse)
async def verify_reset_code(
    data: VerifyResetCodeRequest,
    db: AsyncSession = Depends(deps.get_session),
):
    return await verify_password_reset_code(
        db=db,
        email=data.email,
        code=data.code,
    )


@router.post("/reset-password", response_model=Token)
async def reset_password(
    data: ResetPasswordRequest,
    db: AsyncSession = Depends(deps.get_session),
):
    return await reset_password_with_token(
        db=db,
        reset_token=data.reset_token,
        new_password=data.new_password,
    )


@router.post("/request-confirmation-code")
async def request_confirmation(
    data: RequestConfirmationCodeRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(deps.get_session),
):
    return await request_confirmation_code(
        db=db,
        email=data.email,
        background_tasks=background_tasks,
    )


@router.post("/verify-confirmation-code", response_model=ConfirmationCodeVerifiedResponse)
async def verify_confirmation(
    data: VerifyConfirmationCodeRequest,
    db: AsyncSession = Depends(deps.get_session),
):
    return await verify_confirmation_code(
        db=db,
        email=data.email,
        code=data.code,
        confirmation_type="email_verification",
    )

@router.post("/auth/professor/signup/request", response_model=ConfirmationCodeVerifiedResponse)
async def signup_professor(
    data: VerifyConfirmationCodeRequest,
    db: AsyncSession = Depends(deps.get_session),
):
    return await request_professor_signup_code(
        db=db,
        email=data.email,
    ) # type: ignore

@router.post("/auth/professor/verify", response_model=ResetCodeVerifiedResponse)
async def verify_professor_signup_code(
    email: str,
    code: str,
    db: AsyncSession = Depends(deps.get_session),
):
    return await verify_professor_signup_code(email=email, code=code)


@router.post("/auth/professor/signup/complete", response_model=Token)
async def professor_signup_confirmation(
    signup_token: str,
    email: str,
    username: str,
    password: str,
    db: AsyncSession = Depends(deps.get_session),
): 
    