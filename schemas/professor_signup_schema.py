from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
)


class ProfessorSignupRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid"
    )

    email: EmailStr


class ProfessorSignupVerifyRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid"
    )

    email: EmailStr

    code: str = Field(
        min_length=6,
        max_length=6,
        pattern=r"^\d{6}$",
    )


class ProfessorSignupVerifiedResponse(
    BaseModel
):
    signup_token: str
    token_type: str
    expires_in: int


class ProfessorSignupCompleteRequest(
    BaseModel
):
    model_config = ConfigDict(
        extra="forbid"
    )

    signup_token: str


    email: EmailStr

    username: str = Field(
        min_length=3,
        max_length=50,
    )

    password: str = Field(
        max_length=128,
    )