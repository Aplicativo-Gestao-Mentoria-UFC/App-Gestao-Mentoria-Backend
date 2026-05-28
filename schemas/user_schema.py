from pydantic import BaseModel, ConfigDict, EmailStr, Field
from models.__all_models import UserRole
import uuid


class UserBase(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: EmailStr
    role: UserRole


class UserCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: str = Field(min_length=3, max_length=50)
    email: EmailStr
    role: UserRole = UserRole.student
    password: str = Field(min_length=8, max_length=128)


class User(BaseModel):
    id: uuid.UUID
    username: str
    email: EmailStr
    role: UserRole

    class Config:
        from_attributes = True
