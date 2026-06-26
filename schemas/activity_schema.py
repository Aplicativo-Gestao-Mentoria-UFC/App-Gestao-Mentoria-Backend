import uuid

from typing import Optional
from pydantic import BaseModel


class ActivityBase(BaseModel):
    title: str
    description: str
    fileUrl: Optional[str] = None


class ActivityCreate(ActivityBase):
    pass


class ActivityUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    fileUrl: Optional[str] = None


class ActivityRegister(ActivityBase):
    course_class_id: uuid.UUID


class Activity(ActivityBase):
    id: uuid.UUID
    course_class_id: uuid.UUID

    class Config:
        from_attributes = True