from datetime import datetime
import re
from typing import Optional

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
    model_validator,
)
from models.__all_models import UserRole
import uuid


WEAK_PASSWORD_MESSAGE = (
    "A senha deve ter pelo menos 8 caracteres, uma letra maiúscula, "
    "uma letra minúscula, um número e um caractere especial."
)
TEACHER_EMAIL_DOMAIN = "ufc.br"
INVALID_TEACHER_EMAIL_MESSAGE = (
    "Professores devem usar email institucional com domínio @ufc.br."
)


def validate_strong_password(password: str) -> str:
    has_min_length = len(password) >= 8
    has_uppercase = re.search(r"[A-Z]", password)
    has_lowercase = re.search(r"[a-z]", password)
    has_number = re.search(r"\d", password)
    has_special_char = re.search(r"[^A-Za-z0-9]", password)

    if not all(
        [has_min_length, has_uppercase, has_lowercase, has_number, has_special_char]
    ):
        raise ValueError(WEAK_PASSWORD_MESSAGE)

    return password


def get_email_domain(email: EmailStr | str) -> str:
    email_value = str(email)
    return email_value.rsplit("@", maxsplit=1)[-1].lower()


def validate_teacher_institutional_email(email: EmailStr | str, role: UserRole) -> str:
    email_value = str(email)

    if (
        role == UserRole.teacher
        and get_email_domain(email_value) != TEACHER_EMAIL_DOMAIN
    ):
        raise ValueError(INVALID_TEACHER_EMAIL_MESSAGE)

    return email_value


class UserBase(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: EmailStr
    role: UserRole

    @model_validator(mode="after")
    def validate_teacher_email_domain(self):
        self.email = validate_teacher_institutional_email(self.email, self.role)
        return self


class UserCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: str = Field(min_length=3, max_length=50)
    email: EmailStr
    role: UserRole = UserRole.student
    password: str = Field(max_length=128)

    @model_validator(mode="after")
    def validate_teacher_email_domain(self):
        self.email = validate_teacher_institutional_email(self.email, self.role)
        return self

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, password: str) -> str:
        return validate_strong_password(password)


class UserUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: Optional[str] = Field(default=None, min_length=3, max_length=50)
    email: Optional[EmailStr] = None
    role: Optional[UserRole] = None
    password: Optional[str] = Field(default=None, max_length=128)

    @model_validator(mode="after")
    def validate_teacher_email_domain(self):
        if self.email is not None and self.role is not None:
            self.email = validate_teacher_institutional_email(self.email, self.role)

        return self

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, password: str | None) -> str | None:
        if password is None:
            return password

        return validate_strong_password(password)


class User(BaseModel):
    id: uuid.UUID
    username: str
    email: EmailStr
    role: UserRole
    email_verified_at: datetime | None

    class Config:
        from_attributes = True
