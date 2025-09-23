import uuid
from sqlalchemy import Column, UUID, String
from core.database import Base
from enum import Enum

class UserRole(str, Enum):
    admin = "ADMIN"
    user = "USER"


class UserModel(Base):
    __tablename__ = "users"

    id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False
    )
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    role = Column(String,  default=UserRole.user.value)
    hashed_password = Column(String, nullable=False)
