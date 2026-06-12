from pydantic import BaseModel, EmailStr


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class VerifyResetCodeRequest(BaseModel):
    email: EmailStr
    code: str


class ResetPasswordRequest(BaseModel):
    reset_token: str
    new_password: str


class ResetCodeVerifiedResponse(BaseModel):
    reset_token: str
    token_type: str = "bearer"