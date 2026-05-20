from pydantic import BaseModel, Field
import uuid


class ActivityBase(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    description: str = Field(min_length=1, max_length=500)


class ActivityRegister(ActivityBase):
    course_class_id: uuid.UUID


class Activity(ActivityBase):
    id: uuid.UUID

    class Config:
        from_attributes = True
