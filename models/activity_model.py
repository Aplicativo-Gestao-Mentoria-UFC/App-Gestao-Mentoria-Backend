import uuid
from sqlalchemy import UUID, Column, ForeignKey, String
from sqlalchemy.orm import relationship

from core.database import Base


class ActivityModel(Base):
    __tablename__ = "activities"

    id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False
    )
    title = Column(String, nullable=False)
    description = Column(String, nullable=False)
    course_class_id = Column(UUID(as_uuid=True), ForeignKey("course_class.id"))

    course_class = relationship("CourseClassModel", back_populates="activities")
