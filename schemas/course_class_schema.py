from typing import List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, EmailStr, Field

from schemas.user_schema import User
from schemas.activity_schema import Activity


class CourseClassBase(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    discipline: str = Field(min_length=1, max_length=100)


class CourseClassRegister(CourseClassBase):
    teacher_id: uuid.UUID


class CourseClass(BaseModel):
    id: uuid.UUID
    name: str
    discipline: str
    teacher_id: uuid.UUID
    status: str
    activities: Optional[List[Activity]] = []
    monitor: Optional[List[User]] = []
    students: Optional[List[User]] = []

    class Config:
        from_attributes = True


class AddStudentSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr


class RemoveStudentSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    student_id: str
