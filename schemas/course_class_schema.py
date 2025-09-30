import uuid
from pydantic import BaseModel


class CourseClassBase(BaseModel):
    name: str
    discipline: str


class CourseClassRegister(CourseClassBase):
    teacher_id: uuid.UUID


class CourseClass(CourseClassBase):
    id: uuid.UUID
    teacher_id: uuid.UUID

    class Config:
        from_attributes = True
