from typing import List, Optional
import uuid
from pydantic import BaseModel

from schemas.user_schema import User


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
    monitor: Optional[List[User]] = []
    students: Optional[List[User]] = []

    class Config:
        from_attributes = True


class AddMonitorSchema(BaseModel):
    email: str
