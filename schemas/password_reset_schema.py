from pydantic import BaseModel, ConfigDict, EmailStr, Field


class ForgotPasswordRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: EmailStr


class VerifyResetCodeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: EmailStr
    code: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")


class ResetPasswordRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reset_token: str
    new_password: str = Field(min_length=8, max_length=128)


class ResetCodeVerifiedResponse(BaseModel):
    reset_token: str
    token_type: str = "bearer"
