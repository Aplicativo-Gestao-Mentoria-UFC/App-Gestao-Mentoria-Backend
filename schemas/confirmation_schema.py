from pydantic import BaseModel, EmailStr


class RequestConfirmationCodeRequest(BaseModel):
    email: EmailStr


class VerifyConfirmationCodeRequest(BaseModel):
    email: EmailStr
    code: str
    confirmation_type: str = "email_verification"


class ConfirmationCodeVerifiedResponse(BaseModel):
    message: str
    token_type: str = "bearer"
