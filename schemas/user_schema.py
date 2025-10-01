from pydantic import BaseModel, EmailStr
from models.__all_models import UserRole
import uuid


class UserBase(BaseModel):
    username: str
    email: EmailStr
    role: UserRole


class UserCreate(UserBase):
    password: str


class User(BaseModel):
    id: uuid.UUID
    username: str
    email: EmailStr
    role: UserRole

    class Config:
        from_attributes = True
