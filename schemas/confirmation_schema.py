from pydantic import BaseModel, ConfigDict, EmailStr, Field


class RequestConfirmationCodeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: EmailStr


class VerifyConfirmationCodeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: EmailStr
    code: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")


class ConfirmationCodeVerifiedResponse(BaseModel):
    message: str
    confirmation_type: str
