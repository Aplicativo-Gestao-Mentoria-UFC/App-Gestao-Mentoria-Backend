from pydantic import BaseModel, ConfigDict, EmailStr
from models.__all_models import UserRole
import uuid


class UserBase(BaseModel):
    username: str
    email: EmailStr
    role: UserRole


class UserCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: str
    email: EmailStr
    password: str


class User(BaseModel):
    id: uuid.UUID
    username: str
    email: EmailStr
    role: UserRole

    class Config:
        from_attributes = True
