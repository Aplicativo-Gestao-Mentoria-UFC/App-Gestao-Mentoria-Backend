from pydantic import BaseModel, EmailStr
from models.__all_models import UserRole
import uuid


class UserBase(BaseModel):
    username: str
    email: EmailStr
    role: UserRole


class UserCreate(UserBase):
    password: str


class User(UserBase):
    id: uuid.UUID

    class Config:
        from_attributes = True
