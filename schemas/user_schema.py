from datetime import datetime
import re
from typing import Optional
import uuid

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from core.config import settings
from models.__all_models import UserRole


WEAK_PASSWORD_MESSAGE = (
    "A senha deve ter pelo menos 8 caracteres, uma letra maiúscula, "
    "uma letra minúscula, um número e um caractere especial."
)


def validate_strong_password(password: str) -> str:
    checks = (
        len(password) >= 8,
        re.search(r"[A-Z]", password),
        re.search(r"[a-z]", password),
        re.search(r"\d", password),
        re.search(r"[^A-Za-z0-9]", password),
    )
    if not all(checks):
        raise ValueError(WEAK_PASSWORD_MESSAGE)
    return password


def get_email_domain(email: EmailStr | str) -> str:
    return str(email).strip().lower().rsplit("@", maxsplit=1)[-1]


def validate_teacher_institutional_email(email: EmailStr | str, role: UserRole) -> str:
    email_value = str(email).strip().lower()
    domain = get_email_domain(email_value)
    allowed_domains = settings.institutional_email_domains

    if role == UserRole.teacher and domain not in allowed_domains:
        allowed = ", ".join(f"@{item}" for item in sorted(allowed_domains))
        raise ValueError(
            f"Professores devem usar email institucional de um domínio permitido: {allowed}."
        )

    if role == UserRole.student and domain in allowed_domains:
        raise ValueError(
            "Este domínio está reservado ao fluxo de cadastro institucional de professor."
        )

    return email_value


class UserBase(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: EmailStr
    role: UserRole

    @model_validator(mode="after")
    def validate_email_domain(self):
        self.email = validate_teacher_institutional_email(self.email, self.role)
        return self


class UserCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: str = Field(min_length=3, max_length=50)
    email: EmailStr
    role: UserRole = UserRole.student
    password: str = Field(min_length=8, max_length=128)

    @model_validator(mode="after")
    def validate_email_domain(self):
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
    password: Optional[str] = Field(default=None, min_length=8, max_length=128)

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, password: str | None) -> str | None:
        if password is None:
            return None
        return validate_strong_password(password)


class User(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    username: str
    email: EmailStr
    role: UserRole
    email_verified_at: datetime | None
