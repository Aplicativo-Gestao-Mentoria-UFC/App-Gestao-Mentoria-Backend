from typing import ClassVar
from pydantic_settings import BaseSettings
from sqlalchemy.ext.declarative import declarative_base, DeclarativeMeta

class Settings(BaseSettings):
    API_STR: str
    DB_URL: str
    DBBaseModel: ClassVar[DeclarativeMeta] = declarative_base()

    class Config:
        env_file = ".env"
        class_sensitive = True

settings = Settings()