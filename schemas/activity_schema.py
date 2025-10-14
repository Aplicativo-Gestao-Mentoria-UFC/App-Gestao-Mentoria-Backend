from pydantic import BaseModel
import uuid


class ActivityBase(BaseModel):
    title: str
    description: str


class ActivityRegister(ActivityBase):
    course_class_id: uuid.UUID
