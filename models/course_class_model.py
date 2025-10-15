import uuid
from sqlalchemy import UUID, Column, ForeignKey, String, Table, true
from core.database import Base
from sqlalchemy.orm import relationship

course_class_monitors = Table(
    "course_class_monitors",
    Base.metadata,
    Column("course_class_id", UUID(as_uuid=True), ForeignKey("course_class.id")),
    Column("monitor_id", UUID(as_uuid=True), ForeignKey("users.id")),
)

course_class_students = Table(
    "course_class_students",
    Base.metadata,
    Column("course_class_id", UUID(as_uuid=True), ForeignKey("course_class.id")),
    Column("student_id", UUID(as_uuid=True), ForeignKey("users.id")),
)


class CourseClassModel(Base):
    __tablename__ = "course_class"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    discipline = Column(String, nullable=False)
    teacher_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    status = Column(String, default="On")

    teacher = relationship("UserModel", foreign_keys=[teacher_id])
    monitor = relationship(
        "UserModel", secondary=course_class_monitors, backref="course_class_monitor"
    )
    students = relationship(
        "UserModel", secondary=course_class_students, backref="course_class_students"
    )
    activities = relationship(
        "ActivityModel", back_populates="course_class", cascade="all, delete-orphan"
    )
