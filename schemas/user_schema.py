import re
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
from models.__all_models import UserRole
import uuid


WEAK_PASSWORD_MESSAGE = (
    "A senha deve ter pelo menos 8 caracteres, uma letra maiúscula, "
    "uma letra minúscula, um número e um caractere especial."
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


class UserBase(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: EmailStr
    role: UserRole


class UserCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: str = Field(min_length=3, max_length=50)
    email: EmailStr
    role: UserRole = UserRole.student
    password: str = Field(max_length=128)

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, password: str) -> str:
        return validate_strong_password(password)


class UserUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: Optional[str] = Field(default=None, min_length=3, max_length=50)
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(default=None, max_length=128)

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

    class Config:
        from_attributes = True
