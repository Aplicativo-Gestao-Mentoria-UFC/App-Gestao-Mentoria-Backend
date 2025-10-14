from typing import List, Optional
import uuid
from pydantic import BaseModel

from schemas.user_schema import User
from schemas.activity_schema import Activity


class CourseClassBase(BaseModel):
    name: str
    discipline: str


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
    email: str


class RemoveStudentSchema(BaseModel):
    student_id: str
